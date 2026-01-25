"""
Test suite for testbench detectors
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from step2_classify_route.detectors.cocotb_detector import CocoTBDetector
from step2_classify_route.detectors.pyuvm_detector import PyUVMDetector
from step2_classify_route.detectors.uvm_sv_detector import UVMSVDetector
from step2_classify_route.detectors.vunit_detector import VUnitDetector
from step2_classify_route.detectors.hdl_detector import HDLDetector
from step2_classify_route.models import TBType


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


class TestCocoTBDetector:
    """Test CocoTB detector"""
    
    def test_detect_cocotb_basic(self, temp_dir):
        """Test basic CocoTB detection"""
        test_file = temp_dir / "test_basic.py"
        test_file.write_text("""
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_adder(dut):
    dut.a.value = 5
    dut.b.value = 3
    await Timer(1, units='ns')
    assert dut.sum.value == 8
""")
        
        detector = CocoTBDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.COCOTB
        assert result.confidence >= 0.85
    
    def test_detect_cocotb_no_decorator(self, temp_dir):
        """Test CocoTB detection without decorator"""
        test_file = temp_dir / "test_no_decorator.py"
        test_file.write_text("""
import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock

async def my_test(dut):
    pass
""")
        
        detector = CocoTBDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.COCOTB
        # Lower confidence without @cocotb.test
        assert result.confidence < 0.90
    
    def test_no_detection_plain_python(self, temp_dir):
        """Test that plain Python is not detected as CocoTB"""
        test_file = temp_dir / "plain.py"
        test_file.write_text("""
def add(a, b):
    return a + b

if __name__ == '__main__':
    print(add(2, 3))
""")
        
        detector = CocoTBDetector()
        result = detector.detect(test_file)
        
        assert result is None


class TestPyUVMDetector:
    """Test PyUVM detector"""
    
    def test_detect_pyuvm(self, temp_dir):
        """Test PyUVM detection"""
        test_file = temp_dir / "test_pyuvm.py"
        test_file.write_text("""
from pyuvm import *

class MyTest(uvm_test):
    def __init__(self, name, parent):
        super().__init__(name, parent)
    
    async def run_phase(self):
        self.raise_objection()
        await Timer(100, "ns")
        self.drop_objection()
""")
        
        detector = PyUVMDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.PYUVM
        assert result.confidence >= 0.75


class TestUVMSVDetector:
    """Test UVM SystemVerilog detector"""
    
    def test_detect_uvm_sv(self, temp_dir):
        """Test UVM-SV detection"""
        test_file = temp_dir / "test_uvm.sv"
        test_file.write_text("""
`include "uvm_macros.svh"
import uvm_pkg::*;

class my_test extends uvm_test;
    `uvm_component_utils(my_test)
    
    function new(string name = "my_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        #100ns;
        phase.drop_objection(this);
    endtask
endclass
""")
        
        detector = UVMSVDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.UVM_SV
        assert result.confidence >= 0.85
        assert result.metadata['requires_commercial_sim'] == True


class TestVUnitDetector:
    """Test VUnit detector"""
    
    def test_detect_vunit_python(self, temp_dir):
        """Test VUnit Python runner detection"""
        test_file = temp_dir / "run.py"
        test_file.write_text("""
from vunit import VUnit

vu = VUnit.from_argv()
lib = vu.add_library("lib")
lib.add_source_files("*.vhd")
vu.main()
""")
        
        detector = VUnitDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.VUNIT
        assert result.confidence >= 0.90
    
    def test_detect_vunit_vhdl(self, temp_dir):
        """Test VUnit VHDL testbench detection"""
        test_file = temp_dir / "tb_example.vhd"
        test_file.write_text("""
library vunit_lib;
context vunit_lib.vunit_context;

entity tb_example is
    generic (runner_cfg : string);
end entity;

architecture tb of tb_example is
begin
    main : process
    begin
        test_runner_setup(runner, runner_cfg);
        
        while test_suite loop
            if run("test_1") then
                -- test code
            end if;
        end loop;
        
        test_runner_cleanup(runner);
    end process;
end architecture;
""")
        
        detector = VUnitDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.VUNIT


class TestHDLDetector:
    """Test generic HDL detector"""
    
    def test_detect_systemverilog_tb(self, temp_dir):
        """Test SystemVerilog testbench detection"""
        test_file = temp_dir / "tb_adder.sv"
        test_file.write_text("""
`timescale 1ns/1ps

module tb_adder;
    logic [7:0] a, b, sum;
    
    adder dut (
        .a(a),
        .b(b),
        .sum(sum)
    );
    
    initial begin
        a = 8'd5;
        b = 8'd3;
        #10;
        $display("Sum = %d", sum);
        $finish;
    end
endmodule
""")
        
        detector = HDLDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.SYSTEMVERILOG
        assert result.confidence >= 0.60
    
    def test_detect_vhdl_tb(self, temp_dir):
        """Test VHDL testbench detection"""
        test_file = temp_dir / "tb_adder.vhd"
        test_file.write_text("""
entity tb_adder is
end entity;

architecture test of tb_adder is
    signal a, b, sum : integer;
begin
    dut: entity work.adder
        port map (a => a, b => b, sum => sum);
    
    process
    begin
        a <= 5;
        b <= 3;
        wait for 10 ns;
        assert sum = 8 report "Test failed" severity error;
        wait;
    end process;
end architecture;
""")
        
        detector = HDLDetector()
        result = detector.detect(test_file)
        
        assert result is not None
        assert result.tb_type == TBType.VHDL


def test_detector_priority():
    """Test that detectors don't conflict"""
    # CocoTB should take priority over plain Python
    # UVM-SV should take priority over plain SV
    # etc.
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
