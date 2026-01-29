"""
Questa Coverage Analyzer Module.

Provides coverage analysis using Questa vcover tool.
Supports UCDB (Unified Coverage Database) format.

Coverage Types:
    - Line/Statement coverage
    - Branch coverage
    - Condition coverage
    - Toggle coverage
    - FSM coverage
    - Assertion coverage (SVA)
    - Functional coverage (covergroups)

Example Usage:
    from questa.coverage import QuestaCoverageAnalyzer
    
    analyzer = QuestaCoverageAnalyzer()
    
    # Analyze single UCDB
    result = analyzer.analyze("coverage.ucdb")
    print(f"Line coverage: {result.line_coverage}%")
    
    # Merge multiple UCDBs
    merged = analyzer.merge(["test1.ucdb", "test2.ucdb"], "merged.ucdb")
"""

import re
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .config import QuestaConfig, get_config


@dataclass
class CoverageDetail:
    """Detailed coverage information for a specific type."""
    total_bins: int = 0
    covered_bins: int = 0
    percentage: float = 0.0
    
    def __post_init__(self):
        if self.total_bins > 0:
            self.percentage = (self.covered_bins / self.total_bins) * 100


@dataclass
class CoverageResult:
    """Coverage analysis result."""
    
    # Overall percentages
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    condition_coverage: float = 0.0
    toggle_coverage: float = 0.0
    fsm_coverage: float = 0.0
    assertion_coverage: float = 0.0
    functional_coverage: float = 0.0
    
    # Detailed breakdown
    line_detail: CoverageDetail = field(default_factory=CoverageDetail)
    branch_detail: CoverageDetail = field(default_factory=CoverageDetail)
    toggle_detail: CoverageDetail = field(default_factory=CoverageDetail)
    
    # Per-module coverage
    module_coverage: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Covergroup details
    covergroup_coverage: Dict[str, float] = field(default_factory=dict)
    
    # Assertion details
    assertion_results: Dict[str, str] = field(default_factory=dict)  # name -> pass/fail
    
    # Source file
    ucdb_file: Optional[Path] = None
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_coverage(self) -> float:
        """Calculate overall weighted coverage."""
        metrics = [
            (self.line_coverage, 0.30),
            (self.branch_coverage, 0.20),
            (self.toggle_coverage, 0.10),
            (self.functional_coverage, 0.30),
            (self.assertion_coverage, 0.10),
        ]
        
        total = sum(cov * weight for cov, weight in metrics if cov > 0)
        total_weight = sum(weight for cov, weight in metrics if cov > 0)
        
        return total / total_weight if total_weight > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'line_coverage': round(self.line_coverage, 2),
            'branch_coverage': round(self.branch_coverage, 2),
            'condition_coverage': round(self.condition_coverage, 2),
            'toggle_coverage': round(self.toggle_coverage, 2),
            'fsm_coverage': round(self.fsm_coverage, 2),
            'assertion_coverage': round(self.assertion_coverage, 2),
            'functional_coverage': round(self.functional_coverage, 2),
            'total_coverage': round(self.total_coverage, 2),
            'module_coverage': self.module_coverage,
            'covergroup_coverage': self.covergroup_coverage,
            'errors': self.errors,
        }
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "",
            "=" * 50,
            "COVERAGE SUMMARY",
            "=" * 50,
            "",
            f"  Line Coverage:       {self.line_coverage:6.2f}%",
            f"  Branch Coverage:     {self.branch_coverage:6.2f}%",
            f"  Toggle Coverage:     {self.toggle_coverage:6.2f}%",
            f"  FSM Coverage:        {self.fsm_coverage:6.2f}%",
            f"  Assertion Coverage:  {self.assertion_coverage:6.2f}%",
            f"  Functional Coverage: {self.functional_coverage:6.2f}%",
            "",
            f"  TOTAL COVERAGE:      {self.total_coverage:6.2f}%",
            "=" * 50,
        ]
        return "\n".join(lines)


class QuestaCoverageAnalyzer:
    """
    Questa Coverage Analyzer.
    
    Uses vcover to analyze and manipulate UCDB coverage databases.
    """
    
    def __init__(self, config: QuestaConfig = None):
        """
        Initialize coverage analyzer.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self.config = config or get_config()
    
    def analyze(self, ucdb_file: Path) -> CoverageResult:
        """
        Analyze a UCDB coverage database.
        
        Args:
            ucdb_file: Path to UCDB file
            
        Returns:
            CoverageResult with coverage metrics
        """
        ucdb_file = Path(ucdb_file)
        result = CoverageResult(ucdb_file=ucdb_file)
        
        if not ucdb_file.exists():
            result.errors.append(f"UCDB file not found: {ucdb_file}")
            return result
        
        # Get summary report
        self._parse_summary_report(ucdb_file, result)
        
        # Get detailed module coverage
        self._parse_module_coverage(ucdb_file, result)
        
        # Get covergroup details
        self._parse_covergroup_details(ucdb_file, result)
        
        return result
    
    def _parse_summary_report(self, ucdb_file: Path, result: CoverageResult):
        """Parse vcover summary report."""
        try:
            proc = subprocess.run(
                [
                    self.config.vcover_path,
                    'report', '-summary',
                    str(ucdb_file)
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=self.config.get_env()
            )
            
            output = proc.stdout + proc.stderr
            
            # Parse statement/line coverage
            match = re.search(r'Stmts\s+(\d+)\s+(\d+)\s+([\d.]+)%', output)
            if match:
                result.line_detail = CoverageDetail(
                    total_bins=int(match.group(1)),
                    covered_bins=int(match.group(2)),
                    percentage=float(match.group(3))
                )
                result.line_coverage = float(match.group(3))
            
            # Parse branch coverage
            match = re.search(r'Branches\s+(\d+)\s+(\d+)\s+([\d.]+)%', output)
            if match:
                result.branch_detail = CoverageDetail(
                    total_bins=int(match.group(1)),
                    covered_bins=int(match.group(2)),
                    percentage=float(match.group(3))
                )
                result.branch_coverage = float(match.group(3))
            
            # Parse condition coverage
            match = re.search(r'FEC Condition\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.condition_coverage = float(match.group(1))
            
            # Parse toggle coverage
            match = re.search(r'Toggles\s+(\d+)\s+(\d+)\s+([\d.]+)%', output)
            if match:
                result.toggle_detail = CoverageDetail(
                    total_bins=int(match.group(1)),
                    covered_bins=int(match.group(2)),
                    percentage=float(match.group(3))
                )
                result.toggle_coverage = float(match.group(3))
            
            # Parse FSM coverage
            match = re.search(r'FSM States\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.fsm_coverage = float(match.group(1))
            
            # Parse assertion coverage
            match = re.search(r'Assertions\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.assertion_coverage = float(match.group(1))
            
            # Parse functional coverage (covergroups)
            match = re.search(r'Covergroups\s+([\d.]+)%', output)
            if match:
                result.functional_coverage = float(match.group(1))
            
        except subprocess.TimeoutExpired:
            result.errors.append("Coverage analysis timed out")
        except FileNotFoundError:
            result.errors.append(f"vcover not found: {self.config.vcover_path}")
    
    def _parse_module_coverage(self, ucdb_file: Path, result: CoverageResult):
        """Parse per-module coverage."""
        try:
            proc = subprocess.run(
                [
                    self.config.vcover_path,
                    'report', '-bydu', '-totals',
                    str(ucdb_file)
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=self.config.get_env()
            )
            
            output = proc.stdout
            
            # Parse module lines (format: module_name coverage%)
            for line in output.split('\n'):
                match = re.match(r'\s*(\w+)\s+([\d.]+)%', line)
                if match:
                    module_name = match.group(1)
                    coverage = float(match.group(2))
                    result.module_coverage[module_name] = {'total': coverage}
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def _parse_covergroup_details(self, ucdb_file: Path, result: CoverageResult):
        """Parse covergroup coverage details."""
        try:
            proc = subprocess.run(
                [
                    self.config.vcover_path,
                    'report', '-cvg',
                    str(ucdb_file)
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=self.config.get_env()
            )
            
            output = proc.stdout
            
            # Parse covergroup lines
            for line in output.split('\n'):
                match = re.search(r'(\w+)\s+([\d.]+)%\s+\d+\s+\d+\s+\d+', line)
                if match:
                    cg_name = match.group(1)
                    coverage = float(match.group(2))
                    result.covergroup_coverage[cg_name] = coverage
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def merge(self, 
              ucdb_files: List[Path],
              output_file: Path,
              merge_mode: str = "union") -> Optional[Path]:
        """
        Merge multiple UCDB files.
        
        Args:
            ucdb_files: List of UCDB files to merge
            output_file: Output merged UCDB file
            merge_mode: Merge mode (union, intersection)
            
        Returns:
            Path to merged UCDB or None on failure
        """
        try:
            cmd = [
                self.config.vcover_path,
                'merge',
                '-out', str(output_file),
            ]
            
            cmd.extend([str(f) for f in ucdb_files])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=self.config.get_env()
            )
            
            if result.returncode == 0 and Path(output_file).exists():
                return Path(output_file)
            return None
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def generate_html_report(self,
                             ucdb_file: Path,
                             output_dir: Path) -> Optional[Path]:
        """
        Generate HTML coverage report.
        
        Args:
            ucdb_file: Input UCDB file
            output_dir: Output directory for HTML files
            
        Returns:
            Path to index.html or None on failure
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                self.config.vcover_path,
                'report', '-html',
                '-htmldir', str(output_dir),
                str(ucdb_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=self.config.get_env()
            )
            
            index_file = output_dir / "index.html"
            if result.returncode == 0 and index_file.exists():
                return index_file
            return None
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def get_uncovered_items(self, ucdb_file: Path) -> Dict[str, List[str]]:
        """
        Get list of uncovered items.
        
        Args:
            ucdb_file: Input UCDB file
            
        Returns:
            Dictionary of uncovered items by type
        """
        uncovered = {
            'statements': [],
            'branches': [],
            'toggles': [],
            'coverpoints': [],
        }
        
        try:
            # Get uncovered statements
            proc = subprocess.run(
                [
                    self.config.vcover_path,
                    'report', '-zeros',
                    str(ucdb_file)
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=self.config.get_env()
            )
            
            output = proc.stdout
            
            # Parse uncovered items from output
            for line in output.split('\n'):
                if 'ZERO' in line or 'uncovered' in line.lower():
                    uncovered['statements'].append(line.strip())
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return uncovered

