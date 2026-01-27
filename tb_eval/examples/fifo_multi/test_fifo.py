"""
FIFO Test Suite.

Multi-file testbench demonstrating structured verification.
Uses separate interface, driver, monitor, scoreboard, and environment.
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
import random
import sys
import os

# Add current directory for imports
sys.path.insert(0, os.path.dirname(__file__))

from fifo_env import FifoEnvironment


FIFO_DEPTH = 16
DATA_WIDTH = 8


@cocotb.test()
async def test_reset(dut):
    """Test reset behavior."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    assert env.interface.is_empty(), "FIFO should be empty after reset"
    assert not env.interface.is_full(), "FIFO should not be full after reset"
    assert env.interface.get_count() == 0, "Count should be 0 after reset"
    
    cocotb.log.info("Reset test PASSED")


@cocotb.test()
async def test_single_write_read(dut):
    """Test single write followed by read."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Write
    test_data = 0xAB
    await env.write_and_track(test_data)
    await RisingEdge(dut.clk)
    
    assert not env.interface.is_empty(), "FIFO should not be empty"
    assert env.interface.get_count() == 1, "Count should be 1"
    
    # Read and verify
    result = await env.read_and_check()
    assert result, "Read data should match written data"
    
    await RisingEdge(dut.clk)
    assert env.interface.is_empty(), "FIFO should be empty after read"
    
    env.report()
    cocotb.log.info("Single write/read test PASSED")


@cocotb.test()
async def test_fill_and_drain(dut):
    """Test filling FIFO completely then draining."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Fill FIFO
    for i in range(FIFO_DEPTH):
        await env.write_and_track(i)
        await RisingEdge(dut.clk)
    
    assert env.interface.is_full(), "FIFO should be full"
    assert env.interface.get_count() == FIFO_DEPTH
    
    # Drain FIFO
    for _ in range(FIFO_DEPTH):
        result = await env.read_and_check()
        assert result, "Data integrity check failed"
        await RisingEdge(dut.clk)
    
    assert env.interface.is_empty(), "FIFO should be empty after drain"
    
    passed = env.report()
    assert passed, "Scoreboard reported errors"
    cocotb.log.info("Fill and drain test PASSED")


@cocotb.test()
async def test_overflow_protection(dut):
    """Test that writes to full FIFO are ignored."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Fill FIFO
    for i in range(FIFO_DEPTH):
        await env.write_and_track(i)
        await RisingEdge(dut.clk)
    
    # Try to write more
    initial_count = env.interface.get_count()
    env.interface.wr_data.value = 0xFF
    env.interface.wr_en.value = 1
    await RisingEdge(dut.clk)
    env.interface.wr_en.value = 0
    await RisingEdge(dut.clk)
    
    assert env.interface.get_count() == initial_count, "Count should not change on overflow"
    
    cocotb.log.info("Overflow protection test PASSED")


@cocotb.test()
async def test_underflow_protection(dut):
    """Test that reads from empty FIFO are handled."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    assert env.interface.is_empty(), "FIFO should be empty"
    
    # Try to read from empty
    env.interface.rd_en.value = 1
    await RisingEdge(dut.clk)
    env.interface.rd_en.value = 0
    await RisingEdge(dut.clk)
    
    assert env.interface.is_empty(), "FIFO should still be empty"
    
    cocotb.log.info("Underflow protection test PASSED")


@cocotb.test()
async def test_random_traffic(dut):
    """Test with random read/write traffic."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Random operations
    for _ in range(100):
        if random.random() < 0.55:  # Slightly more writes
            data = random.randint(0, 255)
            await env.write_and_track(data)
        else:
            await env.read_and_check()
        await RisingEdge(dut.clk)
    
    # Drain remaining
    while not env.interface.is_empty():
        await env.read_and_check()
        await RisingEdge(dut.clk)
    
    passed = env.report()
    assert passed, "Scoreboard reported errors"
    cocotb.log.info("Random traffic test PASSED")


@cocotb.test()
async def test_data_patterns(dut):
    """Test various data patterns."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    patterns = [
        [0x00, 0xFF, 0xAA, 0x55],           # Alternating
        [0x01, 0x02, 0x04, 0x08],           # Walking ones
        [0xFE, 0xFD, 0xFB, 0xF7],           # Walking zeros
    ]
    
    for pattern in patterns:
        # Write pattern
        for data in pattern:
            await env.write_and_track(data)
            await RisingEdge(dut.clk)
        
        # Read and verify
        for _ in pattern:
            result = await env.read_and_check()
            assert result, "Pattern verification failed"
            await RisingEdge(dut.clk)
    
    passed = env.report()
    assert passed, "Data pattern tests failed"
    cocotb.log.info("Data pattern test PASSED")




