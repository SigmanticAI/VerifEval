"""
FIFO Environment - Top-level verification environment
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from fifo_if import FifoInterface
from fifo_driver import FifoDriver
from fifo_monitor import FifoMonitor
from fifo_scoreboard import FifoScoreboard


class FifoEnvironment:
    """
    Top-level verification environment for FIFO.
    Instantiates and connects all verification components.
    """
    
    def __init__(self, dut, depth=16):
        self.dut = dut
        self.depth = depth
        
        # Create components
        self.interface = FifoInterface(dut)
        self.scoreboard = FifoScoreboard(depth=depth)
        self.driver = FifoDriver(self.interface, self.scoreboard)
        self.monitor = FifoMonitor(self.interface, self.scoreboard)
    
    async def start(self):
        """Start the environment."""
        # Start clock
        clock = Clock(self.dut.clk, 10, units="ns")
        cocotb.start_soon(clock.start())
        
        # Start monitor
        await self.monitor.start()
        
        cocotb.log.info("Environment started")
    
    async def reset(self):
        """Apply reset sequence."""
        self.interface.reset_inputs()
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 5)
        self.dut.rst_n.value = 1
        await ClockCycles(self.dut.clk, 2)
        
        # Clear scoreboard
        self.scoreboard.clear()
        
        cocotb.log.info("Reset complete")
    
    def stop(self):
        """Stop the environment."""
        self.monitor.stop()
    
    def report(self):
        """Generate final report."""
        cocotb.log.info("\n" + "=" * 50)
        cocotb.log.info("ENVIRONMENT REPORT")
        cocotb.log.info("=" * 50)
        
        # Monitor stats
        stats = self.monitor.get_stats()
        cocotb.log.info(f"Total writes observed: {stats['writes']}")
        cocotb.log.info(f"Total reads observed:  {stats['reads']}")
        
        # Scoreboard report
        return self.scoreboard.report()

