"""
UVM Testbench Analyzer.

Analyzes parsed UVM components to understand testbench structure,
hierarchy, and dependencies. Prepares structured data for translation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from pathlib import Path

from .parser import (
    UVMParser, ParseResult, UVMComponent, UVMComponentType,
    UVMField, UVMMethod, UVMPort, UVMConstraint
)


@dataclass
class SignalInfo:
    """Information about a DUT signal for cocotb."""
    name: str
    direction: str  # input, output, inout
    width: int = 1
    is_clock: bool = False
    is_reset: bool = False
    cocotb_name: str = ""  # e.g., dut.signal_name


@dataclass
class TransactionInfo:
    """Information about a UVM transaction/sequence_item."""
    name: str
    fields: List[Dict[str, Any]]
    constraints: List[Dict[str, str]]
    has_randomization: bool = False


@dataclass
class DriverInfo:
    """Information about a UVM driver."""
    name: str
    interface_signals: List[SignalInfo]
    drive_logic: str = ""  # Extracted driving logic


@dataclass
class MonitorInfo:
    """Information about a UVM monitor."""
    name: str
    interface_signals: List[SignalInfo]
    sample_logic: str = ""  # Extracted sampling logic


@dataclass
class SequenceInfo:
    """Information about a UVM sequence."""
    name: str
    transaction_type: str
    body_logic: str = ""
    is_random: bool = False


@dataclass
class AgentInfo:
    """Information about a complete UVM agent."""
    name: str
    driver: Optional[DriverInfo] = None
    monitor: Optional[MonitorInfo] = None
    sequencer_type: Optional[str] = None
    is_active: bool = True


@dataclass
class ScoreboardInfo:
    """Information about a UVM scoreboard."""
    name: str
    expected_transaction_type: str = ""
    actual_transaction_type: str = ""
    compare_logic: str = ""


@dataclass
class UVMTestbenchStructure:
    """Complete analyzed structure of a UVM testbench."""
    
    # Project info
    project_name: str = ""
    source_files: List[Path] = field(default_factory=list)
    
    # DUT info
    dut_name: str = ""
    dut_signals: List[SignalInfo] = field(default_factory=list)
    dut_parameters: Dict[str, str] = field(default_factory=dict)
    
    # Interface info
    interface_name: str = ""
    interface_signals: List[SignalInfo] = field(default_factory=list)
    
    # Testbench components
    test_name: str = ""
    env_name: str = ""
    agents: List[AgentInfo] = field(default_factory=list)
    scoreboard: Optional[ScoreboardInfo] = None
    
    # Transactions
    transactions: List[TransactionInfo] = field(default_factory=list)
    
    # Sequences
    sequences: List[SequenceInfo] = field(default_factory=list)
    
    # Clock/reset info
    clock_signal: str = "clk"
    reset_signal: str = "rst_n"
    reset_active_low: bool = True
    clock_period_ns: int = 10
    
    # Analysis metadata
    complexity_score: float = 0.0
    translation_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'project_name': self.project_name,
            'dut_name': self.dut_name,
            'dut_signals': [
                {'name': s.name, 'direction': s.direction, 'width': s.width}
                for s in self.dut_signals
            ],
            'interface_name': self.interface_name,
            'test_name': self.test_name,
            'env_name': self.env_name,
            'agents': [
                {'name': a.name, 'is_active': a.is_active}
                for a in self.agents
            ],
            'transactions': [
                {'name': t.name, 'fields': t.fields}
                for t in self.transactions
            ],
            'sequences': [
                {'name': s.name, 'transaction_type': s.transaction_type}
                for s in self.sequences
            ],
            'clock_signal': self.clock_signal,
            'reset_signal': self.reset_signal,
            'complexity_score': self.complexity_score,
            'warnings': self.warnings
        }


class UVMAnalyzer:
    """
    Analyzes parsed UVM testbench to extract structure and dependencies.
    
    Prepares data for translation to Python/cocotb by identifying:
    - DUT interface signals
    - UVM component hierarchy
    - Transaction fields and constraints
    - Sequence operations
    - Scoreboard logic
    """
    
    # Common clock signal names
    CLOCK_PATTERNS = ['clk', 'clock', 'CLK', 'CLOCK', 'sys_clk', 'sysclk']
    
    # Common reset signal names
    RESET_PATTERNS = ['rst', 'reset', 'rst_n', 'rstn', 'reset_n', 'RST', 'RESET']
    
    def __init__(self):
        self.parser = UVMParser()
    
    def analyze(self, parse_result: ParseResult) -> UVMTestbenchStructure:
        """
        Analyze parsed UVM components to extract testbench structure.
        
        Args:
            parse_result: Result from UVMParser
            
        Returns:
            UVMTestbenchStructure with analyzed information
        """
        structure = UVMTestbenchStructure()
        
        # Extract source files
        structure.source_files = list(set(
            c.file_path for c in parse_result.components + 
            parse_result.interfaces + parse_result.modules
            if c.file_path
        ))
        
        # Analyze interfaces
        self._analyze_interfaces(parse_result.interfaces, structure)
        
        # Analyze modules (for DUT/tb_top)
        self._analyze_modules(parse_result.modules, structure)
        
        # Analyze UVM components
        self._analyze_components(parse_result.components, structure)
        
        # Identify clock/reset
        self._identify_clock_reset(structure)
        
        # Calculate complexity
        structure.complexity_score = self._calculate_complexity(structure)
        
        # Generate translation notes
        structure.translation_notes = self._generate_translation_notes(structure)
        
        return structure
    
    def analyze_project(self, project_dir: Path) -> UVMTestbenchStructure:
        """
        Parse and analyze a complete UVM project.
        
        Args:
            project_dir: Root directory of UVM project
            
        Returns:
            UVMTestbenchStructure with complete analysis
        """
        parse_result = self.parser.parse_project(project_dir)
        structure = self.analyze(parse_result)
        structure.project_name = project_dir.name
        return structure
    
    def _analyze_interfaces(self, interfaces: List[UVMComponent], 
                           structure: UVMTestbenchStructure) -> None:
        """Analyze interface definitions."""
        for interface in interfaces:
            if not structure.interface_name:
                structure.interface_name = interface.name
            
            # Extract signals from interface
            for port in interface.ports:
                signal = SignalInfo(
                    name=port.name,
                    direction=port.direction,
                    width=self._parse_width(port.width),
                    cocotb_name=f"dut.{port.name}"
                )
                
                # Check for clock/reset
                signal.is_clock = any(p in port.name.lower() for p in ['clk', 'clock'])
                signal.is_reset = any(p in port.name.lower() for p in ['rst', 'reset'])
                
                structure.interface_signals.append(signal)
            
            # Also extract fields as potential signals
            for field in interface.fields:
                if not any(s.name == field.name for s in structure.interface_signals):
                    signal = SignalInfo(
                        name=field.name,
                        direction='logic',  # Internal signal
                        width=self._parse_width_from_type(field.data_type),
                        cocotb_name=f"dut.{field.name}"
                    )
                    structure.interface_signals.append(signal)
            
            # Store parameters
            structure.dut_parameters.update(interface.parameters)
    
    def _analyze_modules(self, modules: List[UVMComponent], 
                        structure: UVMTestbenchStructure) -> None:
        """Analyze module definitions (DUT, tb_top)."""
        for module in modules:
            # Check if it's the DUT or tb_top
            if 'tb' in module.name.lower() or 'top' in module.name.lower():
                # This is likely tb_top
                self._extract_tb_top_info(module, structure)
            else:
                # Assume it's DUT
                structure.dut_name = module.name
                structure.dut_parameters.update(module.parameters)
    
    def _extract_tb_top_info(self, module: UVMComponent, 
                            structure: UVMTestbenchStructure) -> None:
        """Extract information from tb_top module."""
        # Look for clock period parameter
        for param_name, param_value in module.parameters.items():
            if 'clk' in param_name.lower() and 'period' in param_name.lower():
                try:
                    structure.clock_period_ns = int(param_value)
                except ValueError:
                    pass
    
    def _analyze_components(self, components: List[UVMComponent], 
                           structure: UVMTestbenchStructure) -> None:
        """Analyze UVM class components."""
        # Group by type
        tests = []
        envs = []
        agents = []
        drivers = []
        monitors = []
        sequencers = []
        scoreboards = []
        sequences = []
        seq_items = []
        
        for comp in components:
            if comp.component_type == UVMComponentType.TEST:
                tests.append(comp)
            elif comp.component_type == UVMComponentType.ENV:
                envs.append(comp)
            elif comp.component_type == UVMComponentType.AGENT:
                agents.append(comp)
            elif comp.component_type == UVMComponentType.DRIVER:
                drivers.append(comp)
            elif comp.component_type == UVMComponentType.MONITOR:
                monitors.append(comp)
            elif comp.component_type == UVMComponentType.SEQUENCER:
                sequencers.append(comp)
            elif comp.component_type == UVMComponentType.SCOREBOARD:
                scoreboards.append(comp)
            elif comp.component_type == UVMComponentType.SEQUENCE:
                sequences.append(comp)
            elif comp.component_type == UVMComponentType.SEQUENCE_ITEM:
                seq_items.append(comp)
        
        # Process tests
        if tests:
            structure.test_name = tests[0].name
        
        # Process envs
        if envs:
            structure.env_name = envs[0].name
        
        # Process sequence items (transactions)
        for item in seq_items:
            transaction = self._analyze_transaction(item)
            structure.transactions.append(transaction)
        
        # Process sequences
        for seq in sequences:
            seq_info = self._analyze_sequence(seq)
            structure.sequences.append(seq_info)
        
        # Process agents
        for agent in agents:
            agent_info = self._analyze_agent(agent, drivers, monitors)
            structure.agents.append(agent_info)
        
        # Process scoreboards
        if scoreboards:
            structure.scoreboard = self._analyze_scoreboard(scoreboards[0])
    
    def _analyze_transaction(self, component: UVMComponent) -> TransactionInfo:
        """Analyze a sequence item/transaction class."""
        fields = []
        
        for f in component.fields:
            fields.append({
                'name': f.name,
                'type': f.data_type,
                'is_rand': f.is_rand,
                'is_randc': f.is_randc,
                'default': f.default_value
            })
        
        constraints = []
        for c in component.constraints:
            constraints.append({
                'name': c.name,
                'body': c.body
            })
        
        return TransactionInfo(
            name=component.name,
            fields=fields,
            constraints=constraints,
            has_randomization=any(f.is_rand or f.is_randc for f in component.fields)
        )
    
    def _analyze_sequence(self, component: UVMComponent) -> SequenceInfo:
        """Analyze a sequence class."""
        # Find body method
        body_method = None
        for method in component.methods:
            if method.name == 'body':
                body_method = method
                break
        
        # Try to determine transaction type from parent class
        trans_type = ""
        if component.parent_class:
            # Extract from uvm_sequence#(transaction_type)
            import re
            match = re.search(r'#\s*\(\s*(\w+)\s*\)', component.parent_class)
            if match:
                trans_type = match.group(1)
        
        return SequenceInfo(
            name=component.name,
            transaction_type=trans_type,
            body_logic=body_method.body if body_method else "",
            is_random=bool(body_method and 'randomize' in body_method.body.lower())
        )
    
    def _analyze_agent(self, agent: UVMComponent, 
                      drivers: List[UVMComponent],
                      monitors: List[UVMComponent]) -> AgentInfo:
        """Analyze an agent and its components."""
        agent_info = AgentInfo(name=agent.name)
        
        # Check is_active field
        for f in agent.fields:
            if 'active' in f.name.lower():
                agent_info.is_active = True
                break
        
        # Find associated driver
        for driver in drivers:
            if agent.name.replace('_agent', '') in driver.name:
                agent_info.driver = self._analyze_driver(driver)
                break
        
        # Find associated monitor
        for monitor in monitors:
            if agent.name.replace('_agent', '') in monitor.name:
                agent_info.monitor = self._analyze_monitor(monitor)
                break
        
        return agent_info
    
    def _analyze_driver(self, component: UVMComponent) -> DriverInfo:
        """Analyze a driver class."""
        # Find run_phase method
        run_phase = None
        for method in component.methods:
            if method.phase_name == 'run_phase':
                run_phase = method
                break
        
        return DriverInfo(
            name=component.name,
            interface_signals=[],  # Will be populated from interface
            drive_logic=run_phase.body if run_phase else ""
        )
    
    def _analyze_monitor(self, component: UVMComponent) -> MonitorInfo:
        """Analyze a monitor class."""
        # Find run_phase method
        run_phase = None
        for method in component.methods:
            if method.phase_name == 'run_phase':
                run_phase = method
                break
        
        return MonitorInfo(
            name=component.name,
            interface_signals=[],
            sample_logic=run_phase.body if run_phase else ""
        )
    
    def _analyze_scoreboard(self, component: UVMComponent) -> ScoreboardInfo:
        """Analyze a scoreboard class."""
        return ScoreboardInfo(
            name=component.name
        )
    
    def _identify_clock_reset(self, structure: UVMTestbenchStructure) -> None:
        """Identify clock and reset signals."""
        all_signals = structure.interface_signals + structure.dut_signals
        
        # Find clock
        for signal in all_signals:
            if signal.is_clock:
                structure.clock_signal = signal.name
                break
        
        # Find reset
        for signal in all_signals:
            if signal.is_reset:
                structure.reset_signal = signal.name
                structure.reset_active_low = '_n' in signal.name or 'n' == signal.name[-1]
                break
    
    def _parse_width(self, width_str: Optional[str]) -> int:
        """Parse width from width string like [7:0]."""
        if not width_str:
            return 1
        
        import re
        match = re.search(r'(\d+)\s*:\s*(\d+)', width_str)
        if match:
            high = int(match.group(1))
            low = int(match.group(2))
            return abs(high - low) + 1
        
        return 1
    
    def _parse_width_from_type(self, type_str: str) -> int:
        """Parse width from type string like logic[7:0]."""
        import re
        match = re.search(r'\[(\d+)\s*:\s*(\d+)\]', type_str)
        if match:
            high = int(match.group(1))
            low = int(match.group(2))
            return abs(high - low) + 1
        return 1
    
    def _calculate_complexity(self, structure: UVMTestbenchStructure) -> float:
        """Calculate complexity score for translation difficulty."""
        score = 0.0
        
        # Base score for having components
        if structure.agents:
            score += 20.0 * len(structure.agents)
        if structure.transactions:
            score += 10.0 * len(structure.transactions)
        if structure.sequences:
            score += 15.0 * len(structure.sequences)
        if structure.scoreboard:
            score += 25.0
        
        # Add for constraints
        for trans in structure.transactions:
            score += 5.0 * len(trans.constraints)
        
        # Add for signals
        score += 2.0 * len(structure.interface_signals)
        
        # Normalize to 0-100
        return min(100.0, score)
    
    def _generate_translation_notes(self, structure: UVMTestbenchStructure) -> List[str]:
        """Generate notes about translation considerations."""
        notes = []
        
        if structure.complexity_score > 70:
            notes.append("Complex testbench - translation may require manual review")
        
        if structure.scoreboard:
            notes.append("Scoreboard detected - will translate to Python assertion checks")
        
        for trans in structure.transactions:
            if trans.has_randomization:
                notes.append(f"Transaction {trans.name} has randomization - using Python random")
            if trans.constraints:
                notes.append(f"Transaction {trans.name} has constraints - will be approximated")
        
        if not structure.interface_signals:
            notes.append("WARNING: No interface signals detected - manual signal mapping may be needed")
        
        return notes

