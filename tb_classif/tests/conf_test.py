"""
Shared pytest fixtures for all tests
"""
import pytest
from pathlib import Path
import shutil
import tempfile

from step2_classify_route.models import ProjectConfig


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def sample_projects_dir():
    """Path to sample projects for testing"""
    return Path(__file__).parent / "fixtures" / "sample_projects"


@pytest.fixture
def default_config():
    """Default project configuration"""
    return ProjectConfig(
        project_name="test_project",
        quality_gate_mode="advisory",
        fail_on_critical_errors=True,
        fail_on_syntax_errors=True
    )


@pytest.fixture
def strict_config():
    """Strict quality gate configuration"""
    return ProjectConfig(
        project_name="test_project",
        quality_gate_mode="blocking",
        fail_on_critical_errors=True,
        fail_on_syntax_errors=True,
        fail_on_lint_warnings=True,
        fail_on_style_issues=False
    )


@pytest.fixture
def cocotb_project(temp_workspace):
    """Create sample CocoTB project"""
    project_dir = temp_workspace / "cocotb_test"
    project_dir.mkdir()
    
    # Create structure
    (project_dir / "rtl").mkdir()
    (project_dir / "tb").mkdir()
    
    # DUT
    (project_dir / "rtl" / "adder.sv").write_text("""
module adder #(parameter WIDTH = 8) (
    input  logic [WIDTH-1:0] a,
    input  logic [WIDTH-1:0] b,
    output logic [WIDTH-1:0] sum
);
    assign sum = a + b;
endmodule
""")
    
    # Testbench
    (project_dir / "tb" / "test_adder.py").write_text("""
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_add_basic(dut):
    dut.a.value = 5
    dut.b.value = 3
    await Timer(1, units='ns')
    assert dut.sum.value == 8, "Addition failed"
""")
    
    # Manifest
    (project_dir / "submission.yaml").write_text("""
project_name: "adder_test"
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
