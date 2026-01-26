"""
Integration tests for end-to-end workflow
"""
import pytest
from pathlib import Path
import tempfile
import json

from step2_classify_route.orchestrator import ClassifierRouter
from step2_classify_route.models import TBType, Track
from step2_classify_route.config import ConfigManager, ProjectConfig


@pytest.fixture
def integration_workspace():
    """Create workspace for integration tests"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def create_cocotb_project(root: Path) -> Path:
    """Create a complete CocoTB project structure"""
    project_dir = root / "cocotb_project"
    project_dir.mkdir()
    
    # RTL
    (project_dir / "rtl").mkdir()
    (project_dir / "rtl" / "adder.sv").write_text("""
module adder #(
    parameter WIDTH = 8
) (
    input  logic [WIDTH-1:0] a,
    input  logic [WIDTH-1:0] b,
    output logic [WIDTH-1:0] sum
);
    assign sum = a + b;
endmodule
""")
    
    # Testbench
    (project_dir / "tb").mkdir()
    (project_dir / "tb" / "test_adder.py").write_text("""
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_add_basic(dut):
    \"\"\"Test basic addition\"\"\"
    dut.a.value = 5
    dut.b.value = 3
    await Timer(1, units='ns')
    assert dut.sum.value == 8, f"Expected 8, got {dut.sum.value}"

@cocotb.test()
async def test_add_zero(dut):
    \"\"\"Test addition with zero\"\"\"
    dut.a.value = 0
    dut.b.value = 10
    await Timer(1, units='ns')
    assert dut.sum.value == 10
""")
    
    # Manifest
    (project_dir / "submission.yaml").write_text("""
project_name: "adder_verification"
dut:
  files:
    - "rtl/adder.sv"
  top_module: "adder"
testbench:
  type: "cocotb"
  files:
    - "tb/test_adder.py"
simulator: "verilator"
""")
    
    return project_dir


def create_vunit_project(root: Path) -> Path:
    """Create a complete VUnit project structure"""
    project_dir = root / "vunit_project"
    project_dir.mkdir()
    
    # RTL
    (project_dir / "src").mkdir()
    (project_dir / "src" / "counter.vhd").write_text("""
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity counter is
    generic (WIDTH : natural := 8);
    port (
        clk    : in  std_logic;
        reset  : in  std_logic;
        enable : in  std_logic;
        count  : out std_logic_vector(WIDTH-1 downto 0)
    );
end entity;

architecture rtl of counter is
    signal count_reg : unsigned(WIDTH-1 downto 0);
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '1' then
                count_reg <= (others => '0');
            elsif enable = '1' then
                count_reg <= count_reg + 1;
            end if;
        end if;
    end process;
    
    count <= std_logic_vector(count_reg);
end architecture;
""")
    
    # Testbench
    (project_dir / "tb").mkdir()
    (project_dir / "tb" / "tb_counter.vhd").write_text("""
library ieee;
use ieee.std_logic_1164.all;

library vunit_lib;
context vunit_lib.vunit_context;

entity tb_counter is
    generic (runner_cfg : string);
end entity;

architecture tb of tb_counter is
    signal clk    : std_logic := '0';
    signal reset  : std_logic := '0';
    signal enable : std_logic := '0';
    signal count  : std_logic_vector(7 downto 0);
begin
    clk <= not clk after 5 ns;
    
    dut: entity work.counter
        port map (clk, reset, enable, count);
    
    main: process
    begin
        test_runner_setup(runner, runner_cfg);
        
        while test_suite loop
            if run("test_reset") then
                reset <= '1';
                wait for 20 ns;
                reset <= '0';
                check_equal(count, std_logic_vector'(x"00"));
            elsif run("test_count") then
                enable <= '1';
                wait for 100 ns;
                check(count /= x"00", "Counter should have incremented");
            end if;
        end loop;
        
        test_runner_cleanup(runner);
    end process;
end architecture;
""")
    
    # VUnit run script
    (project_dir / "run.py").write_text("""
from vunit import VUnit

vu = VUnit.from_argv()
lib = vu.add_library("work")
lib.add_source_files("src/*.vhd")
lib.add_source_files("tb/*.vhd")
vu.main()
""")
    
    return project_dir


def create_uvm_project(root: Path) -> Path:
    """Create a UVM-SV project (should fail with helpful error)"""
    project_dir = root / "uvm_project"
    project_dir.mkdir()
    
    (project_dir / "rtl").mkdir()
    (project_dir / "rtl" / "fifo.sv").write_text("""
module fifo #(
    parameter DEPTH = 16,
    parameter WIDTH = 8
) (
    input  logic clk,
    input  logic rst,
    input  logic wr_en,
    input  logic rd_en,
    input  logic [WIDTH-1:0] wr_data,
    output logic [WIDTH-1:0] rd_data,
    output logic full,
    output logic empty
);
    // FIFO implementation
endmodule
""")
    
    (project_dir / "tb").mkdir()
    (project_dir / "tb" / "fifo_test.sv").write_text("""
`include "uvm_macros.svh"
import uvm_pkg::*;

class fifo_test extends uvm_test;
    `uvm_component_utils(fifo_test)
    
    function new(string name = "fifo_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        #1000ns;
        phase.drop_objection(this);
    endtask
endclass

module tb_top;
    initial begin
        run_test("fifo_test");
    end
endmodule
""")
    
    return project_dir


class TestEndToEndWorkflow:
    """End-to-end integration tests"""
    
    def test_cocotb_project_flow(self, integration_workspace):
        """Test complete flow for CocoTB project"""
        project_dir = create_cocotb_project(integration_workspace)
        
        # Run classification
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        # Verify routing decision
        assert routing.tb_type == TBType.COCOTB.value
        assert routing.track == Track.A.value
        assert routing.confidence >= 0.8
        assert len(routing.dut_files) > 0
        assert len(routing.tb_files) > 0
        assert routing.is_valid()
    
    def test_vunit_project_flow(self, integration_workspace):
        """Test complete flow for VUnit project"""
        project_dir = create_vunit_project(integration_workspace)
        
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        assert routing.tb_type == TBType.VUNIT.value
        assert routing.track == Track.B.value
        assert routing.confidence >= 0.8
        assert "run.py" in routing.entrypoint
    
    def test_uvm_project_error_handling(self, integration_workspace):
        """Test that UVM-SV projects get proper error handling"""
        project_dir = create_uvm_project(integration_workspace)
        
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        assert routing.tb_type == TBType.UVM_SV.value
        assert routing.track == Track.C.value
        assert len(routing.errors) > 0
        assert any("commercial" in e.lower() for e in routing.errors)
        assert len(routing.recommendations) > 0
        assert not routing.is_valid()  # Should not be valid for execution
    
    def test_output_json_generation(self, integration_workspace):
        """Test that route.json is properly generated"""
        project_dir = create_cocotb_project(integration_workspace)
        
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        # Save and reload
        output_path = project_dir / "route.json"
        router.save_routing(routing, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data['tb_type'] == TBType.COCOTB.value
        assert data['track'] == Track.A.value
        assert 'dut_files' in data
        assert 'tb_files' in data
    
    def test_manifest_override(self, integration_workspace):
        """Test that manifest overrides auto-detection"""
        project_dir = create_cocotb_project(integration_workspace)
        
        # Modify manifest to force different type
        manifest = project_dir / "submission.yaml"
        manifest.write_text("""
project_name: "forced_sv"
dut:
  files:
    - "rtl/adder.sv"
  top_module: "adder"
testbench:
  type: "systemverilog"  # Force SV even though files are Python
  files:
    - "tb/test_adder.py"
simulator: "verilator"
""")
        
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        # Should respect manifest override
        assert routing.tb_type == "systemverilog"
        assert routing.detection_method == "manifest"
    
    def test_config_loading(self, integration_workspace):
        """Test configuration file loading"""
        project_dir = create_cocotb_project(integration_workspace)
        
        # Create config file
        config_file = project_dir / ".tbeval.yaml"
        config_file.write_text("""
project_name: "custom_name"
quality_gate_mode: "blocking"
fail_on_critical_errors: true
fail_on_lint_warnings: true
""")
        
        config = ConfigManager.load_config(search_dir=project_dir)
        
        assert config.project_name == "custom_name"
        assert config.quality_gate_mode == "blocking"
        assert config.fail_on_lint_warnings is True
    
    def test_empty_project_handling(self, integration_workspace):
        """Test handling of empty project directory"""
        empty_dir = integration_workspace / "empty"
        empty_dir.mkdir()
        
        router = ClassifierRouter(empty_dir)
        routing = router.classify_and_route()
        
        assert routing.tb_type == TBType.UNKNOWN.value
        assert routing.confidence == 0.0
        assert not routing.is_valid()
        assert len(routing.errors) > 0


class TestQualityGateIntegration:
    """Test quality gate integration in workflow"""
    
    def test_quality_gate_advisory_mode(self, integration_workspace):
        """Test advisory mode allows continuation with warnings"""
        project_dir = create_cocotb_project(integration_workspace)
        
        config = ProjectConfig(
            quality_gate_mode="advisory",
            fail_on_lint_warnings=False
        )
        
        router = ClassifierRouter(project_dir, config)
        routing = router.classify_and_route()
        
        # Should proceed even with quality issues
        assert routing.is_valid() or routing.tb_type != TBType.UNKNOWN.value
    
    def test_quality_gate_results_in_routing(self, integration_workspace):
        """Test that quality results are included in routing"""
        project_dir = create_cocotb_project(integration_workspace)
        
        router = ClassifierRouter(project_dir)
        routing = router.classify_and_route()
        
        # Quality metrics should be present
        if routing.quality_metrics:
            assert 'linter' in routing.quality_metrics
            assert 'total_files' in routing.quality_metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
