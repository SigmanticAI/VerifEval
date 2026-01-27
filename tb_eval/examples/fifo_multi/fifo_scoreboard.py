"""
FIFO Scoreboard.

Reference model and checker for FIFO verification.
Part of multi-file verification structure.
"""

from collections import deque
import cocotb


class FifoScoreboard:
    """Reference model scoreboard for FIFO."""
    
    def __init__(self, depth: int = 16):
        self.depth = depth
        self.expected_data = deque()
        self.errors = []
        self.checks_passed = 0
        self.checks_failed = 0
    
    def write(self, data: int):
        """Record a write to expected queue."""
        if len(self.expected_data) < self.depth:
            self.expected_data.append(data)
    
    def check_read(self, actual_data: int) -> bool:
        """Check read data against expected."""
        if not self.expected_data:
            self.errors.append(f"Read from empty FIFO, got {actual_data}")
            self.checks_failed += 1
            return False
        
        expected = self.expected_data.popleft()
        
        if actual_data == expected:
            self.checks_passed += 1
            return True
        else:
            self.errors.append(f"Data mismatch: expected {expected}, got {actual_data}")
            self.checks_failed += 1
            return False
    
    def report(self) -> bool:
        """Print report and return pass/fail status."""
        total = self.checks_passed + self.checks_failed
        
        cocotb.log.info(f"Scoreboard: {self.checks_passed}/{total} checks passed")
        
        if self.errors:
            for err in self.errors[:5]:  # Show first 5 errors
                cocotb.log.error(f"  {err}")
        
        return self.checks_failed == 0
    
    def reset(self):
        """Reset scoreboard state."""
        self.expected_data.clear()
        self.errors.clear()
        self.checks_passed = 0
        self.checks_failed = 0




