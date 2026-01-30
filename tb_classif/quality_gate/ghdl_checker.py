"""
GHDL syntax checker for VHDL
"""
from pathlib import Path
from typing import List
import re
import time

from .base import BaseQualityGate
from ..models import QualityReport, FileQualityReport, Violation


class GHDLChecker(BaseQualityGate):
    """GHDL VHDL syntax checker"""
    
    def __init__(self, files: List[Path], root_dir: Path):
        super().__init__(files, root_dir)
        self.tool_name = "ghdl"
    
    def check_tool_available(self) -> bool:
        """Check if GHDL is installed"""
        try:
            result = self.run_command(['ghdl', '--version'])
            return result.returncode == 0
        except Exception:
            return False
    
    def run_checks(self) -> QualityReport:
        """Run GHDL syntax check"""
        if not self.check_tool_available():
            report = self.create_empty_report(status="skipped")
            report.files = [
                FileQualityReport(
                    path="N/A",
                    status="error",
                    violations=[Violation(
                        file="",
                        line=0,
                        column=0,
                        severity="error",
                        rule="tool_missing",
                        message="GHDL not found. Install: http://ghdl.free.fr/"
                    )]
                )
            ]
            report.critical_errors = 1
            return report
        
        start_time = time.time()
        
        file_reports = []
        total_errors = 0
        total_warnings = 0
        
        for file_path in self.files:
            # Run syntax check
            cmd = ['ghdl', '-s', '--std=08', str(file_path)]
            result = self.run_command(cmd)
            
            violations = self._parse_output(result.stderr, str(file_path))
            
            errors = sum(1 for v in violations if v.severity == "error")
            warnings = sum(1 for v in violations if v.severity == "warning")
            
            total_errors += errors
            total_warnings += warnings
            
            file_reports.append(FileQualityReport(
                path=str(file_path.relative_to(self.root_dir)),
                status="fail" if errors > 0 else ("warning" if warnings > 0 else "pass"),
                violations=violations
            ))
        
        execution_time = (time.time() - start_time) * 1000
        
        return QualityReport(
            status="fail" if total_errors > 0 else ("warning" if total_warnings > 0 else "pass"),
            linter="ghdl",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_files=len(self.files),
            files_checked=len(self.files),
            total_violations=total_errors + total_warnings,
            critical_errors=total_errors,
            warnings=total_warnings,
            style_issues=0,
            files=file_reports,
            violations_by_category={"syntax": total_errors, "warnings": total_warnings},
            execution_time_ms=execution_time
        )
    
    def _parse_output(self, output: str, file_path: str) -> List[Violation]:
        """Parse GHDL output"""
        violations = []
        
        # Pattern: file:line:col: error/warning: message
        pattern = r'(.+?):(\d+):(\d+):\s*(error|warning):\s*(.+)'
        
        for line in output.split('\n'):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                violations.append(Violation(
                    file=file_path,
                    line=int(match.group(2)),
                    column=int(match.group(3)),
                    severity=match.group(4).lower(),
                    rule="vhdl_syntax",
                    message=match.group(5)
                ))
        
        return violations
