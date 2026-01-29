"""
Questa compilation checker
"""
from pathlib import Path
from typing import List
import re
import time
import subprocess
import os

from .base import BaseQualityGate
from ..models import QualityReport, FileQualityReport, Violation


class QuestaChecker(BaseQualityGate):
    """Questa compilation checker for SystemVerilog/UVM"""
    
    def __init__(self, files: List[Path], root_dir: Path, questa_path: str = None):
        super().__init__(files, root_dir)
        self.tool_name = "questa"
        self.questa_path = questa_path  # Optional explicit path
    
    def check_tool_available(self) -> bool:
        """Check if Questa is installed and licensed"""
        try:
            # Use explicit path if provided
            if self.questa_path:
                vsim_cmd = os.path.join(self.questa_path, 'bin', 'vsim')
            else:
                vsim_cmd = 'vsim'
            
            result = subprocess.run(
                [vsim_cmd, '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def run_checks(self) -> QualityReport:
        """Run Questa compilation check"""
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
                        message="Questa not found. Ensure vsim is in PATH or configure questa_path"
                    )]
                )
            ]
            report.critical_errors = 1
            return report
        
        start_time = time.time()
        
        # Run compilation check
        file_reports = []
        total_errors = 0
        total_warnings = 0
        
        for file_path in self.files:
            # Use vlog for Verilog/SystemVerilog compilation check
            cmd = ['vlog', '-work', 'work', '-lint', str(file_path)]
            
            result = self.run_command(cmd)
            
            violations = self._parse_output(result.stderr + result.stdout, str(file_path))
            
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
            linter="questa",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_files=len(self.files),
            files_checked=len(self.files),
            total_violations=total_errors + total_warnings,
            critical_errors=total_errors,
            warnings=total_warnings,
            style_issues=0,
            files=file_reports,
            violations_by_category={"compilation": total_errors, "warnings": total_warnings},
            execution_time_ms=execution_time
        )
    
    def _parse_output(self, output: str, file_path: str) -> List[Violation]:
        """Parse Questa vlog output"""
        violations = []
        
        # Pattern: ** Error: file(line): message
        # Pattern: ** Warning: file(line): message
        error_pattern = r'\*\*\s*(Error|Warning):\s*([^(]+)\((\d+)\):\s*(.+)'
        
        for line in output.split('\n'):
            match = re.match(error_pattern, line)
            if match:
                severity = match.group(1).lower()
                file = match.group(2).strip()
                lineno = int(match.group(3))
                message = match.group(4).strip()
                
                violations.append(Violation(
                    file=file,
                    line=lineno,
                    column=0,
                    severity=severity,
                    rule="vlog_compilation",
                    message=message
                ))
        
        return violations
