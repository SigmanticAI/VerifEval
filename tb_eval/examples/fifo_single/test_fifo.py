"""
Single-file FIFO Testbench.

Self-contained cocotb testbench for synchronous FIFO.
Demonstrates single-file verification pattern.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
import random


FIFO_DEPTH = 8


async def reset_dut(dut):
    """Apply reset to DUT."""
    dut.rst_n.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def write_fifo(dut, data):
    """Write single data to FIFO."""
    dut.wr_data.value = data
    dut.wr_en.value = 1
    await RisingEdge(dut.clk)
    dut.wr_en.value = 0


async def read_fifo(dut):
    """Read single data from FIFO."""
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    return int(dut.rd_data.value)


@cocotb.test()
async def test_reset(dut):
    """Test reset behavior."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    assert dut.empty.value == 1, "FIFO should be empty after reset"
    assert dut.full.value == 0, "FIFO should not be full after reset"
    
    cocotb.log.info("Reset test PASSED")


@cocotb.test()
async def test_single_write_read(dut):
    """Test single write and read."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    # Write
    await write_fifo(dut, 0xAB)
    await RisingEdge(dut.clk)
    
    assert dut.empty.value == 0, "FIFO should not be empty"
    
    # Read
    data = await read_fifo(dut)
    assert data == 0xAB, f"Expected 0xAB, got {hex(data)}"
    
    await RisingEdge(dut.clk)
    assert dut.empty.value == 1, "FIFO should be empty after read"
    
    cocotb.log.info("Single write/read test PASSED")


@cocotb.test()
async def test_fill_and_drain(dut):
    """Test filling FIFO to capacity then draining."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    # Fill FIFO
    test_data = list(range(FIFO_DEPTH))
    for data in test_data:
        await write_fifo(dut, data)
        await RisingEdge(dut.clk)
    
    assert dut.full.value == 1, "FIFO should be full"
    
    # Drain FIFO
    for expected in test_data:
        actual = await read_fifo(dut)
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    await RisingEdge(dut.clk)
    assert dut.empty.value == 1, "FIFO should be empty"
    
    cocotb.log.info("Fill and drain test PASSED")


@cocotb.test()
async def test_overflow_protection(dut):
    """Test that writes to full FIFO are ignored."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    # Fill FIFO
    for i in range(FIFO_DEPTH):
        await write_fifo(dut, i)
        await RisingEdge(dut.clk)
    
    assert dut.full.value == 1, "FIFO should be full"
    
    # Try to write more - should be ignored
    await write_fifo(dut, 0xFF)
    await RisingEdge(dut.clk)
    
    # First read should still be 0, not 0xFF
    data = await read_fifo(dut)
    assert data == 0, f"First data should be 0, got {data}"
    
    cocotb.log.info("Overflow protection test PASSED")


@cocotb.test()
async def test_underflow_protection(dut):
    """Test reads from empty FIFO."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    assert dut.empty.value == 1, "FIFO should be empty"
    
    # Try to read from empty
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    
    # Should still be empty
    assert dut.empty.value == 1, "FIFO should still be empty"
    
    cocotb.log.info("Underflow protection test PASSED")


@cocotb.test()
async def test_random_operations(dut):
    """Test random read/write patterns."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    # Reference model
    expected_data = []
    
    for _ in range(50):
        if random.random() < 0.6 and not dut.full.value:
            # Write
            data = random.randint(0, 255)
            await write_fifo(dut, data)
            expected_data.append(data)
        elif not dut.empty.value and expected_data:
            # Read
            actual = await read_fifo(dut)
            expected = expected_data.pop(0)
            assert actual == expected, f"Mismatch: expected {expected}, got {actual}"
        
        await RisingEdge(dut.clk)
    
    # Drain remaining
    while not dut.empty.value and expected_data:
        actual = await read_fifo(dut)
        expected = expected_data.pop(0)
        assert actual == expected, f"Drain mismatch: expected {expected}, got {actual}"
    
    cocotb.log.info("Random operations test PASSED")


@cocotb.test()
async def test_data_patterns(dut):
    """Test various data patterns."""
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await reset_dut(dut)
    
    patterns = [
        [0x00, 0xFF],           # Min/max
        [0xAA, 0x55],           # Alternating bits
        [0x01, 0x02, 0x04, 0x08],  # Walking ones
    ]
    
    for pattern in patterns:
        # Write pattern
        for data in pattern:
            await write_fifo(dut, data)
            await RisingEdge(dut.clk)
        
        # Read and verify
        for expected in pattern:
            actual = await read_fifo(dut)
            assert actual == expected, f"Pattern error: expected {hex(expected)}, got {hex(actual)}"
    
    cocotb.log.info("Data patterns test PASSED")


