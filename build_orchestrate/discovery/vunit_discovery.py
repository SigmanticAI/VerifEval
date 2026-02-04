"""
VUnit Test Discovery
====================

Discovers tests via VUnit's built-in test enumeration.

Author: TB Eval Team
Version: 0.1.0
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional
import re

from .base import BaseTestDiscovery, DiscoveryResult
from ..models import TestCase, TestStatus


class VUnitTestDiscovery(BaseTestDiscovery):
    """
    Discovers tests using VUnit's --list functionality
    
    Usage:
        discovery = VUnitTestDiscovery(submission_dir, run_script)
        result = discovery.discover([])  # Files not needed, VUnit handles it
    """
    
    def __init__(
        self,
        submission_dir: Path,
        run_script: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ):
        """
        Initialize VUnit test discovery
        
        Args:
            submission_dir: Path to submission directory
            run_script: Path to VUnit run.py script
            output_path: VUnit output path
        """
        super().__init__(submission_dir)
        self.run_script = run_script
        self.output_path = output_path or (submission_dir / ".tbeval" / "vunit_out")
    
    def get_discovery_method(self) -> str:
        return "vunit_list"
    
    def discover(self, source_files: List[Path]) -> DiscoveryResult:
        """
        Discover tests using VUnit --list
        
        Args:
            source_files: Not used (VUnit handles file discovery)
        
        Returns:
            DiscoveryResult with discovered tests
        """
        result = DiscoveryResult(
            discovery_method=self.get_discovery_method(),
        )
        
        if not self.run_script or not self.run_script.exists():
            result.errors.append(f"VUnit run script not found: {self.run_script}")
            return result
        
        # Run VUnit with --list
        cmd = [
            sys.executable,
            str(self.run_script),
            "--list",
            f"--output-path={self.output_path}",
        ]
        
        try:
            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.run_script.parent),
            )
            
            # Parse output
            tests = self._parse_list_output(proc_result.stdout)
            result.tests = tests
            
            if proc_result.returncode != 0 and not tests:
                result.errors.append(f"VUnit --list failed: {proc_result.stderr}")
            
        except subprocess.TimeoutExpired:
            result.errors.append("VUnit --list timed out")
        except Exception as e:
            result.errors.append(f"VUnit discovery failed: {str(e)}")
        
        return result
    
    def _parse_list_output(self, output: str) -> List[TestCase]:
        """Parse VUnit --list output"""
        tests = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # VUnit format: library.test_bench.test_name
            # or: library.test_bench.test_name.config_name
            parts = line.split('.')
            
            if len(parts) >= 3:
                library = parts[0]
                testbench = parts[1]
                test_name = '.'.join(parts[2:])  # Handle configs
                
                tests.append(TestCase(
                    name=test_name,
                    full_name=line,
                    testbench=testbench,
                    library=library,
                    test_type="vunit",
                    status=TestStatus.READY,
                ))
            elif len(parts) == 2:
                # library.test_bench (no specific test)
                tests.append(TestCase(
                    name=parts[1],
                    full_name=line,
                    testbench=parts[1],
                    library=parts[0],
                    test_type="vunit",
                    status=TestStatus.READY,
                ))
        
        return tests
