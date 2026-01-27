"""
UVM-SV Parser.

Extracts UVM components, sequences, and testbench structure from SystemVerilog files.
Uses regex-based parsing to identify UVM constructs without requiring full SV parser.
"""

import re
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set


class UVMComponentType(Enum):
    """Types of UVM components that can be detected."""
    TEST = "uvm_test"
    ENV = "uvm_env"
    AGENT = "uvm_agent"
    DRIVER = "uvm_driver"
    MONITOR = "uvm_monitor"
    SEQUENCER = "uvm_sequencer"
    SCOREBOARD = "uvm_scoreboard"
    SUBSCRIBER = "uvm_subscriber"
    SEQUENCE = "uvm_sequence"
    SEQUENCE_ITEM = "uvm_sequence_item"
    COMPONENT = "uvm_component"  # Generic
    OBJECT = "uvm_object"
    INTERFACE = "interface"
    MODULE = "module"
    PACKAGE = "package"
    UNKNOWN = "unknown"


@dataclass
class UVMPort:
    """Represents a port or signal in an interface or module."""
    name: str
    direction: str  # input, output, inout
    data_type: str
    width: Optional[str] = None
    is_array: bool = False


@dataclass
class UVMField:
    """Represents a field/variable in a UVM class."""
    name: str
    data_type: str
    is_rand: bool = False
    is_randc: bool = False
    default_value: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


@dataclass
class UVMMethod:
    """Represents a method/task/function in a UVM class."""
    name: str
    return_type: str
    is_task: bool  # True for task, False for function
    is_virtual: bool = False
    arguments: List[Dict[str, str]] = field(default_factory=list)
    body: str = ""
    phase_name: Optional[str] = None  # For UVM phases like build_phase, run_phase


@dataclass
class UVMConstraint:
    """Represents a constraint in a UVM class."""
    name: str
    body: str


@dataclass 
class UVMComponent:
    """Represents a parsed UVM component/class."""
    name: str
    component_type: UVMComponentType
    parent_class: Optional[str] = None
    file_path: Optional[Path] = None
    
    # Class members
    fields: List[UVMField] = field(default_factory=list)
    methods: List[UVMMethod] = field(default_factory=list)
    constraints: List[UVMConstraint] = field(default_factory=list)
    
    # Interface signals (for interfaces)
    ports: List[UVMPort] = field(default_factory=list)
    
    # UVM-specific
    config_db_gets: List[Dict[str, str]] = field(default_factory=list)
    config_db_sets: List[Dict[str, str]] = field(default_factory=list)
    tlm_connections: List[Dict[str, str]] = field(default_factory=list)
    
    # Raw source
    raw_source: str = ""
    
    # Parameters
    parameters: Dict[str, str] = field(default_factory=dict)
    
    def get_phase_method(self, phase: str) -> Optional[UVMMethod]:
        """Get method for a specific UVM phase."""
        for method in self.methods:
            if method.phase_name == phase:
                return method
        return None
    
    def has_phase(self, phase: str) -> bool:
        """Check if component implements a specific phase."""
        return self.get_phase_method(phase) is not None


@dataclass
class ParseResult:
    """Result of parsing a UVM file or project."""
    components: List[UVMComponent] = field(default_factory=list)
    interfaces: List[UVMComponent] = field(default_factory=list)
    modules: List[UVMComponent] = field(default_factory=list)
    packages: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class UVMParser:
    """
    Parser for UVM SystemVerilog files.
    
    Extracts UVM components, interfaces, and testbench structure
    using pattern matching. Not a full SV parser but handles
    common UVM constructs effectively.
    """
    
    # UVM base class patterns
    UVM_BASE_CLASSES = {
        'uvm_test': UVMComponentType.TEST,
        'uvm_env': UVMComponentType.ENV,
        'uvm_agent': UVMComponentType.AGENT,
        'uvm_driver': UVMComponentType.DRIVER,
        'uvm_monitor': UVMComponentType.MONITOR,
        'uvm_sequencer': UVMComponentType.SEQUENCER,
        'uvm_scoreboard': UVMComponentType.SCOREBOARD,
        'uvm_subscriber': UVMComponentType.SUBSCRIBER,
        'uvm_sequence': UVMComponentType.SEQUENCE,
        'uvm_sequence_item': UVMComponentType.SEQUENCE_ITEM,
        'uvm_component': UVMComponentType.COMPONENT,
        'uvm_object': UVMComponentType.OBJECT,
    }
    
    # UVM phase names
    UVM_PHASES = [
        'build_phase', 'connect_phase', 'end_of_elaboration_phase',
        'start_of_simulation_phase', 'run_phase', 'pre_reset_phase',
        'reset_phase', 'post_reset_phase', 'pre_configure_phase',
        'configure_phase', 'post_configure_phase', 'pre_main_phase',
        'main_phase', 'post_main_phase', 'pre_shutdown_phase',
        'shutdown_phase', 'post_shutdown_phase', 'extract_phase',
        'check_phase', 'report_phase', 'final_phase'
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for parsing."""
        # Class declaration pattern
        self.class_pattern = re.compile(
            r'class\s+(\w+)\s*(?:#\s*\([^)]*\))?\s*extends\s+(\w+(?:\s*#\s*\([^)]*\))?)',
            re.MULTILINE | re.DOTALL
        )
        
        # Interface declaration pattern
        self.interface_pattern = re.compile(
            r'interface\s+(\w+)\s*(?:#\s*\(([^)]*)\))?\s*(?:\([^)]*\))?\s*;',
            re.MULTILINE
        )
        
        # Module declaration pattern
        self.module_pattern = re.compile(
            r'module\s+(\w+)\s*(?:#\s*\(([^)]*)\))?\s*(?:\([^)]*\))?\s*;',
            re.MULTILINE
        )
        
        # Package declaration pattern
        self.package_pattern = re.compile(
            r'package\s+(\w+)\s*;',
            re.MULTILINE
        )
        
        # Field/variable pattern
        self.field_pattern = re.compile(
            r'(rand|randc)?\s*(logic|bit|int|byte|shortint|longint|integer|string|'
            r'\w+)\s*(?:\[([^\]]+)\])?\s*(\w+)\s*(?:=\s*([^;]+))?\s*;',
            re.MULTILINE
        )
        
        # Constraint pattern
        self.constraint_pattern = re.compile(
            r'constraint\s+(\w+)\s*\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
        
        # Task/function pattern
        self.method_pattern = re.compile(
            r'(virtual)?\s*(task|function)\s*(?:(\w+)\s+)?(\w+)\s*\(([^)]*)\)\s*;',
            re.MULTILINE
        )
        
        # Config DB get pattern
        self.config_db_get_pattern = re.compile(
            r'uvm_config_db\s*#\s*\(([^)]+)\)\s*::\s*get\s*\(\s*([^,]+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*(\w+)\s*\)',
            re.MULTILINE
        )
        
        # Config DB set pattern
        self.config_db_set_pattern = re.compile(
            r'uvm_config_db\s*#\s*\(([^)]+)\)\s*::\s*set\s*\(\s*([^,]+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*([^)]+)\s*\)',
            re.MULTILINE
        )
        
        # Port/signal pattern for interfaces
        self.port_pattern = re.compile(
            r'(input|output|inout)?\s*(logic|wire|reg|bit)?\s*(?:\[([^\]]+)\])?\s*(\w+)\s*;',
            re.MULTILINE
        )
        
        # Import pattern
        self.import_pattern = re.compile(
            r'import\s+([\w:]+)\s*;',
            re.MULTILINE
        )
        
        # Include pattern
        self.include_pattern = re.compile(
            r'`include\s+"([^"]+)"',
            re.MULTILINE
        )
        
        # Parameter pattern
        self.param_pattern = re.compile(
            r'parameter\s+(\w+)\s*=\s*([^,;]+)',
            re.MULTILINE
        )
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """
        Parse a single UVM SystemVerilog file.
        
        Args:
            file_path: Path to .sv file
            
        Returns:
            ParseResult with extracted components
        """
        result = ParseResult()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            result.errors.append(f"Failed to read {file_path}: {e}")
            return result
        
        # Remove comments for cleaner parsing
        clean_content = self._remove_comments(content)
        
        # Extract imports and includes
        result.imports = self._extract_imports(clean_content)
        result.includes = self._extract_includes(content)  # Keep original for includes
        
        # Extract parameters
        result.parameters = self._extract_parameters(clean_content)
        
        # Extract packages
        result.packages = self._extract_packages(clean_content)
        
        # Extract interfaces
        interfaces = self._extract_interfaces(clean_content, file_path)
        result.interfaces.extend(interfaces)
        
        # Extract modules
        modules = self._extract_modules(clean_content, file_path)
        result.modules.extend(modules)
        
        # Extract classes (UVM components)
        components = self._extract_classes(clean_content, file_path)
        result.components.extend(components)
        
        return result
    
    def parse_project(self, project_dir: Path, 
                      file_patterns: List[str] = None) -> ParseResult:
        """
        Parse all UVM files in a project directory.
        
        Args:
            project_dir: Root directory of UVM project
            file_patterns: Glob patterns for files (default: *.sv, *.svh)
            
        Returns:
            Aggregated ParseResult
        """
        if file_patterns is None:
            file_patterns = ['**/*.sv', '**/*.svh']
        
        result = ParseResult()
        
        for pattern in file_patterns:
            for file_path in project_dir.glob(pattern):
                file_result = self.parse_file(file_path)
                
                result.components.extend(file_result.components)
                result.interfaces.extend(file_result.interfaces)
                result.modules.extend(file_result.modules)
                result.packages.extend(file_result.packages)
                result.imports.extend(file_result.imports)
                result.includes.extend(file_result.includes)
                result.parameters.update(file_result.parameters)
                result.errors.extend(file_result.errors)
                result.warnings.extend(file_result.warnings)
        
        # Deduplicate
        result.imports = list(set(result.imports))
        result.includes = list(set(result.includes))
        result.packages = list(set(result.packages))
        
        return result
    
    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements."""
        return self.import_pattern.findall(content)
    
    def _extract_includes(self, content: str) -> List[str]:
        """Extract include directives."""
        return self.include_pattern.findall(content)
    
    def _extract_parameters(self, content: str) -> Dict[str, str]:
        """Extract parameter declarations."""
        params = {}
        for match in self.param_pattern.finditer(content):
            params[match.group(1)] = match.group(2).strip()
        return params
    
    def _extract_packages(self, content: str) -> List[str]:
        """Extract package declarations."""
        return self.package_pattern.findall(content)
    
    def _extract_interfaces(self, content: str, file_path: Path) -> List[UVMComponent]:
        """Extract interface definitions."""
        interfaces = []
        
        # Find interface blocks
        for match in self.interface_pattern.finditer(content):
            name = match.group(1)
            params_str = match.group(2) or ""
            
            # Find interface body
            start = match.end()
            body = self._find_block_body(content, start, 'endinterface')
            
            interface = UVMComponent(
                name=name,
                component_type=UVMComponentType.INTERFACE,
                file_path=file_path,
                raw_source=content[match.start():start + len(body) + 12] if body else ""
            )
            
            # Parse parameters
            if params_str:
                interface.parameters = self._parse_param_list(params_str)
            
            # Parse ports/signals
            if body:
                interface.ports = self._extract_ports(body)
                interface.fields = self._extract_fields(body)
            
            interfaces.append(interface)
        
        return interfaces
    
    def _extract_modules(self, content: str, file_path: Path) -> List[UVMComponent]:
        """Extract module definitions."""
        modules = []
        
        for match in self.module_pattern.finditer(content):
            name = match.group(1)
            params_str = match.group(2) or ""
            
            # Find module body
            start = match.end()
            body = self._find_block_body(content, start, 'endmodule')
            
            module = UVMComponent(
                name=name,
                component_type=UVMComponentType.MODULE,
                file_path=file_path,
                raw_source=content[match.start():start + len(body) + 9] if body else ""
            )
            
            # Parse parameters
            if params_str:
                module.parameters = self._parse_param_list(params_str)
            
            # Parse config_db operations (for tb_top)
            if body:
                module.config_db_gets = self._extract_config_db_gets(body)
                module.config_db_sets = self._extract_config_db_sets(body)
            
            modules.append(module)
        
        return modules
    
    def _extract_classes(self, content: str, file_path: Path) -> List[UVMComponent]:
        """Extract UVM class definitions."""
        components = []
        
        for match in self.class_pattern.finditer(content):
            class_name = match.group(1)
            parent_class = match.group(2).strip()
            
            # Determine UVM component type from parent class
            component_type = self._determine_component_type(parent_class)
            
            # Find class body
            start = match.end()
            body = self._find_block_body(content, start, 'endclass')
            
            component = UVMComponent(
                name=class_name,
                component_type=component_type,
                parent_class=parent_class,
                file_path=file_path,
                raw_source=content[match.start():start + len(body) + 8] if body else ""
            )
            
            if body:
                # Extract fields
                component.fields = self._extract_fields(body)
                
                # Extract constraints
                component.constraints = self._extract_constraints(body)
                
                # Extract methods
                component.methods = self._extract_methods(body)
                
                # Extract config_db operations
                component.config_db_gets = self._extract_config_db_gets(body)
                component.config_db_sets = self._extract_config_db_sets(body)
            
            components.append(component)
        
        return components
    
    def _determine_component_type(self, parent_class: str) -> UVMComponentType:
        """Determine UVM component type from parent class name."""
        # Remove parameterization
        base_class = re.sub(r'\s*#.*', '', parent_class).strip()
        
        for uvm_class, comp_type in self.UVM_BASE_CLASSES.items():
            if base_class == uvm_class or base_class.endswith('_' + uvm_class.split('_')[1]):
                return comp_type
        
        return UVMComponentType.UNKNOWN
    
    def _find_block_body(self, content: str, start: int, end_keyword: str) -> str:
        """Find the body of a block (class, module, interface) up to end keyword."""
        # Simple approach: find the next occurrence of end_keyword
        pattern = re.compile(rf'\b{end_keyword}\b', re.IGNORECASE)
        match = pattern.search(content, start)
        if match:
            return content[start:match.start()]
        return ""
    
    def _parse_param_list(self, params_str: str) -> Dict[str, str]:
        """Parse parameter list from declaration."""
        params = {}
        # Split by comma but handle nested parentheses
        for param in self.param_pattern.finditer(params_str):
            params[param.group(1)] = param.group(2).strip()
        return params
    
    def _extract_ports(self, content: str) -> List[UVMPort]:
        """Extract port declarations from interface/module."""
        ports = []
        
        for match in self.port_pattern.finditer(content):
            direction = match.group(1) or "logic"
            data_type = match.group(2) or "logic"
            width = match.group(3)
            name = match.group(4)
            
            ports.append(UVMPort(
                name=name,
                direction=direction,
                data_type=data_type,
                width=width
            ))
        
        return ports
    
    def _extract_fields(self, content: str) -> List[UVMField]:
        """Extract field/variable declarations."""
        fields = []
        
        for match in self.field_pattern.finditer(content):
            rand_type = match.group(1)
            data_type = match.group(2)
            width = match.group(3)
            name = match.group(4)
            default = match.group(5)
            
            if width:
                data_type = f"{data_type}[{width}]"
            
            fields.append(UVMField(
                name=name,
                data_type=data_type,
                is_rand=(rand_type == 'rand'),
                is_randc=(rand_type == 'randc'),
                default_value=default.strip() if default else None
            ))
        
        return fields
    
    def _extract_constraints(self, content: str) -> List[UVMConstraint]:
        """Extract constraint blocks."""
        constraints = []
        
        for match in self.constraint_pattern.finditer(content):
            constraints.append(UVMConstraint(
                name=match.group(1),
                body=match.group(2).strip()
            ))
        
        return constraints
    
    def _extract_methods(self, content: str) -> List[UVMMethod]:
        """Extract task and function declarations."""
        methods = []
        
        for match in self.method_pattern.finditer(content):
            is_virtual = match.group(1) is not None
            is_task = match.group(2) == 'task'
            return_type = match.group(3) or 'void'
            name = match.group(4)
            args_str = match.group(5) or ""
            
            # Parse arguments
            arguments = self._parse_arguments(args_str)
            
            # Check if it's a UVM phase
            phase_name = name if name in self.UVM_PHASES else None
            
            # Find method body
            body_start = match.end()
            end_keyword = 'endtask' if is_task else 'endfunction'
            body = self._find_block_body(content, body_start, end_keyword)
            
            methods.append(UVMMethod(
                name=name,
                return_type=return_type,
                is_task=is_task,
                is_virtual=is_virtual,
                arguments=arguments,
                body=body.strip(),
                phase_name=phase_name
            ))
        
        return methods
    
    def _parse_arguments(self, args_str: str) -> List[Dict[str, str]]:
        """Parse function/task arguments."""
        if not args_str.strip():
            return []
        
        arguments = []
        # Simple split by comma
        for arg in args_str.split(','):
            arg = arg.strip()
            if not arg:
                continue
            
            # Parse: [direction] [type] name [= default]
            parts = arg.split()
            if len(parts) >= 2:
                arguments.append({
                    'name': parts[-1].split('=')[0].strip(),
                    'type': ' '.join(parts[:-1])
                })
            elif len(parts) == 1:
                arguments.append({
                    'name': parts[0].split('=')[0].strip(),
                    'type': 'logic'
                })
        
        return arguments
    
    def _extract_config_db_gets(self, content: str) -> List[Dict[str, str]]:
        """Extract uvm_config_db::get calls."""
        gets = []
        
        for match in self.config_db_get_pattern.finditer(content):
            gets.append({
                'type': match.group(1).strip(),
                'context': match.group(2).strip(),
                'inst_name': match.group(3),
                'field_name': match.group(4),
                'variable': match.group(5).strip()
            })
        
        return gets
    
    def _extract_config_db_sets(self, content: str) -> List[Dict[str, str]]:
        """Extract uvm_config_db::set calls."""
        sets = []
        
        for match in self.config_db_set_pattern.finditer(content):
            sets.append({
                'type': match.group(1).strip(),
                'context': match.group(2).strip(),
                'inst_name': match.group(3),
                'field_name': match.group(4),
                'value': match.group(5).strip()
            })
        
        return sets

