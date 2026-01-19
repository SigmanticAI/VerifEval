"""
FIFO Interface wrapper.

Provides a clean Python interface to the FIFO DUT signals.
Part of multi-file verification structure.
"""

from cocotb.handle import SimHandleBase


class FifoInterface:
    """Interface to FIFO DUT signals."""
    
    def __init__(self, dut: SimHandleBase, depth: int = 16):
        self.dut = dut
        self.depth = depth
        
        # Map signals
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        self.wr_en = dut.wr_en
        self.wr_data = dut.wr_data
        self.rd_en = dut.rd_en
        self.rd_data = dut.rd_data
        self.full = dut.full
        self.empty = dut.empty
        self.count = dut.count
    
    def is_full(self) -> bool:
        """Check if FIFO is full."""
        return bool(self.full.value)
    
    def is_empty(self) -> bool:
        """Check if FIFO is empty."""
        return bool(self.empty.value)
    
    def get_count(self) -> int:
        """Get current FIFO count."""
        return int(self.count.value)
    
    def reset_signals(self):
        """Reset control signals to default."""
        self.wr_en.value = 0
        self.rd_en.value = 0
        self.wr_data.value = 0

