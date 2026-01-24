"""
Verible linter integration for SystemVerilog
"""
from pathlib import Path
from typing import List, Optional, Dict
import json
import re
import time

from .base import BaseQualityGate
from ..models import QualityReport, FileQualityReport, Violation, QualityStatus


class VeribleLinter(BaseQualityGate):
    """Verible SystemVerilog linter integration"""
    
    def __init__(self, files: List[Path], root_dir: Path,
                 rules_config: Optional[Path] = None,
                 waiver_file: Optional[Path] = None):
        super().__init__(files, root_dir)
        self.tool_name = "verible"
        self.rules_config = rules_config
        self.waiver_file = waiver_file
    
    def check_tool_available(self) -> bool:
        """Check if Verible is installed"""
        try:
            result = self.run_command(['verible-verilog-lint', '--version'])
            return result.returncode == 0
        except Exception:
            return False
    
    def run_checks(self) -> QualityReport:
        """Run Verible linting"""
        if not self.check_tool_available():
            report = self.create_empty_report(status="skipped", reason="Verible not available")
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
                        message="Verible linter not found. Install: https://github.com/chipsalliance/verible"
                    )]
                )
            ]
            report.critical_errors = 1
            return report
        
        start_time = time.time()
        
        # Run syntax check first
        syntax_report = self._run_syntax_check()
        
        # If syntax errors, don't run linting
        if syntax_report.critical_errors > 0:
            execution_time = (time.time() - start_time) * 1000
            syntax_report.execution_time_ms = execution_time
            return syntax_report
        
        # Run linting
        lint_report = self._run_lint()
        
        execution_time = (time.time() - start_time) * 1000
        lint_report.execution_time_ms = execution_time
        
        return lint_report
    
    def _run_syntax_check(self) -> QualityReport:
        """Run Verible syntax checker"""
        file_reports = []
        total_errors = 0
        
        for file_path in self.files:
            cmd = [
                'verible-verilog-syntax',
                '--error_limit=0',
                str(file_path)
            ]
            
            result = self.run_command(cmd)
            
            violations = []
            if result.returncode != 0:
                # Parse syntax errors
                violations = self._parse_syntax_output(result.stderr, str(file_path))
                total_errors += len(violations)
            
            file_reports.append(FileQualityReport(
                path=str(file_path.relative_to(self.root_dir)),
                status="fail" if violations else "pass",
                violations=violations
            ))
        
        return QualityReport(
            status="fail" if total_errors > 0 else "pass",
            linter="verible-syntax",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_files=len(self.files),
            files_checked=len(self.files),
            total_violations=total_errors,
            critical_errors=total_errors,
            warnings=0,
            style_issues=0,
            files=file_reports,
            violations_by_category={"syntax": total_errors}
        )
    
    def _run_lint(self) -> QualityReport:
        """Run Verible linter"""
        cmd = [
            'verible-verilog-lint',
            '--parse_fatal',
            '--lint_fatal'
        ]
        
        # Add rules config if provided
        if self.rules_config and self.rules_config.exists():
            cmd.extend(['--rules_config', str(self.rules_config)])
        
        # Add waiver file if provided
        if self.waiver_file and self.waiver_file.exists():
            cmd.extend(['--waiver_files', str(self.waiver_file)])
        
        # Add files
        cmd.extend([str(f) for f in self.files])
        
        result = self.run_command(cmd)
        
        # Parse output
        violations = self._parse_lint_output(result.stdout)
        
        # Organize by file
        files_dict: Dict[str, List[Violation]] = {}
        for v in violations:
            if v.file not in files_dict:
                files_dict[v.file] = []
            files_dict[v.file].append(v)
        
        file_reports = []
        for file_path in self.files:
            rel_path = str(file_path.relative_to(self.root_dir))
            file_violations = files_dict.get(rel_path, [])
            
            file_reports.append(FileQualityReport(
                path=rel_path,
                status="warning" if file_violations else "pass",
                violations=file_violations
            ))
        
        # Count by severity
        errors = sum(1 for v in violations if v.severity == "error")
        warnings = sum(1 for v in violations if v.severity == "warning")
        style = sum(1 for v in violations if v.severity == "info")
        
        # Categorize violations
        categories: Dict[str, int] = {}
        for v in violations:
            rule_category = self._categorize_rule(v.rule)
            categories[rule_category] = categories.get(rule_category, 0) + 1
        
        return QualityReport(
            status="fail" if errors > 0 else ("warning" if warnings > 0 else "pass"),
            linter="verible-lint",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_files=len(self.files),
            files_checked=len(self.files),
            total_violations=len(violations),
            critical_errors=errors,
            warnings=warnings,
            style_issues=style,
            files=file_reports,
            violations_by_category=categories
        )
    
    def _parse_syntax_output(self, output: str, file_path: str) -> List[Violation]:
        """Parse Verible syntax checker output"""
        violations = []
        
        # Pattern: file:line:col: error: message
        pattern = r'(.+?):(\d+):(\d+):\s*(.*)'
        
        for line in output.split('\n'):
            match = re.match(pattern, line)
            if match:
                violations.append(Violation(
                    file=file_path,
                    line=int(match.group(2)),
                    column=int(match.group(3)),
                    severity="error",
                    rule="syntax",
                    message=match.group(4)
                ))
        
        return violations
    
    def _parse_lint_output(self, output: str) -> List[Violation]:
        """Parse Verible lint output"""
        violations = []
        
        # Pattern: file:line:col: message [rule-name]
        pattern = r'(.+?):(\d+):(\d+):\s*(.+?)\s*\[([^\]]+)\]'
        
        for line in output.split('\n'):
            match = re.match(pattern, line)
            if match:
                severity = "warning"  # Default
                if "error" in match.group(4).lower():
                    severity = "error"
                elif "style" in match.group(4).lower():
                    severity = "info"
                
                violations.append(Violation(
                    file=match.group(1),
                    line=int(match.group(2)),
                    column=int(match.group(3)),
                    severity=severity,
                    rule=match.group(5),
                    message=match.group(4)
                ))
        
        return violations
    
    def _categorize_rule(self, rule: str) -> str:
        """Categorize Verible rule into high-level category"""
        rule_lower = rule.lower()
        
        if any(x in rule_lower for x in ['name', 'naming']):
            return "naming"
        elif any(x in rule_lower for x in ['format', 'indent', 'line-length', 'space']):
            return "formatting"
        elif any(x in rule_lower for x in ['parameter', 'port', 'signal']):
            return "structure"
        elif any(x in rule_lower for x in ['forbidden', 'banned']):
            return "prohibited_constructs"
        else:
            return "other"
