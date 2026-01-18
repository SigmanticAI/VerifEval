"""
FIFO Monitor - Observes DUT behavior
"""

import cocotb
from cocotb.triggers import RisingEdge


class FifoMonitor:
    """
    Monitor for FIFO verification.
    Observes transactions and reports to scoreboard.
    """
    
    def __init__(self, interface, scoreboard=None):
        self.intf = interface
        self.scoreboard = scoreboard
        self.write_count = 0
        self.read_count = 0
        self.running = False
    
    async def start(self):
        """Start monitoring in background."""
        self.running = True
        cocotb.start_soon(self._monitor_writes())
        cocotb.start_soon(self._monitor_reads())
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
    
    async def _monitor_writes(self):
        """Monitor write transactions."""
        while self.running:
            await RisingEdge(self.intf.clk)
            
            if int(self.intf.wr_en.value) == 1 and not self.intf.is_full():
                data = int(self.intf.wr_data.value)
                self.write_count += 1
                cocotb.log.debug(f"Monitor: Write {data} (count={self.write_count})")
    
    async def _monitor_reads(self):
        """Monitor read transactions."""
        while self.running:
            await RisingEdge(self.intf.clk)
            
            if int(self.intf.rd_en.value) == 1 and not self.intf.is_empty():
                data = int(self.intf.rd_data.value)
                self.read_count += 1
                cocotb.log.debug(f"Monitor: Read {data} (count={self.read_count})")
    
    def get_stats(self):
        """Get monitoring statistics."""
        return {
            "writes": self.write_count,
            "reads": self.read_count,
        }

