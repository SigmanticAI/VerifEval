"""
Test suite for quality gate (Verible/GHDL integration)
"""
import pytest
from pathlib import Path
import tempfile
import subprocess

from step2_classify_route.quality_gate.verible_linter import VeribleLinter
from step2_classify_route.quality_gate.ghdl_checker import GHDLChecker
from step2_classify_route.models import QualityReport, Violation


def is_verible_available() -> bool:
    """Check if Verible is installed"""
    try:
        result = subprocess.run(
            ['verible-verilog-lint', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_ghdl_available() -> bool:
    """Check if GHDL is installed"""
    try:
        result = subprocess.run(
            ['ghdl', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestVeribleLinter:
    """Test Verible linter integration"""
    
    def test_check_tool_available(self, temp_dir):
        """Test tool availability check"""
        linter = VeribleLinter([], temp_dir)
        available = linter.check_tool_available()
        
        # Should match our detection function
        assert available == is_verible_available()
    
    @pytest.mark.skipif(not is_verible_available(), reason="Verible not installed")
    def test_lint_valid_file(self, temp_dir):
        """Test linting valid SystemVerilog file"""
        test_file = temp_dir / "valid.sv"
        test_file.write_text("""
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
        
        linter = VeribleLinter([test_file], temp_dir)
        report = linter.run_checks()
        
        assert report is not None
        assert report.linter in ["verible", "verible-syntax", "verible-lint"]
        assert report.files_checked == 1
    
    @pytest.mark.skipif(not is_verible_available(), reason="Verible not installed")
    def test_lint_syntax_error(self, temp_dir):
        """Test linting file with syntax error"""
        test_file = temp_dir / "syntax_error.sv"
        test_file.write_text("""
module broken
    // Missing port list and semicolon
    input a
    output b
endmodule
""")
        
        linter = VeribleLinter([test_file], temp_dir)
        report = linter.run_checks()
        
        assert report is not None
        assert report.critical_errors > 0
        assert report.status == "fail"
    
    def test_lint_without_verible(self, temp_dir):
        """Test graceful handling when Verible not available"""
        test_file = temp_dir / "test.sv"
        test_file.write_text("module test; endmodule")
        
        linter = VeribleLinter([test_file], temp_dir)
        
        # Mock unavailability
        linter.check_tool_available = lambda: False
        
        report = linter.run_checks()
        
        assert report is not None
        assert report.status == "skipped"
        assert report.critical_errors >= 1  # Tool missing error
    
    @pytest.mark.skipif(not is_verible_available(), reason="Verible not installed")
    def test_lint_multiple_files(self, temp_dir):
        """Test linting multiple files"""
        files = []
        for i in range(3):
            f = temp_dir / f"module_{i}.sv"
            f.write_text(f"module module_{i}; endmodule")
            files.append(f)
        
        linter = VeribleLinter(files, temp_dir)
        report = linter.run_checks()
        
        assert report.total_files == 3
        assert report.files_checked == 3


class TestGHDLChecker:
    """Test GHDL syntax checker integration"""
    
    def test_check_tool_available(self, temp_dir):
        """Test tool availability check"""
        checker = GHDLChecker([], temp_dir)
        available = checker.check_tool_available()
        
        assert available == is_ghdl_available()
    
    @pytest.mark.skipif(not is_ghdl_available(), reason="GHDL not installed")
    def test_check_valid_vhdl(self, temp_dir):
        """Test checking valid VHDL file"""
        test_file = temp_dir / "valid.vhd"
        test_file.write_text("""
library ieee;
use ieee.std_logic_1164.all;

entity adder is
    port (
        a : in std_logic_vector(7 downto 0);
        b : in std_logic_vector(7 downto 0);
        sum : out std_logic_vector(7 downto 0)
    );
end entity;

architecture rtl of adder is
begin
    sum <= std_logic_vector(unsigned(a) + unsigned(b));
end architecture;
""")
        
        checker = GHDLChecker([test_file], temp_dir)
        report = checker.run_checks()
        
        assert report is not None
        assert report.linter == "ghdl"
        assert report.files_checked == 1
    
    @pytest.mark.skipif(not is_ghdl_available(), reason="GHDL not installed")
    def test_check_syntax_error_vhdl(self, temp_dir):
        """Test checking VHDL file with syntax error"""
        test_file = temp_dir / "syntax_error.vhd"
        test_file.write_text("""
entity broken is
    port (
        a : in integer
        -- Missing semicolon and closing
    end entity;
""")
        
        checker = GHDLChecker([test_file], temp_dir)
        report = checker.run_checks()
        
        assert report is not None
        assert report.critical_errors > 0
        assert report.status == "fail"
    
    def test_check_without_ghdl(self, temp_dir):
        """Test graceful handling when GHDL not available"""
        test_file = temp_dir / "test.vhd"
        test_file.write_text("entity test is end entity;")
        
        checker = GHDLChecker([test_file], temp_dir)
        
        # Mock unavailability
        checker.check_tool_available = lambda: False
        
        report = checker.run_checks()
        
        assert report is not None
        assert report.status == "skipped"


class TestQualityReportModel:
    """Test QualityReport data model"""
    
    def test_has_critical_errors_true(self):
        """Test has_critical_errors returns True when errors exist"""
        report = QualityReport(
            status="fail",
            linter="verible",
            timestamp="",
            total_files=1,
            files_checked=1,
            total_violations=5,
            critical_errors=3,
            warnings=2,
            style_issues=0,
            files=[]
        )
        
        assert report.has_critical_errors() is True
    
    def test_has_critical_errors_false(self):
        """Test has_critical_errors returns False when no errors"""
        report = QualityReport(
            status="pass",
            linter="verible",
            timestamp="",
            total_files=1,
            files_checked=1,
            total_violations=2,
            critical_errors=0,
            warnings=2,
            style_issues=0,
            files=[]
        )
        
        assert report.has_critical_errors() is False
    
    def test_to_dict(self):
        """Test QualityReport serialization"""
        report = QualityReport(
            status="pass",
            linter="verible",
            timestamp="2024-01-01T00:00:00Z",
            total_files=2,
            files_checked=2,
            total_violations=0,
            critical_errors=0,
            warnings=0,
            style_issues=0,
            files=[]
        )
        
        data = report.to_dict()
        
        assert data['status'] == "pass"
        assert data['linter'] == "verible"
        assert data['total_files'] == 2


class TestViolationModel:
    """Test Violation data model"""
    
    def test_violation_creation(self):
        """Test creating a Violation"""
        violation = Violation(
            file="test.sv",
            line=10,
            column=5,
            severity="error",
            rule="syntax",
            message="Unexpected token"
        )
        
        assert violation.file == "test.sv"
        assert violation.line == 10
        assert violation.severity == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
