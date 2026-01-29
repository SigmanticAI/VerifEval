"""
Questa Formal Verification Module.

Provides formal verification capabilities using Questa Formal (qformal).

Supported Analysis:
    - Assertion proofs (SVA assert properties)
    - Cover point reachability (SVA cover properties)
    - Bounded model checking
    - Property-based verification

Example Usage:
    from questa.formal import QuestaFormalChecker
    from questa.config import set_license
    
    # Configure license
    set_license("1717@license.company.com")
    
    # Create checker
    checker = QuestaFormalChecker()
    
    # Verify a project
    result = checker.verify_project(
        project_dir=Path("my_design"),
        max_depth=30
    )
    
    print(f"Proof rate: {result.proof_rate}%")
    print(f"Score: {result.overall_score}/100")
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from .config import QuestaConfig, get_config


@dataclass
class AssertionResult:
    """Result of a single assertion verification."""
    name: str
    status: str  # "proven", "failed", "unknown", "covered"
    depth: int = 0
    cex_trace: Optional[str] = None  # Counter-example trace
    

@dataclass
class FormalResult:
    """Result of formal verification run."""
    
    # Parse status
    parse_success: bool = False
    parse_errors: List[str] = field(default_factory=list)
    
    # Verification status
    verification_success: bool = False
    verification_errors: List[str] = field(default_factory=list)
    verification_log: str = ""
    
    # Assertion results
    assertion_results: List[AssertionResult] = field(default_factory=list)
    
    # Cover results
    cover_results: List[AssertionResult] = field(default_factory=list)
    
    # Counts
    total_assertions: int = 0
    proven_assertions: int = 0
    failed_assertions: int = 0
    unknown_assertions: int = 0
    
    total_covers: int = 0
    reached_covers: int = 0
    unreached_covers: int = 0
    
    # Timing
    compile_time_sec: float = 0.0
    verify_time_sec: float = 0.0
    
    # Depth used
    max_depth: int = 0
    
    @property
    def proof_rate(self) -> float:
        """Percentage of assertions proven."""
        if self.total_assertions == 0:
            return 100.0
        return (self.proven_assertions / self.total_assertions) * 100
    
    @property
    def cover_rate(self) -> float:
        """Percentage of cover points reached."""
        if self.total_covers == 0:
            return 100.0
        return (self.reached_covers / self.total_covers) * 100
    
    @property
    def overall_score(self) -> float:
        """
        Calculate overall formal verification score.
        
        Scoring:
        - Syntax valid: 25 points
        - Assertion proof rate: 50 points (scaled by proof_rate)
        - Cover reachability: 25 points (scaled by cover_rate)
        """
        score = 0.0
        
        # Syntax (25 points)
        if self.parse_success:
            score += 25.0
        
        # Proof rate (50 points)
        score += 0.50 * self.proof_rate
        
        # Cover rate (25 points)
        score += 0.25 * self.cover_rate
        
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'parse_success': self.parse_success,
            'verification_success': self.verification_success,
            'total_assertions': self.total_assertions,
            'proven_assertions': self.proven_assertions,
            'failed_assertions': self.failed_assertions,
            'unknown_assertions': self.unknown_assertions,
            'proof_rate': round(self.proof_rate, 2),
            'total_covers': self.total_covers,
            'reached_covers': self.reached_covers,
            'cover_rate': round(self.cover_rate, 2),
            'overall_score': round(self.overall_score, 2),
            'max_depth': self.max_depth,
            'timing': {
                'compile_sec': round(self.compile_time_sec, 2),
                'verify_sec': round(self.verify_time_sec, 2),
            },
            'parse_errors': self.parse_errors,
            'verification_errors': self.verification_errors,
            'assertions': [
                {'name': a.name, 'status': a.status, 'depth': a.depth}
                for a in self.assertion_results
            ],
            'covers': [
                {'name': c.name, 'status': c.status}
                for c in self.cover_results
            ],
        }
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "",
            "=" * 60,
            "FORMAL VERIFICATION SUMMARY",
            "=" * 60,
            "",
            f"  Parse Status:        {'✓ Success' if self.parse_success else '✗ Failed'}",
            f"  Verification Status: {'✓ Success' if self.verification_success else '✗ Failed'}",
            "",
            f"  Assertions:",
            f"    Total:   {self.total_assertions}",
            f"    Proven:  {self.proven_assertions}",
            f"    Failed:  {self.failed_assertions}",
            f"    Unknown: {self.unknown_assertions}",
            f"    Rate:    {self.proof_rate:.1f}%",
            "",
            f"  Cover Points:",
            f"    Total:     {self.total_covers}",
            f"    Reached:   {self.reached_covers}",
            f"    Unreached: {self.unreached_covers}",
            f"    Rate:      {self.cover_rate:.1f}%",
            "",
            f"  OVERALL SCORE: {self.overall_score:.1f}/100",
            "=" * 60,
        ]
        return "\n".join(lines)


class QuestaFormalChecker:
    """
    Questa Formal Verification Checker.
    
    Uses Questa Formal (qformal) or vsim -formal for formal verification.
    
    Attributes:
        config: Questa configuration instance
    """
    
    def __init__(self, config: QuestaConfig = None):
        """
        Initialize formal checker.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self.config = config or get_config()
    
    def validate_environment(self) -> Tuple[bool, List[str]]:
        """
        Validate that Questa formal tools are available.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for vlog
        if not shutil.which(self.config.vlog_path):
            errors.append(f"vlog not found: {self.config.vlog_path}")
        
        # Check for qformal or vsim
        qformal_available = shutil.which(self.config.qformal_path)
        vsim_available = shutil.which(self.config.vsim_path)
        
        if not qformal_available and not vsim_available:
            errors.append("Neither qformal nor vsim found. Questa Formal tools not available.")
        
        # Check license
        if not self.config.license_file:
            errors.append("No license configured. Set QUESTA_LICENSE environment variable.")
        
        return len(errors) == 0, errors
    
    def verify_project(self,
                       project_dir: Path,
                       top_module: str = None,
                       max_depth: int = 20,
                       cleanup: bool = True) -> FormalResult:
        """
        Run formal verification on a project directory.
        
        Args:
            project_dir: Path to project containing SV files
            top_module: Top-level module name (auto-detected if None)
            max_depth: Maximum bounded model checking depth
            cleanup: Remove work directory after verification
            
        Returns:
            FormalResult with verification results
        """
        result = FormalResult(max_depth=max_depth)
        project_dir = Path(project_dir)
        
        if not project_dir.exists():
            result.parse_errors.append(f"Project directory not found: {project_dir}")
            return result
        
        # Find source files
        sv_files = list(project_dir.rglob("*.sv")) + list(project_dir.rglob("*.v"))
        
        if not sv_files:
            result.parse_errors.append("No SystemVerilog files found")
            return result
        
        # Auto-detect top module if not specified
        if not top_module:
            top_module = self._detect_top_module(sv_files)
            if not top_module:
                result.parse_errors.append("Could not detect top module")
                return result
        
        # Create work directory
        work_dir = Path(tempfile.mkdtemp(prefix="questa_formal_"))
        
        try:
            # Compile
            import time
            start = time.time()
            
            compile_success, compile_errors = self._compile_for_formal(
                sv_files, work_dir, top_module
            )
            
            result.compile_time_sec = time.time() - start
            result.parse_success = compile_success
            result.parse_errors = compile_errors
            
            if not compile_success:
                return result
            
            # Run formal verification
            start = time.time()
            
            self._run_formal_verification(work_dir, top_module, max_depth, result)
            
            result.verify_time_sec = time.time() - start
            
        finally:
            if cleanup and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        
        return result
    
    def verify_files(self,
                     source_files: List[Path],
                     top_module: str,
                     max_depth: int = 20,
                     work_dir: Path = None,
                     cleanup: bool = True) -> FormalResult:
        """
        Run formal verification on specific files.
        
        Args:
            source_files: List of source files to verify
            top_module: Top-level module name
            max_depth: Maximum bounded model checking depth
            work_dir: Work directory (auto-created if None)
            cleanup: Remove work directory after verification
            
        Returns:
            FormalResult with verification results
        """
        result = FormalResult(max_depth=max_depth)
        
        # Create work directory if not provided
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix="questa_formal_"))
        else:
            work_dir = Path(work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import time
            
            # Compile
            start = time.time()
            compile_success, compile_errors = self._compile_for_formal(
                source_files, work_dir, top_module
            )
            result.compile_time_sec = time.time() - start
            result.parse_success = compile_success
            result.parse_errors = compile_errors
            
            if not compile_success:
                return result
            
            # Run verification
            start = time.time()
            self._run_formal_verification(work_dir, top_module, max_depth, result)
            result.verify_time_sec = time.time() - start
            
        finally:
            if cleanup and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        
        return result
    
    def _detect_top_module(self, sv_files: List[Path]) -> Optional[str]:
        """Detect top module from source files."""
        for f in sv_files:
            try:
                content = f.read_text()
                
                # Look for module with assertions
                match = re.search(r'module\s+(\w+)', content)
                if match and ('assert property' in content or 'assume property' in content):
                    return match.group(1)
            except Exception:
                pass
        
        # Fallback: first module found
        for f in sv_files:
            try:
                content = f.read_text()
                match = re.search(r'module\s+(\w+)', content)
                if match:
                    return match.group(1)
            except Exception:
                pass
        
        return None
    
    def _compile_for_formal(self,
                            source_files: List[Path],
                            work_dir: Path,
                            top_module: str) -> Tuple[bool, List[str]]:
        """Compile sources for formal verification."""
        errors = []
        
        # Create work library
        try:
            lib_result = subprocess.run(
                [self.config.vlib_path, 'work'],
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                timeout=30,
                env=self.config.get_env()
            )
            
            if lib_result.returncode != 0:
                errors.append(f"Failed to create work library: {lib_result.stderr}")
                return False, errors
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            errors.append(f"vlib failed: {e}")
            return False, errors
        
        # Compile with vlog
        cmd = [
            self.config.vlog_path,
            '-work', 'work',
            '-sv',
            '+acc',
            '-timescale', '1ns/1ps',
            '+define+UVM_NO_DPI',  # Avoid DPI issues in formal
        ]
        
        cmd.extend([str(f) for f in source_files])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                timeout=self.config.timeout_sec,
                env=self.config.get_env()
            )
            
            output = result.stdout + result.stderr
            
            # Check for errors
            error_matches = re.findall(r'\*\* Error[^*]+', output)
            if error_matches:
                errors.extend(error_matches[:5])
                return False, errors
            
            return result.returncode == 0, errors
            
        except subprocess.TimeoutExpired:
            errors.append("Compilation timed out")
            return False, errors
        except FileNotFoundError:
            errors.append(f"vlog not found: {self.config.vlog_path}")
            return False, errors
    
    def _run_formal_verification(self,
                                  work_dir: Path,
                                  top_module: str,
                                  max_depth: int,
                                  result: FormalResult):
        """Run formal verification using qformal or vsim -formal."""
        
        # Try qformal first, fall back to vsim -formal
        qformal_available = shutil.which(self.config.qformal_path)
        
        if qformal_available:
            self._run_qformal(work_dir, top_module, max_depth, result)
        else:
            self._run_vsim_formal(work_dir, top_module, max_depth, result)
    
    def _run_qformal(self,
                     work_dir: Path,
                     top_module: str,
                     max_depth: int,
                     result: FormalResult):
        """Run formal verification using qformal."""
        
        # Create qformal script
        script_content = f"""
# Questa Formal verification script
# Auto-generated by VerifEval

# Set up database
formal compile -work work -d {top_module}

# Configure proof
formal verify -init {{}} -timeout 300 -depth {max_depth} {top_module}

# Get results
formal report -list
formal report -summary

# Exit
exit
"""
        
        script_file = work_dir / "qformal.do"
        script_file.write_text(script_content)
        
        try:
            proc = subprocess.run(
                [self.config.qformal_path, '-do', str(script_file)],
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                timeout=self.config.timeout_sec * 3,  # Formal can take longer
                env=self.config.get_env()
            )
            
            result.verification_log = proc.stdout + proc.stderr
            result.verification_success = proc.returncode == 0
            
            self._parse_formal_output(result)
            
        except subprocess.TimeoutExpired:
            result.verification_errors.append("Formal verification timed out")
        except FileNotFoundError:
            result.verification_errors.append(f"qformal not found: {self.config.qformal_path}")
    
    def _run_vsim_formal(self,
                          work_dir: Path,
                          top_module: str,
                          max_depth: int,
                          result: FormalResult):
        """Run formal verification using vsim -formal (fallback)."""
        
        # Create vsim formal script
        do_commands = f"""
# Enable formal
formal prove -all -depth {max_depth}

# Get summary
formal report -summary

# Quit
quit -f
"""
        
        try:
            proc = subprocess.run(
                [
                    self.config.vsim_path,
                    '-c',
                    '-formal',
                    '-work', 'work',
                    '-do', do_commands,
                    top_module
                ],
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                timeout=self.config.timeout_sec * 3,
                env=self.config.get_env()
            )
            
            result.verification_log = proc.stdout + proc.stderr
            result.verification_success = proc.returncode == 0
            
            self._parse_formal_output(result)
            
        except subprocess.TimeoutExpired:
            result.verification_errors.append("Formal verification timed out")
        except FileNotFoundError:
            result.verification_errors.append(f"vsim not found: {self.config.vsim_path}")
    
    def _parse_formal_output(self, result: FormalResult):
        """Parse formal verification output for results."""
        log = result.verification_log
        
        # Parse assertion results
        # Look for patterns like "Property NAME: proven" or "Property NAME: failed"
        
        # Proven assertions
        proven_matches = re.findall(r'(?:Property|Assertion)\s+(\S+).*(?:proven|passed)', log, re.IGNORECASE)
        for name in proven_matches:
            result.assertion_results.append(AssertionResult(name=name, status="proven"))
        result.proven_assertions = len(proven_matches)
        
        # Failed assertions
        failed_matches = re.findall(r'(?:Property|Assertion)\s+(\S+).*(?:failed|violated)', log, re.IGNORECASE)
        for name in failed_matches:
            result.assertion_results.append(AssertionResult(name=name, status="failed"))
        result.failed_assertions = len(failed_matches)
        
        # Unknown/inconclusive
        unknown_matches = re.findall(r'(?:Property|Assertion)\s+(\S+).*(?:unknown|inconclusive|bounded)', log, re.IGNORECASE)
        for name in unknown_matches:
            result.assertion_results.append(AssertionResult(name=name, status="unknown"))
        result.unknown_assertions = len(unknown_matches)
        
        result.total_assertions = result.proven_assertions + result.failed_assertions + result.unknown_assertions
        
        # Parse cover results
        covered_matches = re.findall(r'(?:Cover|Coverpoint)\s+(\S+).*(?:covered|reached)', log, re.IGNORECASE)
        for name in covered_matches:
            result.cover_results.append(AssertionResult(name=name, status="covered"))
        result.reached_covers = len(covered_matches)
        
        unreached_matches = re.findall(r'(?:Cover|Coverpoint)\s+(\S+).*(?:uncovered|unreached|unreachable)', log, re.IGNORECASE)
        for name in unreached_matches:
            result.cover_results.append(AssertionResult(name=name, status="unreached"))
        result.unreached_covers = len(unreached_matches)
        
        result.total_covers = result.reached_covers + result.unreached_covers
        
        # Alternative parsing: look for summary lines
        if result.total_assertions == 0:
            # Try to find summary line
            match = re.search(r'(\d+)\s+(?:assertions?|properties)\s+proven', log, re.IGNORECASE)
            if match:
                result.proven_assertions = int(match.group(1))
            
            match = re.search(r'(\d+)\s+(?:assertions?|properties)\s+failed', log, re.IGNORECASE)
            if match:
                result.failed_assertions = int(match.group(1))
            
            match = re.search(r'(\d+)\s+(?:assertions?|properties)\s+(?:total|found)', log, re.IGNORECASE)
            if match:
                result.total_assertions = int(match.group(1))
                result.unknown_assertions = result.total_assertions - result.proven_assertions - result.failed_assertions
        
        # Verification is successful if we found any assertions and none failed
        if result.total_assertions > 0:
            result.verification_success = result.failed_assertions == 0
