"""
FIFO Test Suite - Main test file
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
import random
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fifo_if import FifoInterface
from fifo_driver import FifoDriver
from fifo_monitor import FifoMonitor
from fifo_scoreboard import FifoScoreboard
from fifo_env import FifoEnvironment


# Constants
FIFO_DEPTH = 16
DATA_WIDTH = 8


@cocotb.test()
async def test_reset(dut):
    """Test reset behavior."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Check initial state
    assert env.interface.is_empty(), "FIFO should be empty after reset"
    assert not env.interface.is_full(), "FIFO should not be full after reset"
    assert env.interface.get_count() == 0, "Count should be 0 after reset"
    
    env.stop()
    cocotb.log.info("Reset test PASSED")


@cocotb.test()
async def test_single_write_read(dut):
    """Test single write followed by read."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Write single value
    test_data = 0xAB
    await env.driver.write(test_data)
    await RisingEdge(dut.clk)
    
    # Check state
    assert not env.interface.is_empty(), "FIFO should not be empty after write"
    assert env.interface.get_count() == 1, "Count should be 1"
    
    # Read back
    read_data = await env.driver.read()
    await RisingEdge(dut.clk)
    
    assert read_data == test_data, f"Data mismatch: wrote {test_data}, read {read_data}"
    assert env.interface.is_empty(), "FIFO should be empty after read"
    
    env.stop()
    env.report()
    cocotb.log.info("Single write/read test PASSED")


@cocotb.test()
async def test_fill_and_drain(dut):
    """Test filling FIFO completely then draining."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Fill FIFO
    test_data = list(range(FIFO_DEPTH))
    for data in test_data:
        await env.driver.write(data)
        await RisingEdge(dut.clk)
    
    # Check full
    assert env.interface.is_full(), "FIFO should be full"
    assert env.interface.get_count() == FIFO_DEPTH, f"Count should be {FIFO_DEPTH}"
    
    # Drain FIFO
    for expected in test_data:
        read_data = await env.driver.read()
        await RisingEdge(dut.clk)
        assert read_data == expected, f"Data mismatch: expected {expected}, got {read_data}"
    
    # Check empty
    assert env.interface.is_empty(), "FIFO should be empty after drain"
    
    env.stop()
    passed = env.report()
    assert passed, "Scoreboard reported errors"
    cocotb.log.info("Fill and drain test PASSED")


@cocotb.test()
async def test_concurrent_rw(dut):
    """Test concurrent read and write operations."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Pre-fill with some data
    for i in range(FIFO_DEPTH // 2):
        await env.driver.write(i)
        await RisingEdge(dut.clk)
    
    # Concurrent read/write
    for i in range(50):
        # Write new data
        new_data = 100 + i
        env.interface.wr_data.value = new_data
        env.interface.wr_en.value = 1
        
        # Read existing data
        env.interface.rd_en.value = 1
        
        await RisingEdge(dut.clk)
        
        env.interface.wr_en.value = 0
        env.interface.rd_en.value = 0
        
        await RisingEdge(dut.clk)
    
    env.stop()
    cocotb.log.info("Concurrent R/W test PASSED")


@cocotb.test()
async def test_random_traffic(dut):
    """Test with random traffic pattern."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Generate random traffic
    await env.driver.random_traffic(num_ops=200, write_prob=0.55)
    
    # Drain remaining
    while not env.interface.is_empty():
        await env.driver.read()
        await RisingEdge(dut.clk)
    
    env.stop()
    passed = env.report()
    assert passed, "Scoreboard reported errors"
    cocotb.log.info("Random traffic test PASSED")


@cocotb.test()
async def test_overflow_protection(dut):
    """Test that writes to full FIFO are ignored."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Fill FIFO
    for i in range(FIFO_DEPTH):
        await env.driver.write(i)
        await RisingEdge(dut.clk)
    
    # Try to write more (should be ignored)
    initial_count = env.interface.get_count()
    env.interface.wr_data.value = 0xFF
    env.interface.wr_en.value = 1
    await RisingEdge(dut.clk)
    env.interface.wr_en.value = 0
    await RisingEdge(dut.clk)
    
    # Count should not change
    assert env.interface.get_count() == initial_count, "Count changed on full write"
    
    env.stop()
    cocotb.log.info("Overflow protection test PASSED")


@cocotb.test()
async def test_underflow_protection(dut):
    """Test that reads from empty FIFO are handled."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Try to read from empty FIFO
    assert env.interface.is_empty(), "FIFO should be empty"
    
    env.interface.rd_en.value = 1
    await RisingEdge(dut.clk)
    env.interface.rd_en.value = 0
    await RisingEdge(dut.clk)
    
    # Should still be empty
    assert env.interface.is_empty(), "FIFO should still be empty"
    
    env.stop()
    cocotb.log.info("Underflow protection test PASSED")


@cocotb.test()
async def test_data_integrity(dut):
    """Test data integrity with various patterns."""
    env = FifoEnvironment(dut, depth=FIFO_DEPTH)
    await env.start()
    await env.reset()
    
    # Test patterns
    patterns = [
        [0x00, 0xFF, 0xAA, 0x55],  # Alternating
        [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80],  # Walking ones
        [0xFE, 0xFD, 0xFB, 0xF7, 0xEF, 0xDF, 0xBF, 0x7F],  # Walking zeros
    ]
    
    for pattern in patterns:
        # Write pattern
        for data in pattern:
            await env.driver.write(data)
            await RisingEdge(dut.clk)
        
        # Read and verify
        for expected in pattern:
            actual = await env.driver.read()
            await RisingEdge(dut.clk)
            assert actual == expected, f"Pattern mismatch: expected {expected:02X}, got {actual:02X}"
    
    env.stop()
    passed = env.report()
    assert passed, "Scoreboard reported errors"
    cocotb.log.info("Data integrity test PASSED")

