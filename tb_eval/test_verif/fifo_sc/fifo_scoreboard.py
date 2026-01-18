"""
FIFO Scoreboard - Reference model and checking
"""

import cocotb
from collections import deque


class FifoScoreboard:
    """
    Scoreboard for FIFO verification.
    Maintains reference model and checks DUT output.
    """
    
    def __init__(self, depth=16):
        self.depth = depth
        self.expected_queue = deque()
        self.matches = 0
        self.mismatches = 0
        self.errors = []
    
    def add_expected(self, data):
        """Add expected data to reference queue."""
        if len(self.expected_queue) < self.depth:
            self.expected_queue.append(data)
            cocotb.log.debug(f"Scoreboard: Added expected {data}")
        else:
            error = f"Reference FIFO overflow - data {data} dropped"
            self.errors.append(error)
            cocotb.log.error(error)
    
    def check_actual(self, actual_data):
        """Check actual data against expected."""
        if not self.expected_queue:
            error = f"Unexpected read: got {actual_data} but reference queue empty"
            self.errors.append(error)
            cocotb.log.error(error)
            self.mismatches += 1
            return False
        
        expected = self.expected_queue.popleft()
        
        if actual_data == expected:
            self.matches += 1
            cocotb.log.debug(f"Scoreboard: Match - expected {expected}, got {actual_data}")
            return True
        else:
            self.mismatches += 1
            error = f"Data mismatch: expected {expected}, got {actual_data}"
            self.errors.append(error)
            cocotb.log.error(error)
            return False
    
    def get_expected_count(self):
        """Get number of items in reference queue."""
        return len(self.expected_queue)
    
    def is_empty(self):
        """Check if reference queue is empty."""
        return len(self.expected_queue) == 0
    
    def clear(self):
        """Clear the scoreboard state."""
        self.expected_queue.clear()
        self.matches = 0
        self.mismatches = 0
        self.errors = []
    
    def report(self):
        """Generate final report."""
        cocotb.log.info("=" * 50)
        cocotb.log.info("SCOREBOARD REPORT")
        cocotb.log.info("=" * 50)
        cocotb.log.info(f"Matches:    {self.matches}")
        cocotb.log.info(f"Mismatches: {self.mismatches}")
        cocotb.log.info(f"Pending:    {len(self.expected_queue)}")
        
        if self.errors:
            cocotb.log.info(f"Errors ({len(self.errors)}):")
            for err in self.errors[:10]:  # Show first 10
                cocotb.log.info(f"  - {err}")
        
        return self.mismatches == 0 and len(self.errors) == 0

