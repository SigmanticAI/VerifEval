"""
Base class for quality gate implementations
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import subprocess
import time

from ..models import QualityReport, FileQualityReport, Violation, QualityStatus


class BaseQualityGate(ABC):
    """Base class for language-specific quality gates"""
    
    def __init__(self, files: List[Path], root_dir: Path):
        self.files = files
        self.root_dir = Path(root_dir)
        self.tool_name = "unknown"
    
    @abstractmethod
    def check_tool_available(self) -> bool:
        """Check if the linting tool is available"""
        pass
    
    @abstractmethod
    def run_checks(self) -> QualityReport:
        """Run quality checks and return report"""
        pass
    
    def run_command(self, cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """Run shell command with timeout"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.root_dir
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError(f"Command not found: {cmd[0]}")
    
    def create_empty_report(self, status: str = "skipped", reason: str = "") -> QualityReport:
        """Create an empty quality report"""
        return QualityReport(
            status=status,
            linter=self.tool_name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_files=len(self.files),
            files_checked=0,
            total_violations=0,
            critical_errors=0,
            warnings=0,
            style_issues=0,
            files=[],
            violations_by_category={},
            execution_time_ms=0.0
        )
