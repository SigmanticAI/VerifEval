"""
VUnit Project Detector
======================

Detects existing VUnit project configurations in submissions.

Looks for:
- run.py, vunit_run.py, run_tests.py
- VUnit configuration in existing scripts
- Existing library configurations

Author: TB Eval Team
Version: 0.1.0
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class ExistingVUnitProject:
    """
    Information about an existing VUnit project
    
    Attributes:
        run_script: Path to the VUnit run script
        libraries: Detected library configurations
        simulator: Detected simulator preference
        source_files: Detected source file patterns
        has_tests: Whether tests are defined
        configuration: Extracted configuration
        usable: Whether the existing setup is usable as-is
        issues: List of issues that prevent direct use
    """
    run_script: Path
    libraries: List[str] = field(default_factory=list)
    simulator: Optional[str] = None
    source_files: Dict[str, List[str]] = field(default_factory=dict)
    has_tests: bool = False
    configuration: Dict[str, Any] = field(default_factory=dict)
    usable: bool = True
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_script": str(self.run_script),
            "libraries": self.libraries,
            "simulator": self.simulator,
            "source_files": self.source_files,
            "has_tests": self.has_tests,
            "usable": self.usable,
            "issues": self.issues,
        }


class VUnitProjectDetector:
    """
    Detects existing VUnit project configuration
    
    Usage:
        detector = VUnitProjectDetector(submission_dir)
        existing = detector.detect()
        
        if existing and existing.usable:
            print(f"Found existing VUnit setup: {existing.run_script}")
    """
    
    # Common VUnit run script names
    RUN_SCRIPT_NAMES = [
        "run.py",
        "vunit_run.py",
        "run_tests.py",
        "run_vunit.py",
        "test_runner.py",
        "tb_run.py",
    ]
    
    # VUnit import patterns
    VUNIT_IMPORT_PATTERNS = [
        r'from\s+vunit\s+import\s+VUnit',
        r'from\s+vunit\.verilog\s+import\s+VUnit',
        r'from\s+vunit\.vhdl\s+import\s+VUnit',
        r'import\s+vunit',
    ]
    
    def __init__(self, submission_dir: Path):
        """
        Initialize detector
        
        Args:
            submission_dir: Path to submission directory
        """
        self.submission_dir = Path(submission_dir)
    
    def detect(self) -> Optional[ExistingVUnitProject]:
        """
        Detect existing VUnit project
        
        Returns:
            ExistingVUnitProject if found, None otherwise
        """
        # Search for run scripts
        run_script = self._find_run_script()
        
        if not run_script:
            return None
        
        # Analyze the run script
        return self._analyze_run_script(run_script)
    
    def _find_run_script(self) -> Optional[Path]:
        """Find VUnit run script in submission"""
        # Check root directory first
        for name in self.RUN_SCRIPT_NAMES:
            script_path = self.submission_dir / name
            if script_path.exists() and self._is_vunit_script(script_path):
                return script_path
        
        # Check common subdirectories
        subdirs = ["tb", "test", "tests", "sim", "scripts"]
        for subdir in subdirs:
            dir_path = self.submission_dir / subdir
            if dir_path.exists():
                for name in self.RUN_SCRIPT_NAMES:
                    script_path = dir_path / name
                    if script_path.exists() and self._is_vunit_script(script_path):
                        return script_path
        
        # Search all Python files for VUnit usage
        for py_file in self.submission_dir.rglob("*.py"):
            # Skip common non-test files
            if any(skip in py_file.name for skip in ["setup", "conf", "__"]):
                continue
            if self._is_vunit_script(py_file):
                return py_file
        
        return None
    
    def _is_vunit_script(self, script_path: Path) -> bool:
        """Check if a Python file is a VUnit run script"""
        try:
            content = script_path.read_text(errors='ignore')
            
            # Check for VUnit imports
            for pattern in self.VUNIT_IMPORT_PATTERNS:
                if re.search(pattern, content):
                    return True
            
            return False
        except Exception:
            return False
    
    def _analyze_run_script(self, script_path: Path) -> ExistingVUnitProject:
        """Analyze VUnit run script for configuration"""
        project = ExistingVUnitProject(run_script=script_path)
        
        try:
            content = script_path.read_text(errors='ignore')
            
            # Try AST parsing for accurate analysis
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, project)
            except SyntaxError:
                # Fall back to regex analysis
                self._analyze_regex(content, project)
            
            # Validate usability
            self._validate_project(project, content)
            
        except Exception as e:
            project.usable = False
            project.issues.append(f"Error analyzing script: {str(e)}")
        
        return project
    
    def _analyze_ast(self, tree: ast.AST, project: ExistingVUnitProject) -> None:
        """Analyze script using AST"""
        for node in ast.walk(tree):
            # Look for library additions
            if isinstance(node, ast.Call):
                if hasattr(node, 'func'):
                    func = node.func
                    
                    # Check for add_library calls
                    if isinstance(func, ast.Attribute) and func.attr == 'add_library':
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant):
                                project.libraries.append(arg.value)
                            elif isinstance(arg, ast.Str):  # Python < 3.8
                                project.libraries.append(arg.s)
                    
                    # Check for add_source_files calls
                    elif isinstance(func, ast.Attribute) and func.attr == 'add_source_files':
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant):
                                lib_name = self._get_lib_from_chain(func)
                                if lib_name not in project.source_files:
                                    project.source_files[lib_name] = []
                                project.source_files[lib_name].append(arg.value)
            
            # Look for test_bench or test definitions
            if isinstance(node, ast.Call):
                if hasattr(node, 'func'):
                    func = node.func
                    if isinstance(func, ast.Attribute):
                        if func.attr in ['test_bench', 'add_testbench', 'test']:
                            project.has_tests = True
    
    def _get_lib_from_chain(self, func: ast.Attribute) -> str:
        """Extract library name from method chain"""
        # This is simplified - real implementation would trace the chain
        return "unknown"
    
    def _analyze_regex(self, content: str, project: ExistingVUnitProject) -> None:
        """Analyze script using regex patterns"""
        # Find library additions
        lib_pattern = r'\.add_library\s*\(\s*["\'](\w+)["\']'
        for match in re.finditer(lib_pattern, content):
            project.libraries.append(match.group(1))
        
        # Find source file additions
        src_pattern = r'\.add_source_files?\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(src_pattern, content):
            if "work" not in project.source_files:
                project.source_files["work"] = []
            project.source_files["work"].append(match.group(1))
        
        # Check for test definitions
        if re.search(r'\.(test_bench|add_testbench|test)\s*\(', content):
            project.has_tests = True
        
        # Detect simulator
        if "modelsim" in content.lower() or "questa" in content.lower():
            project.simulator = "modelsim"
        elif "ghdl" in content.lower():
            project.simulator = "ghdl"
    
    def _validate_project(self, project: ExistingVUnitProject, content: str) -> None:
        """Validate if existing project is usable"""
        # Check if it has required structure
        if not project.libraries:
            project.issues.append("No libraries defined")
        
        # Check for hardcoded paths that might not work
        if re.search(r'["\'][A-Z]:\\', content):  # Windows absolute paths
            project.issues.append("Contains hardcoded Windows paths")
        elif re.search(r'["\']/home/', content):  # Unix absolute paths
            project.issues.append("Contains hardcoded Unix paths")
        
        # Check for deprecated patterns
        if "vu.set_simulator_name" in content:
            project.issues.append("Uses deprecated set_simulator_name")
        
        # Still usable if only warnings
        if any("hardcoded" in issue.lower() for issue in project.issues):
            project.usable = False
