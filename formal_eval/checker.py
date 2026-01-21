"""
Formal Checker using Yosys.

Uses Yosys to parse, synthesize, and formally verify SVA assertions.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import FormalConfig, FormalProject, WORK_DIR


@dataclass
class AssertionResult:
    """Result for a single assertion."""
    name: str
    status: str  # "proven", "failed", "unknown", "error"
    message: str = ""
    counterexample: Optional[str] = None
    depth_reached: int = 0


@dataclass
class FormalResult:
    """Result of formal verification run."""
    
    # Parsing status
    parse_success: bool = False
    parse_errors: List[str] = field(default_factory=list)
    
    # Synthesis status
    synth_success: bool = False
    synth_errors: List[str] = field(default_factory=list)
    synth_warnings: int = 0
    
    # Formal verification results
    assertions_found: int = 0
    assertions_proven: int = 0
    assertions_failed: int = 0
    assertions_unknown: int = 0
    
    # Individual assertion results
    assertion_results: List[AssertionResult] = field(default_factory=list)
    
    # Cover points
    cover_points_found: int = 0
    cover_points_reached: int = 0
    
    # Raw output
    output: str = ""
    
    @property
    def success(self) -> bool:
        return self.parse_success and self.synth_success
    
    @property
    def proof_rate(self) -> float:
        """Percentage of assertions proven."""
        if self.assertions_found == 0:
            return 0.0
        return (self.assertions_proven / self.assertions_found) * 100
    
    @property
    def cover_rate(self) -> float:
        """Percentage of cover points reached."""
        if self.cover_points_found == 0:
            return 0.0
        return (self.cover_points_reached / self.cover_points_found) * 100


class FormalChecker:
    """Formal verification checker using Yosys."""
    
    def __init__(self, config: FormalConfig = None):
        self.config = config or FormalConfig()
        self._verify_dependencies()
    
    def _verify_dependencies(self):
        """Verify required tools are available."""
        # Check Yosys
        result = subprocess.run(['which', 'yosys'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Yosys not found. Install with: brew install yosys")
    
    def check(self, project: FormalProject, run_id: int = 1) -> FormalResult:
        """
        Run formal verification on a project.
        
        Steps:
        1. Create work directory
        2. Parse and extract assertions
        3. Run Yosys synthesis
        4. Run formal checks (SAT-based BMC)
        5. Collect results
        """
        result = FormalResult()
        
        # Create work directory
        work_dir = WORK_DIR / project.name / f"run_{run_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy files to work directory
            self._setup_work_dir(project, work_dir)
            
            # Parse and extract assertions
            assertions = self._extract_assertions(project, work_dir, result)
            result.assertions_found = len(assertions)
            
            if not result.parse_success:
                return result
            
            # Run Yosys synthesis
            self._run_synthesis(project, work_dir, result)
            
            if not result.synth_success:
                return result
            
            # Run formal verification
            self._run_formal_checks(project, work_dir, assertions, result)
            
        except Exception as e:
            result.parse_errors.append(str(e))
        
        finally:
            # Clean up if requested
            if not self.config.keep_work_dir and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        
        return result
    
    def _setup_work_dir(self, project: FormalProject, work_dir: Path):
        """Copy project files to work directory."""
        for f in project.all_files:
            if f.exists():
                shutil.copy(f, work_dir / f.name)
    
    def _extract_assertions(self, project: FormalProject, 
                           work_dir: Path, result: FormalResult) -> List[dict]:
        """Extract assertions from project files."""
        assertions = []
        
        all_files = list(work_dir.glob("*.v")) + list(work_dir.glob("*.sv"))
        
        for file_path in all_files:
            try:
                content = file_path.read_text()
                
                # Extract assert properties
                assert_pattern = r'(\w+)\s*:\s*assert\s+property\s*\(\s*@\s*\(\s*posedge\s+(\w+)\s*\)([^;]+)\);'
                for match in re.finditer(assert_pattern, content, re.DOTALL):
                    assertions.append({
                        'name': match.group(1),
                        'clock': match.group(2),
                        'property': match.group(3).strip(),
                        'type': 'assert',
                        'file': file_path.name,
                    })
                
                # Also match unnamed assertions
                anon_pattern = r'assert\s+property\s*\(\s*@\s*\(\s*posedge\s+(\w+)\s*\)([^;]+)\);'
                idx = 0
                for match in re.finditer(anon_pattern, content, re.DOTALL):
                    # Skip if this was already captured as named
                    prop = match.group(2).strip()
                    if not any(a['property'] == prop for a in assertions):
                        assertions.append({
                            'name': f'anon_assert_{idx}',
                            'clock': match.group(1),
                            'property': prop,
                            'type': 'assert',
                            'file': file_path.name,
                        })
                        idx += 1
                
                # Extract cover properties
                cover_pattern = r'(\w+)\s*:\s*cover\s+property\s*\([^;]+\);'
                for match in re.finditer(cover_pattern, content, re.DOTALL):
                    result.cover_points_found += 1
                
                # Extract simple assert statements (non-property)
                simple_assert = r'assert\s*\(([^)]+)\)'
                for match in re.finditer(simple_assert, content):
                    assertions.append({
                        'name': f'simple_assert_{len(assertions)}',
                        'clock': None,
                        'property': match.group(1).strip(),
                        'type': 'immediate',
                        'file': file_path.name,
                    })
                    
            except Exception as e:
                result.parse_errors.append(f"Error parsing {file_path.name}: {e}")
        
        if assertions or not result.parse_errors:
            result.parse_success = True
        
        return assertions
    
    def _run_synthesis(self, project: FormalProject, 
                       work_dir: Path, result: FormalResult):
        """Run Yosys synthesis to check for errors."""
        
        # Build file list
        files = list(work_dir.glob("*.v")) + list(work_dir.glob("*.sv"))
        if not files:
            result.synth_errors.append("No Verilog files found")
            return
        
        # Create Yosys script
        script = f"""# Yosys formal verification script
# Read design files
"""
        for f in files:
            script += f'read_verilog -sv -formal -DFORMAL "{f}"\n'
        
        script += """
# Synthesize
hierarchy -auto-top
proc
flatten
opt
"""
        
        script_path = work_dir / "synth.ys"
        script_path.write_text(script)
        
        # Run Yosys
        try:
            proc = subprocess.run(
                ['yosys', '-s', str(script_path)],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_sec,
                cwd=str(work_dir)
            )
            
            result.output = proc.stdout + proc.stderr
            
            # Check for errors
            if 'ERROR' in proc.stderr or proc.returncode != 0:
                result.synth_success = False
                error_lines = [l for l in proc.stderr.split('\n') if 'ERROR' in l or 'error' in l.lower()]
                result.synth_errors = error_lines[:5]  # First 5 errors
            else:
                result.synth_success = True
            
            # Count warnings
            result.synth_warnings = proc.stderr.count('Warning')
            
        except subprocess.TimeoutExpired:
            result.synth_errors.append("Synthesis timed out")
        except Exception as e:
            result.synth_errors.append(str(e))
    
    def _run_formal_checks(self, project: FormalProject, work_dir: Path,
                           assertions: List[dict], result: FormalResult):
        """Run formal verification on assertions using Yosys SAT."""
        
        if not assertions:
            # No assertions to check - this is still a valid result
            return
        
        # Build file list
        files = list(work_dir.glob("*.v")) + list(work_dir.glob("*.sv"))
        
        # Create formal verification script
        script = f"""# Yosys formal verification
"""
        for f in files:
            script += f'read_verilog -sv -formal -DFORMAL "{f}"\n'
        
        script += f"""
hierarchy -auto-top
proc
flatten
opt

# Convert memories to registers for SAT solving
memory -nomap
opt

# Check for assertions
stat

# Formal verification setup  
async2sync
dffunmap
formalff -clk2ff -ff2anyinit

# Remove cover points and assumptions for SAT
chformal -cover -remove
chformal -assume -remove

# Remove memories for SAT
memory_map

# Run bounded model checking
sat -tempinduct -prove-asserts -seq {self.config.bounded_depth} -set-init-zero
"""
        
        script_path = work_dir / "formal.ys"
        script_path.write_text(script)
        
        # Run formal verification
        try:
            proc = subprocess.run(
                ['yosys', '-s', str(script_path)],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_sec * len(assertions),
                cwd=str(work_dir)
            )
            
            output = proc.stdout + proc.stderr
            result.output += output
            
            # Parse results
            self._parse_formal_output(output, assertions, result)
            
        except subprocess.TimeoutExpired:
            result.assertion_results.append(AssertionResult(
                name="all",
                status="unknown",
                message="Formal verification timed out"
            ))
            result.assertions_unknown = len(assertions)
        except Exception as e:
            result.assertion_results.append(AssertionResult(
                name="all",
                status="error",
                message=str(e)
            ))
    
    def _parse_formal_output(self, output: str, 
                             assertions: List[dict], result: FormalResult):
        """Parse Yosys formal verification output."""
        
        # Check for SAT results
        proof_success = (
            ("SUCCESS" in output and "FAIL" not in output) or
            ("Induction step proven: SUCCESS" in output) or
            ("proven: SUCCESS" in output)
        )
        
        proof_failed = (
            "FAIL!" in output or
            "FAIL" in output or
            "Assert failed" in output or
            "counterexample" in output.lower() or
            "model found" in output.lower()
        )
        
        has_error = "ERROR" in output
        
        if proof_success and not proof_failed and not has_error:
            # All proofs passed
            result.assertions_proven = len(assertions)
            for assertion in assertions:
                result.assertion_results.append(AssertionResult(
                    name=assertion['name'],
                    status="proven",
                    message="Assertion holds (induction proof)",
                    depth_reached=self.config.bounded_depth
                ))
        
        elif proof_failed:
            # Assertions failed - mark all as failed since Yosys stops on first failure
            result.assertions_failed = len(assertions)
            for assertion in assertions:
                result.assertion_results.append(AssertionResult(
                    name=assertion['name'],
                    status="failed",
                    message="Assertion violated (counterexample found)"
                ))
        
        elif has_error:
            # Error during formal verification
            result.assertions_unknown = len(assertions)
            for assertion in assertions:
                result.assertion_results.append(AssertionResult(
                    name=assertion['name'],
                    status="error",
                    message="Formal verification error"
                ))
        
        else:
            # Unknown result
            result.assertions_unknown = len(assertions)
            for assertion in assertions:
                result.assertion_results.append(AssertionResult(
                    name=assertion['name'],
                    status="unknown",
                    message="Could not determine result"
                ))


def parse_formal_project(folder_path: Path) -> FormalProject:
    """
    Parse a folder to create a FormalProject.
    
    Identifies:
    - .v/.sv files with module definitions -> Design files
    - .v/.sv files with assertions -> Assertion files
    - .sva files -> Pure assertion files
    """
    
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    project = FormalProject(path=folder_path)
    
    for file in folder_path.iterdir():
        if not file.is_file():
            continue
        
        suffix = file.suffix.lower()
        name = file.stem.lower()
        
        if suffix in ['.v', '.sv']:
            content = file.read_text()
            
            # Check if it's primarily assertions or design
            has_module = 'module ' in content
            has_assert = 'assert ' in content or 'assume ' in content
            
            if 'assert' in name or 'sva' in name or 'prop' in name:
                project.assertion_files.append(file)
            elif has_module and not has_assert:
                project.design_files.append(file)
            elif has_assert and not has_module:
                project.assertion_files.append(file)
            else:
                # Has both - treat as design with embedded assertions
                project.design_files.append(file)
                
        elif suffix == '.sva':
            project.assertion_files.append(file)
    
    return project

