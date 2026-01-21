"""
Single-file testbench for 8-bit Adder.

This is a simple, self-contained cocotb testbench demonstrating
basic verification patterns.
"""

import cocotb
from cocotb.triggers import Timer
import random


@cocotb.test()
async def test_basic_addition(dut):
    """Test basic addition operations."""
    
    # Test case 1: 0 + 0
    dut.a.value = 0
    dut.b.value = 0
    dut.cin.value = 0
    await Timer(1, units='ns')
    
    assert dut.sum.value == 0, f"Expected sum=0, got {dut.sum.value}"
    assert dut.cout.value == 0, f"Expected cout=0, got {dut.cout.value}"
    
    # Test case 2: 1 + 1
    dut.a.value = 1
    dut.b.value = 1
    dut.cin.value = 0
    await Timer(1, units='ns')
    
    assert dut.sum.value == 2, f"Expected sum=2, got {dut.sum.value}"
    assert dut.cout.value == 0, f"Expected cout=0, got {dut.cout.value}"
    
    # Test case 3: 100 + 50
    dut.a.value = 100
    dut.b.value = 50
    dut.cin.value = 0
    await Timer(1, units='ns')
    
    assert dut.sum.value == 150, f"Expected sum=150, got {dut.sum.value}"
    
    cocotb.log.info("Basic addition tests PASSED")


@cocotb.test()
async def test_carry_in(dut):
    """Test carry-in functionality."""
    
    # With carry in
    dut.a.value = 10
    dut.b.value = 20
    dut.cin.value = 1
    await Timer(1, units='ns')
    
    assert dut.sum.value == 31, f"Expected sum=31 (10+20+1), got {dut.sum.value}"
    
    # Carry in at boundary
    dut.a.value = 255
    dut.b.value = 0
    dut.cin.value = 1
    await Timer(1, units='ns')
    
    assert dut.sum.value == 0, f"Expected sum=0 (overflow), got {dut.sum.value}"
    assert dut.cout.value == 1, f"Expected cout=1, got {dut.cout.value}"
    
    cocotb.log.info("Carry-in tests PASSED")


@cocotb.test()
async def test_overflow(dut):
    """Test overflow/carry-out behavior."""
    
    # Test overflow: 255 + 1 = 0 with cout=1
    dut.a.value = 255
    dut.b.value = 1
    dut.cin.value = 0
    await Timer(1, units='ns')
    
    assert dut.sum.value == 0, f"Expected sum=0, got {dut.sum.value}"
    assert dut.cout.value == 1, f"Expected cout=1, got {dut.cout.value}"
    
    # Test overflow: 200 + 100 = 44 with cout=1
    dut.a.value = 200
    dut.b.value = 100
    dut.cin.value = 0
    await Timer(1, units='ns')
    
    assert dut.sum.value == 44, f"Expected sum=44, got {dut.sum.value}"
    assert dut.cout.value == 1, f"Expected cout=1, got {dut.cout.value}"
    
    # Max overflow: 255 + 255 + 1 = 255 with cout=1
    dut.a.value = 255
    dut.b.value = 255
    dut.cin.value = 1
    await Timer(1, units='ns')
    
    assert dut.sum.value == 255, f"Expected sum=255, got {dut.sum.value}"
    assert dut.cout.value == 1, f"Expected cout=1, got {dut.cout.value}"
    
    cocotb.log.info("Overflow tests PASSED")


@cocotb.test()
async def test_random_values(dut):
    """Test with random values."""
    
    for _ in range(50):
        a = random.randint(0, 255)
        b = random.randint(0, 255)
        cin = random.randint(0, 1)
        
        dut.a.value = a
        dut.b.value = b
        dut.cin.value = cin
        await Timer(1, units='ns')
        
        expected_sum = (a + b + cin) & 0xFF
        expected_cout = 1 if (a + b + cin) > 255 else 0
        
        assert dut.sum.value == expected_sum, \
            f"Random test failed: {a} + {b} + {cin} = {dut.sum.value}, expected {expected_sum}"
        assert dut.cout.value == expected_cout, \
            f"Carry test failed: expected cout={expected_cout}, got {dut.cout.value}"
    
    cocotb.log.info("Random value tests PASSED (50 iterations)")


@cocotb.test()
async def test_boundary_values(dut):
    """Test boundary/edge cases."""
    
    # All zeros
    dut.a.value = 0
    dut.b.value = 0
    dut.cin.value = 0
    await Timer(1, units='ns')
    assert dut.sum.value == 0 and dut.cout.value == 0
    
    # All ones (max values)
    dut.a.value = 255
    dut.b.value = 255
    dut.cin.value = 1
    await Timer(1, units='ns')
    assert dut.sum.value == 255 and dut.cout.value == 1
    
    # Alternating bits
    dut.a.value = 0xAA
    dut.b.value = 0x55
    dut.cin.value = 0
    await Timer(1, units='ns')
    assert dut.sum.value == 0xFF, f"Expected 0xFF, got {hex(dut.sum.value)}"
    
    cocotb.log.info("Boundary value tests PASSED")


