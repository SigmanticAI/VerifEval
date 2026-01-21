"""
FIFO Driver.

Drives stimulus to the FIFO DUT.
Part of multi-file verification structure.
"""

import random
from cocotb.triggers import RisingEdge

from fifo_interface import FifoInterface


class FifoDriver:
    """Driver for FIFO operations."""
    
    def __init__(self, interface: FifoInterface):
        self.intf = interface
    
    async def write(self, data: int) -> bool:
        """
        Write data to FIFO.
        
        Returns True if write was accepted (FIFO not full).
        """
        if self.intf.is_full():
            return False
        
        self.intf.wr_data.value = data
        self.intf.wr_en.value = 1
        await RisingEdge(self.intf.clk)
        self.intf.wr_en.value = 0
        
        return True
    
    async def read(self) -> int:
        """
        Read data from FIFO.
        
        Returns read data, or -1 if FIFO was empty.
        """
        if self.intf.is_empty():
            return -1
        
        self.intf.rd_en.value = 1
        await RisingEdge(self.intf.clk)
        self.intf.rd_en.value = 0
        await RisingEdge(self.intf.clk)  # Wait for data
        
        return int(self.intf.rd_data.value)
    
    async def random_traffic(self, num_ops: int = 100, write_prob: float = 0.5):
        """Generate random read/write traffic."""
        
        for _ in range(num_ops):
            if random.random() < write_prob:
                # Write operation
                data = random.randint(0, 255)
                await self.write(data)
            else:
                # Read operation
                await self.read()
            
            await RisingEdge(self.intf.clk)


