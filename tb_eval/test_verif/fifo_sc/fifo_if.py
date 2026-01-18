"""
FIFO Interface - Signal definitions and helper methods
"""

class FifoInterface:
    """
    Interface wrapper for FIFO DUT signals.
    Provides abstraction for signal access.
    """
    
    def __init__(self, dut):
        self.dut = dut
        
        # Clock and reset
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        
        # Write interface
        self.wr_en = dut.wr_en
        self.wr_data = dut.wr_data
        self.full = dut.full
        
        # Read interface
        self.rd_en = dut.rd_en
        self.rd_data = dut.rd_data
        self.empty = dut.empty
        
        # Status
        self.count = dut.count
    
    def reset_inputs(self):
        """Reset all input signals to default values."""
        self.wr_en.value = 0
        self.wr_data.value = 0
        self.rd_en.value = 0
    
    def is_full(self):
        """Check if FIFO is full."""
        return int(self.full.value) == 1
    
    def is_empty(self):
        """Check if FIFO is empty."""
        return int(self.empty.value) == 1
    
    def get_count(self):
        """Get current FIFO count."""
        return int(self.count.value)

