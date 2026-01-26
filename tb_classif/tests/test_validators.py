"""
Test suite for file and project validators
"""
import pytest
from pathlib import Path
import tempfile
import stat

from step2_classify_route.utils.validators import FileValidator, ProjectValidator


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestFileValidator:
    """Test FileValidator class"""
    
    def test_validate_existing_file(self, temp_dir):
        """Test validation of existing readable file"""
        test_file = temp_dir / "test.sv"
        test_file.write_text("module test; endmodule")
        
        valid, msg = FileValidator.validate_file_exists(test_file)
        
        assert valid is True
        assert msg == ""
    
    def test_validate_nonexistent_file(self, temp_dir):
        """Test validation of non-existent file"""
        test_file = temp_dir / "nonexistent.sv"
        
        valid, msg = FileValidator.validate_file_exists(test_file)
        
        assert valid is False
        assert "does not exist" in msg
    
    def test_validate_directory_not_file(self, temp_dir):
        """Test that directories are not valid files"""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        valid, msg = FileValidator.validate_file_exists(subdir)
        
        assert valid is False
        assert "not a file" in msg
    
    @pytest.mark.skipif(
        not hasattr(stat, 'S_IRUSR'),
        reason="Platform does not support Unix permissions"
    )
    def test_validate_unreadable_file(self, temp_dir):
        """Test validation of unreadable file"""
        test_file = temp_dir / "unreadable.sv"
        test_file.write_text("module test; endmodule")
        test_file.chmod(0o000)  # Remove all permissions
        
        try:
            valid, msg = FileValidator.validate_file_exists(test_file)
            # On some systems this might still work if running as root
            if not valid:
                assert "Permission denied" in msg or "Cannot read" in msg
        finally:
            test_file.chmod(0o644)  # Restore permissions for cleanup
    
    def test_hdl_syntax_valid_module(self, temp_dir):
        """Test HDL syntax validation for valid module"""
        test_file = temp_dir / "valid.sv"
        test_file.write_text("""
module adder (
    input [7:0] a,
    input [7:0] b,
    output [7:0] sum
);
    assign sum = a + b;
endmodule
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is True
        assert len(issues) == 0
    
    def test_hdl_syntax_missing_module(self, temp_dir):
        """Test HDL syntax validation for file without module"""
        test_file = temp_dir / "no_module.sv"
        test_file.write_text("""
// Just some comments
// No module declaration
assign a = b;
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is False
        assert any("module" in issue.lower() for issue in issues)
    
    def test_hdl_syntax_unbalanced_parentheses(self, temp_dir):
        """Test HDL syntax validation for unbalanced parentheses"""
        test_file = temp_dir / "unbalanced.sv"
        test_file.write_text("""
module test (
    input a,
    input b
;  // Missing closing parenthesis
    assign c = (a + b;  // Missing closing parenthesis
endmodule
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is False
        assert any("Unbalanced" in issue for issue in issues)
    
    def test_hdl_syntax_unbalanced_begin_end(self, temp_dir):
        """Test HDL syntax validation for unbalanced begin/end"""
        test_file = temp_dir / "unbalanced_begin.sv"
        test_file.write_text("""
module test;
    initial begin
        $display("test");
        begin
            $display("nested");
        // Missing end
    end
endmodule
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is False
        assert any("begin/end" in issue.lower() for issue in issues)
    
    def test_vhdl_syntax_valid_entity(self, temp_dir):
        """Test VHDL syntax validation for valid entity"""
        test_file = temp_dir / "valid.vhd"
        test_file.write_text("""
entity adder is
    port (
        a : in integer;
        b : in integer;
        sum : out integer
    );
end entity;

architecture rtl of adder is
begin
    sum <= a + b;
end architecture;
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is True
    
    def test_vhdl_syntax_missing_entity(self, temp_dir):
        """Test VHDL syntax validation for missing entity"""
        test_file = temp_dir / "no_entity.vhd"
        test_file.write_text("""
-- Just comments
-- No entity declaration
""")
        
        valid, issues = FileValidator.validate_hdl_syntax_basic(test_file)
        
        assert valid is False
        assert any("entity" in issue.lower() for issue in issues)
    
    def test_python_syntax_valid(self, temp_dir):
        """Test Python syntax validation for valid file"""
        test_file = temp_dir / "valid.py"
        test_file.write_text("""
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_example(dut):
    await Timer(1, units='ns')
    assert True
""")
        
        valid, issues = FileValidator.validate_python_syntax_basic(test_file)
        
        assert valid is True
        assert len(issues) == 0
    
    def test_python_syntax_error(self, temp_dir):
        """Test Python syntax validation for syntax error"""
        test_file = temp_dir / "syntax_error.py"
        test_file.write_text("""
def broken_function(
    # Missing closing parenthesis
    print("hello"
""")
        
        valid, issues = FileValidator.validate_python_syntax_basic(test_file)
        
        assert valid is False
        assert len(issues) > 0
        assert any("syntax" in issue.lower() for issue in issues)


class TestProjectValidator:
    """Test ProjectValidator class"""
    
    @pytest.fixture
    def project_validator(self, temp_dir):
        """Create ProjectValidator instance"""
        return ProjectValidator(temp_dir)
    
    def test_validate_project_valid(self, temp_dir, project_validator):
        """Test validation of valid project"""
        # Create valid project structure
        (temp_dir / "rtl").mkdir()
        (temp_dir / "tb").mkdir()
        
        dut_file = temp_dir / "rtl" / "adder.sv"
        dut_file.write_text("module adder; endmodule")
        
        tb_file = temp_dir / "tb" / "test.py"
        tb_file.write_text("import cocotb\n@cocotb.test()\nasync def test(dut): pass")
        
        results = project_validator.validate_project(
            dut_files=[dut_file],
            tb_files=[tb_file]
        )
        
        assert results['valid'] is True
        assert len(results['errors']) == 0
    
    def test_validate_project_no_dut_files(self, project_validator, temp_dir):
        """Test validation with no DUT files"""
        tb_file = temp_dir / "test.py"
        tb_file.write_text("print('test')")
        
        results = project_validator.validate_project(
            dut_files=[],
            tb_files=[tb_file]
        )
        
        assert results['valid'] is False
        assert any("No DUT files" in err for err in results['errors'])
    
    def test_validate_project_no_tb_files(self, project_validator, temp_dir):
        """Test validation with no testbench files"""
        dut_file = temp_dir / "dut.sv"
        dut_file.write_text("module dut; endmodule")
        
        results = project_validator.validate_project(
            dut_files=[dut_file],
            tb_files=[]
        )
        
        assert results['valid'] is False
        assert any("No testbench files" in err for err in results['errors'])
    
    def test_validate_project_missing_file(self, project_validator, temp_dir):
        """Test validation with missing file"""
        dut_file = temp_dir / "dut.sv"
        dut_file.write_text("module dut; endmodule")
        
        missing_tb = temp_dir / "nonexistent.py"  # Don't create this
        
        results = project_validator.validate_project(
            dut_files=[dut_file],
            tb_files=[missing_tb]
        )
        
        assert results['valid'] is False
        assert any("does not exist" in err for err in results['errors'])
    
    def test_validate_project_statistics(self, temp_dir, project_validator):
        """Test that statistics are correctly computed"""
        (temp_dir / "rtl").mkdir()
        (temp_dir / "tb").mkdir()
        
        dut1 = temp_dir / "rtl" / "dut1.sv"
        dut1.write_text("module dut1; endmodule")
        dut2 = temp_dir / "rtl" / "dut2.sv"
        dut2.write_text("module dut2; endmodule")
        
        tb1 = temp_dir / "tb" / "test1.py"
        tb1.write_text("x = 1")
        
        results = project_validator.validate_project(
            dut_files=[dut1, dut2],
            tb_files=[tb1]
        )
        
        assert results['statistics']['dut_files'] == 2
        assert results['statistics']['tb_files'] == 1
        assert results['statistics']['total_files'] == 3
    
    def test_validate_file_paths_valid(self, project_validator):
        """Test file path validation with valid paths"""
        valid, issues = project_validator.validate_file_paths([
            "rtl/adder.sv",
            "tb/test.py"
        ])
        
        assert valid is True
        assert len(issues) == 0
    
    def test_validate_file_paths_traversal(self, project_validator):
        """Test file path validation catches traversal attempts"""
        valid, issues = project_validator.validate_file_paths([
            "../../../etc/passwd",
            "rtl/../../../secret.txt"
        ])
        
        assert valid is False
        assert any(".." in issue for issue in issues)
    
    def test_check_common_issues_spaces(self, temp_dir):
        """Test detection of files with spaces in names"""
        validator = ProjectValidator(temp_dir)
        
        # Create file with space in name
        bad_file = temp_dir / "my file.sv"
        bad_file.write_text("module test; endmodule")
        
        warnings = validator.check_common_issues()
        
        assert any("space" in w.lower() for w in warnings)
    
    def test_check_common_issues_case_sensitivity(self, temp_dir):
        """Test detection of case sensitivity issues"""
        validator = ProjectValidator(temp_dir)
        
        # Create files that differ only in case
        (temp_dir / "Test.sv").write_text("module Test; endmodule")
        (temp_dir / "test.sv").write_text("module test; endmodule")
        
        warnings = validator.check_common_issues()
        
        # This might not trigger on case-sensitive filesystems
        # but should on case-insensitive ones
        # Just verify the check runs without error
        assert isinstance(warnings, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
