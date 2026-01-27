"""
FIFO Verification Environment.

Top-level environment connecting all verification components.
Part of multi-file verification structure.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from fifo_interface import FifoInterface
from fifo_driver import FifoDriver
from fifo_scoreboard import FifoScoreboard


class FifoEnvironment:
    """Verification environment for FIFO."""
    
    def __init__(self, dut, depth: int = 16, data_width: int = 8):
        self.dut = dut
        self.depth = depth
        self.data_width = data_width
        
        # Create components
        self.interface = FifoInterface(dut, depth)
        self.driver = FifoDriver(self.interface)
        self.scoreboard = FifoScoreboard(depth)
    
    async def start(self, clock_period_ns: int = 10):
        """Start the environment (clock, etc.)."""
        # Start clock
        cocotb.start_soon(Clock(self.dut.clk, clock_period_ns, units='ns').start())
        await RisingEdge(self.dut.clk)
    
    async def reset(self, cycles: int = 5):
        """Apply reset sequence."""
        self.dut.rst_n.value = 0
        self.interface.reset_signals()
        
        await ClockCycles(self.dut.clk, cycles)
        
        self.dut.rst_n.value = 1
        await RisingEdge(self.dut.clk)
        
        self.scoreboard.reset()
    
    async def write_and_track(self, data: int) -> bool:
        """Write data and track in scoreboard."""
        success = await self.driver.write(data)
        if success:
            self.scoreboard.write(data)
        return success
    
    async def read_and_check(self) -> bool:
        """Read data and verify with scoreboard."""
        data = await self.driver.read()
        if data >= 0:
            return self.scoreboard.check_read(data)
        return True  # Empty read is OK
    
    def report(self) -> bool:
        """Generate final report."""
        return self.scoreboard.report()




