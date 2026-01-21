"""
FIFO Monitor.

Monitors FIFO transactions for verification.
Part of multi-file verification structure.
"""

from cocotb.triggers import RisingEdge
from collections import deque

from fifo_interface import FifoInterface


class FifoMonitor:
    """Monitor for FIFO transactions."""
    
    def __init__(self, interface: FifoInterface):
        self.intf = interface
        self.write_transactions = deque()
        self.read_transactions = deque()
        self._running = False
    
    async def start(self):
        """Start monitoring."""
        self._running = True
        
        while self._running:
            await RisingEdge(self.intf.clk)
            
            # Monitor writes
            if self.intf.wr_en.value and not self.intf.is_full():
                data = int(self.intf.wr_data.value)
                self.write_transactions.append(data)
            
            # Monitor reads
            if self.intf.rd_en.value and not self.intf.is_empty():
                # Data appears on next cycle
                await RisingEdge(self.intf.clk)
                data = int(self.intf.rd_data.value)
                self.read_transactions.append(data)
    
    def stop(self):
        """Stop monitoring."""
        self._running = False
    
    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        return {
            "total_writes": len(self.write_transactions),
            "total_reads": len(self.read_transactions),
        }


