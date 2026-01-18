"""
FIFO Driver - Drives stimulus to the DUT
"""

import cocotb
from cocotb.triggers import RisingEdge
import random


class FifoDriver:
    """
    Driver for FIFO verification.
    Handles write and read transactions.
    """
    
    def __init__(self, interface, scoreboard=None):
        self.intf = interface
        self.scoreboard = scoreboard
    
    async def write(self, data):
        """
        Write a single data item to FIFO.
        Returns True if write was successful.
        """
        if self.intf.is_full():
            cocotb.log.warning(f"FIFO full, cannot write {data}")
            return False
        
        self.intf.wr_data.value = data
        self.intf.wr_en.value = 1
        await RisingEdge(self.intf.clk)
        self.intf.wr_en.value = 0
        
        # Notify scoreboard
        if self.scoreboard:
            self.scoreboard.add_expected(data)
        
        return True
    
    async def read(self):
        """
        Read a single data item from FIFO.
        Returns the data read, or None if empty.
        """
        if self.intf.is_empty():
            cocotb.log.warning("FIFO empty, cannot read")
            return None
        
        self.intf.rd_en.value = 1
        await RisingEdge(self.intf.clk)
        data = int(self.intf.rd_data.value)
        self.intf.rd_en.value = 0
        
        # Notify scoreboard
        if self.scoreboard:
            self.scoreboard.check_actual(data)
        
        return data
    
    async def write_burst(self, data_list):
        """Write multiple data items."""
        written = 0
        for data in data_list:
            if await self.write(data):
                written += 1
            await RisingEdge(self.intf.clk)
        return written
    
    async def read_burst(self, count):
        """Read multiple data items."""
        data_list = []
        for _ in range(count):
            data = await self.read()
            if data is not None:
                data_list.append(data)
            await RisingEdge(self.intf.clk)
        return data_list
    
    async def random_traffic(self, num_ops, write_prob=0.6):
        """Generate random read/write traffic."""
        for _ in range(num_ops):
            if random.random() < write_prob:
                data = random.randint(0, 255)
                await self.write(data)
            else:
                await self.read()
            await RisingEdge(self.intf.clk)

