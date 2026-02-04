"""
UVM Test Discovery
==================

Discovers UVM test classes from SystemVerilog source files.

Features:
- Parses `class X extends uvm_test` declarations
- Extracts factory-registered components
- Supports manifest-based test lists
- Generates proper UVM plusargs
- Handles complex class hierarchies
- Detects test configurations

Author: TB Eval Team
Version: 0.1.0
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
import time

from .base import BaseTestDiscovery, DiscoveryResult
from ..models import TestCase, TestStatus


# =============================================================================
# UVM COMPONENT INFO
# =============================================================================

@dataclass
class UVMComponentInfo:
    """
    Information about a UVM component
    
    Attributes:
        name: Component class name
        parent_class: Parent class name
        component_type: Type (test, env, agent, driver, etc.)
        file_path: Source file where defined
        line_number: Line number of definition
        has_factory_registration: Whether registered with factory
        factory_type_name: Factory type name if different
        is_parameterized: Whether class is parameterized
        parameters: Class parameters
    """
    name: str
    parent_class: str = ""
    component_type: str = "component"
    file_path: str = ""
    line_number: int = 0
    has_factory_registration: bool = False
    factory_type_name: Optional[str] = None
    is_parameterized: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def get_factory_name(self) -> str:
        """Get the factory registration name"""
        return self.factory_type_name or self.name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parent_class": self.parent_class,
            "component_type": self.component_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "has_factory_registration": self.has_factory_registration,
            "factory_type_name": self.factory_type_name,
            "is_parameterized": self.is_parameterized,
        }


@dataclass
class UVMTestInfo(UVMComponentInfo):
    """
    Extended information for UVM tests
    
    Attributes:
        description: Test description (from comments)
        timeout: Test timeout in ns
        verbosity: Default verbosity level
        tags: Test tags/categories
        dependencies: Required test dependencies
        plusargs: Additional plusargs for this test
    """
    component_type: str = "test"
    description: str = ""
    timeout: Optional[int] = None
    verbosity: str = "UVM_MEDIUM"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    plusargs: List[str] = field(default_factory=list)
    
    def to_test_case(self) -> TestCase:
        """Convert to TestCase"""
        # Build plusargs
        all_plusargs = [
            f"+UVM_TESTNAME={self.get_factory_name()}",
            f"+UVM_VERBOSITY={self.verbosity}",
        ]
        
        if self.timeout:
            all_plusargs.append(f"+UVM_TIMEOUT={self.timeout}")
        
        all_plusargs.extend(self.plusargs)
        
        return TestCase(
            name=self.name,
            full_name=f"uvm.{self.name}",
            testbench="uvm_top",
            library="work",
            test_type="uvm",
            status=TestStatus.READY,
            attributes={
                "description": self.description,
                "parent_class": self.parent_class,
                "file": self.file_path,
                "line": self.line_number,
                "tags": self.tags,
            },
            plusargs=all_plusargs,
            timeout_ms=self.timeout * 1000 if self.timeout else None,
        )


# =============================================================================
# UVM PARSER
# =============================================================================

class UVMParser:
    """
    Parser for UVM constructs in SystemVerilog files
    
    Extracts:
    - Class declarations extending UVM base classes
    - Factory registrations
    - Test configurations
    - Component hierarchy
    """
    
    # UVM base classes by type
    UVM_TEST_BASES = [
        'uvm_test',
    ]
    
    UVM_ENV_BASES = [
        'uvm_env',
    ]
    
    UVM_AGENT_BASES = [
        'uvm_agent',
    ]
    
    UVM_COMPONENT_BASES = [
        'uvm_component',
        'uvm_driver',
        'uvm_monitor',
        'uvm_sequencer',
        'uvm_scoreboard',
        'uvm_subscriber',
    ]
    
    UVM_OBJECT_BASES = [
        'uvm_object',
        'uvm_sequence',
        'uvm_sequence_item',
        'uvm_transaction',
    ]
    
    # Regex patterns
    PATTERNS = {
        # Class declaration: class name extends parent;
        # Handles parameterized classes: class name #(params) extends parent #(params);
        'class_decl': re.compile(
            r'class\s+(\w+)\s*(?:#\s*\([^)]*\))?\s+extends\s+(\w+)',
            re.MULTILINE | re.IGNORECASE
        ),
        
        # Factory registration macros
        'uvm_component_utils': re.compile(
            r'`uvm_component_utils\s*\(\s*(\w+)\s*\)',
            re.MULTILINE
        ),
        'uvm_component_utils_begin': re.compile(
            r'`uvm_component_utils_begin\s*\(\s*(\w+)\s*\)',
            re.MULTILINE
        ),
        'uvm_object_utils': re.compile(
            r'`uvm_object_utils\s*\(\s*(\w+)\s*\)',
            re.MULTILINE
        ),
        'uvm_component_param_utils': re.compile(
            r'`uvm_component_param_utils\s*\(\s*(\w+)\s*\)',
            re.MULTILINE
        ),
        
        # Test description from comments
        'test_description': re.compile(
            r'//\s*(?:@desc|@description|Description:?)\s*(.+?)$',
            re.MULTILINE | re.IGNORECASE
        ),
        
        # Test tags from comments
        'test_tags': re.compile(
            r'//\s*(?:@tag|@tags|@category)\s*(.+?)$',
            re.MULTILINE | re.IGNORECASE
        ),
        
        # Timeout specification
        'test_timeout': re.compile(
            r'//\s*(?:@timeout)\s*(\d+)\s*(ns|us|ms|s)?',
            re.MULTILINE | re.IGNORECASE
        ),
        
        # UVM verbosity
        'test_verbosity': re.compile(
            r'//\s*(?:@verbosity)\s*(UVM_\w+)',
            re.MULTILINE | re.IGNORECASE
        ),
    }
    
    def __init__(self):
        self.components: Dict[str, UVMComponentInfo] = {}
        self.tests: Dict[str, UVMTestInfo] = {}
        self.factory_registrations: Set[str] = set()
    
    def parse_file(self, file_path: Path, content: str) -> None:
        """
        Parse a single file for UVM components
        
        Args:
            file_path: Path to the file
            content: File content
        """
        # Find all class declarations
        for match in self.PATTERNS['class_decl'].finditer(content):
            class_name = match.group(1)
            parent_class = match.group(2)
            line_number = content[:match.start()].count('\n') + 1
            
            # Determine component type from parent
            component_type = self._get_component_type(parent_class)
            
            if component_type == "test":
                # Create UVMTestInfo
                test_info = UVMTestInfo(
                    name=class_name,
                    parent_class=parent_class,
                    file_path=str(file_path),
                    line_number=line_number,
                )
                
                # Extract additional info from surrounding comments
                self._extract_test_metadata(content, match.start(), test_info)
                
                self.tests[class_name] = test_info
                
            elif component_type:
                # Create UVMComponentInfo
                component_info = UVMComponentInfo(
                    name=class_name,
                    parent_class=parent_class,
                    component_type=component_type,
                    file_path=str(file_path),
                    line_number=line_number,
                )
                
                self.components[class_name] = component_info
        
        # Find factory registrations
        self._parse_factory_registrations(content)
        
        # Update components with factory info
        self._update_factory_info()
    
    def _get_component_type(self, parent_class: str) -> Optional[str]:
        """Determine component type from parent class"""
        parent_lower = parent_class.lower()
        
        if parent_lower in [p.lower() for p in self.UVM_TEST_BASES]:
            return "test"
        elif parent_lower in [p.lower() for p in self.UVM_ENV_BASES]:
            return "env"
        elif parent_lower in [p.lower() for p in self.UVM_AGENT_BASES]:
            return "agent"
        elif parent_lower in [p.lower() for p in self.UVM_COMPONENT_BASES]:
            return "component"
        elif parent_lower in [p.lower() for p in self.UVM_OBJECT_BASES]:
            return "object"
        
        # Check if parent is a known component (inheritance)
        if parent_class in self.tests:
            return "test"
        if parent_class in self.components:
            return self.components[parent_class].component_type
        
        return None
    
    def _parse_factory_registrations(self, content: str) -> None:
        """Find all factory registration macros"""
        for pattern_name in ['uvm_component_utils', 'uvm_component_utils_begin', 
                            'uvm_object_utils', 'uvm_component_param_utils']:
            pattern = self.PATTERNS[pattern_name]
            for match in pattern.finditer(content):
                class_name = match.group(1)
                self.factory_registrations.add(class_name)
    
    def _update_factory_info(self) -> None:
        """Update components with factory registration info"""
        for test_name, test_info in self.tests.items():
            test_info.has_factory_registration = test_name in self.factory_registrations
        
        for comp_name, comp_info in self.components.items():
            comp_info.has_factory_registration = comp_name in self.factory_registrations
    
    def _extract_test_metadata(
        self,
        content: str,
        class_start: int,
        test_info: UVMTestInfo
    ) -> None:
        """Extract test metadata from comments near class declaration"""
        # Look at the 500 characters before class declaration
        search_start = max(0, class_start - 500)
        search_region = content[search_start:class_start]
        
        # Extract description
        desc_match = self.PATTERNS['test_description'].search(search_region)
        if desc_match:
            test_info.description = desc_match.group(1).strip()
        
        # Extract tags
        tags_match = self.PATTERNS['test_tags'].search(search_region)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            test_info.tags = [t.strip() for t in re.split(r'[,\s]+', tags_str) if t.strip()]
        
        # Extract timeout
        timeout_match = self.PATTERNS['test_timeout'].search(search_region)
        if timeout_match:
            timeout_value = int(timeout_match.group(1))
            unit = timeout_match.group(2) or 'ns'
            
            # Convert to nanoseconds
            unit_multipliers = {'ns': 1, 'us': 1000, 'ms': 1000000, 's': 1000000000}
            test_info.timeout = timeout_value * unit_multipliers.get(unit.lower(), 1)
        
        # Extract verbosity
        verbosity_match = self.PATTERNS['test_verbosity'].search(search_region)
        if verbosity_match:
            test_info.verbosity = verbosity_match.group(1).upper()
    
    def get_tests(self) -> List[UVMTestInfo]:
        """Get all discovered tests"""
        return list(self.tests.values())
    
    def get_components(self) -> List[UVMComponentInfo]:
        """Get all discovered components"""
        return list(self.components.values())
    
    def get_test_hierarchy(self) -> Dict[str, List[str]]:
        """
        Get test inheritance hierarchy
        
        Returns:
            Dict mapping parent test to child tests
        """
        hierarchy = {}
        
        for test_name, test_info in self.tests.items():
            parent = test_info.parent_class
            
            # Check if parent is also a test
            if parent in self.tests:
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(test_name)
        
        return hierarchy


# =============================================================================
# UVM TEST DISCOVERY
# =============================================================================

class UVMTestDiscovery(BaseTestDiscovery):
    """
    Discovers UVM tests from SystemVerilog source files
    
    Usage:
        discovery = UVMTestDiscovery(submission_dir)
        result = discovery.discover(tb_files)
        
        for test in result.tests:
            print(f"Test: {test.name}")
            print(f"Plusargs: {test.plusargs}")
    
    Features:
        - Parses class declarations extending uvm_test
        - Supports test inheritance (test extending another test)
        - Extracts test metadata from comments
        - Supports manifest-based test lists
        - Generates proper UVM plusargs
    """
    
    # File extensions to scan
    VALID_EXTENSIONS = ['.sv', '.svh', '.v', '.vh']
    
    def __init__(
        self,
        submission_dir: Path,
        manifest_tests: Optional[List[str]] = None,
        default_verbosity: str = "UVM_MEDIUM",
        default_timeout: Optional[int] = None,
    ):
        """
        Initialize UVM test discovery
        
        Args:
            submission_dir: Path to submission directory
            manifest_tests: Optional list of tests from manifest
            default_verbosity: Default UVM verbosity level
            default_timeout: Default test timeout in ns
        """
        super().__init__(submission_dir)
        self.manifest_tests = manifest_tests or []
        self.default_verbosity = default_verbosity
        self.default_timeout = default_timeout
        self.parser = UVMParser()
    
    def get_discovery_method(self) -> str:
        return "uvm_class_parsing"
    
    def discover(self, source_files: List[Path]) -> DiscoveryResult:
        """
        Discover UVM tests from source files
        
        Args:
            source_files: List of SystemVerilog files to scan
        
        Returns:
            DiscoveryResult with discovered UVM tests
        """
        result = DiscoveryResult(
            discovery_method=self.get_discovery_method(),
        )
        
        start_time = time.time()
        
        # Filter to valid extensions
        sv_files = [
            f for f in source_files 
            if f.suffix.lower() in self.VALID_EXTENSIONS
        ]
        
        result.source_files = [str(f) for f in sv_files]
        
        # Parse all files
        for file_path in sv_files:
            try:
                content = self.read_file_safe(file_path)
                if content:
                    self.parser.parse_file(file_path, content)
            except Exception as e:
                result.warnings.append(f"Failed to parse {file_path}: {str(e)}")
        
        # Get discovered tests
        discovered_tests = self.parser.get_tests()
        
        # Apply manifest filter if provided
        if self.manifest_tests:
            discovered_tests = self._filter_by_manifest(discovered_tests)
        
        # Apply defaults
        for test_info in discovered_tests:
            if not test_info.verbosity:
                test_info.verbosity = self.default_verbosity
            if not test_info.timeout and self.default_timeout:
                test_info.timeout = self.default_timeout
        
        # Convert to TestCase objects
        for test_info in discovered_tests:
            # Skip tests without factory registration (can't be run)
            if not test_info.has_factory_registration:
                result.warnings.append(
                    f"Test '{test_info.name}' has no factory registration "
                    f"(`uvm_component_utils). It may not be runnable."
                )
            
            test_case = test_info.to_test_case()
            result.tests.append(test_case)
        
        # Add metadata
        result.metadata = {
            "total_components": len(self.parser.get_components()),
            "test_hierarchy": self.parser.get_test_hierarchy(),
            "factory_registered_tests": sum(
                1 for t in discovered_tests if t.has_factory_registration
            ),
        }
        
        result.duration_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _filter_by_manifest(
        self,
        tests: List[UVMTestInfo]
    ) -> List[UVMTestInfo]:
        """Filter tests based on manifest list"""
        if not self.manifest_tests:
            return tests
        
        manifest_set = set(self.manifest_tests)
        
        filtered = []
        for test in tests:
            if test.name in manifest_set or test.get_factory_name() in manifest_set:
                filtered.append(test)
        
        return filtered
    
    def discover_from_directory(
        self,
        directory: Optional[Path] = None,
        recursive: bool = True
    ) -> DiscoveryResult:
        """
        Discover tests from a directory
        
        Args:
            directory: Directory to scan (default: submission_dir)
            recursive: Whether to scan recursively
        
        Returns:
            DiscoveryResult with discovered tests
        """
        scan_dir = directory or self.submission_dir
        
        if recursive:
            files = list(scan_dir.rglob("*"))
        else:
            files = list(scan_dir.glob("*"))
        
        sv_files = [
            f for f in files 
            if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS
        ]
        
        return self.timed_discover(sv_files)
    
    def get_test_by_name(self, test_name: str) -> Optional[UVMTestInfo]:
        """Get test info by name"""
        return self.parser.tests.get(test_name)
    
    def get_all_components(self) -> List[UVMComponentInfo]:
        """Get all discovered UVM components"""
        return self.parser.get_components()
    
    def get_test_count(self) -> int:
        """Get total number of discovered tests"""
        return len(self.parser.tests)
    
    def generate_test_list_file(
        self,
        output_path: Path,
        format: str = "txt"
    ) -> None:
        """
        Generate test list file
        
        Args:
            output_path: Path for output file
            format: Output format (txt, json, yaml)
        """
        tests = self.parser.get_tests()
        
        if format == "txt":
            with open(output_path, 'w') as f:
                f.write("# UVM Test List\n")
                f.write("# Generated by TB Eval Framework\n\n")
                for test in tests:
                    status = "✓" if test.has_factory_registration else "?"
                    f.write(f"{status} {test.name}\n")
                    if test.description:
                        f.write(f"  # {test.description}\n")
        
        elif format == "json":
            import json
            data = {
                "tests": [t.to_dict() for t in tests],
                "count": len(tests),
            }
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == "yaml":
            import yaml
            data = {
                "tests": [{"name": t.name, "description": t.description} for t in tests],
            }
            with open(output_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def discover_uvm_tests(
    submission_dir: Path,
    tb_files: Optional[List[Path]] = None,
    manifest_tests: Optional[List[str]] = None,
) -> DiscoveryResult:
    """
    Convenience function to discover UVM tests
    
    Args:
        submission_dir: Path to submission directory
        tb_files: Optional list of TB files (auto-detected if not provided)
        manifest_tests: Optional list of tests from manifest
    
    Returns:
        DiscoveryResult with discovered tests
    """
    discovery = UVMTestDiscovery(
        submission_dir=submission_dir,
        manifest_tests=manifest_tests,
    )
    
    if tb_files:
        return discovery.timed_discover(tb_files)
    else:
        return discovery.discover_from_directory()


def parse_uvm_file(file_path: Path) -> Tuple[List[UVMTestInfo], List[UVMComponentInfo]]:
    """
    Parse a single UVM file
    
    Args:
        file_path: Path to SystemVerilog file
    
    Returns:
        Tuple of (tests, components)
    """
    parser = UVMParser()
    
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    parser.parse_file(file_path, content)
    
    return parser.get_tests(), parser.get_components()
