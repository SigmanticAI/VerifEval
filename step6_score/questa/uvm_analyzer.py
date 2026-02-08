"""
UVM conformance analyzer for Questa

Analyzes UVM (Universal Verification Methodology) testbench structure
and conformance to UVM best practices:
- Component hierarchy
- Sequence library usage
- Configuration objects
- Phase usage (build, connect, run)
- Factory registration
- TLM usage

Supports:
- Log file parsing
- Source code analysis (Python-based)
- Questa UVM report parsing

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
from enum import Enum
import re
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    UVMConformanceMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class UVMPhase(Enum):
    """UVM phases"""
    BUILD = "build_phase"
    CONNECT = "connect_phase"
    END_OF_ELABORATION = "end_of_elaboration_phase"
    START_OF_SIMULATION = "start_of_simulation_phase"
    RUN = "run_phase"
    EXTRACT = "extract_phase"
    CHECK = "check_phase"
    REPORT = "report_phase"
    FINAL = "final_phase"


class UVMComponentType(Enum):
    """UVM component types"""
    TEST = "test"
    ENV = "env"
    AGENT = "agent"
    SEQUENCER = "sequencer"
    DRIVER = "driver"
    MONITOR = "monitor"
    SCOREBOARD = "scoreboard"
    SUBSCRIBER = "subscriber"
    COMPONENT = "component"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class UVMComponentData:
    """
    UVM component data
    
    Attributes:
        name: Component name
        type: Component type
        parent: Parent component name
        children: List of child component names
        phases_used: Set of phases implemented
        factory_registered: Whether registered with factory
        config_used: Whether uses configuration objects
        tlm_ports: Number of TLM ports
    """
    name: str
    type: UVMComponentType
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    phases_used: Set[UVMPhase] = field(default_factory=set)
    factory_registered: bool = False
    config_used: bool = False
    tlm_ports: int = 0


@dataclass
class UVMSequenceData:
    """
    UVM sequence data
    
    Attributes:
        name: Sequence name
        base_class: Base sequence class
        body_implemented: Whether body() task is implemented
        pre_post_used: Whether pre_body/post_body used
        factory_registered: Whether registered with factory
        randomized: Whether uses randomization
    """
    name: str
    base_class: str
    body_implemented: bool = False
    pre_post_used: bool = False
    factory_registered: bool = False
    randomized: bool = False


@dataclass
class UVMHierarchyData:
    """
    Complete UVM testbench hierarchy
    
    Attributes:
        components: Dictionary of components (name -> UVMComponentData)
        sequences: Dictionary of sequences (name -> UVMSequenceData)
        top_test: Name of top-level test
        max_depth: Maximum hierarchy depth
    """
    components: Dict[str, UVMComponentData] = field(default_factory=dict)
    sequences: Dict[str, UVMSequenceData] = field(default_factory=dict)
    top_test: Optional[str] = None
    max_depth: int = 0
    
    def calculate_depth(self) -> int:
        """Calculate maximum hierarchy depth"""
        def get_depth(comp_name: str, current_depth: int = 0) -> int:
            if comp_name not in self.components:
                return current_depth
            
            comp = self.components[comp_name]
            if not comp.children:
                return current_depth
            
            max_child_depth = current_depth
            for child in comp.children:
                child_depth = get_depth(child, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        if self.top_test:
            self.max_depth = get_depth(self.top_test)
        
        return self.max_depth


# =============================================================================
# UVM ANALYZER
# =============================================================================

class UVMAnalyzer:
    """
    Analyze UVM testbench structure and conformance
    
    Analyzes:
    1. Component hierarchy
    2. Sequence library
    3. Phase usage
    4. Configuration objects
    5. Factory registration
    """
    
    def __init__(self):
        """Initialize UVM analyzer"""
        self.hierarchy = UVMHierarchyData()
    
    def analyze_log(self, log_path: Path) -> UVMHierarchyData:
        """
        Analyze UVM testbench from simulation log
        
        Args:
            log_path: Path to simulation log file
        
        Returns:
            UVMHierarchyData with hierarchy information
        """
        log_path = Path(log_path)
        
        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_path}")
        
        logger.info(f"Analyzing UVM log: {log_path}")
        
        log_text = log_path.read_text()
        self._parse_uvm_topology(log_text)
        self._parse_uvm_phases(log_text)
        self._parse_factory_registrations(log_text)
        
        self.hierarchy.calculate_depth()
        
        logger.info(
            f"Analyzed UVM testbench: {len(self.hierarchy.components)} components, "
            f"{len(self.hierarchy.sequences)} sequences, depth: {self.hierarchy.max_depth}"
        )
        
        return self.hierarchy
    
    def analyze_source(self, source_dir: Path) -> UVMHierarchyData:
        """
        Analyze UVM testbench from source files
        
        Args:
            source_dir: Directory containing UVM source files
        
        Returns:
            UVMHierarchyData with hierarchy information
        """
        source_dir = Path(source_dir)
        
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        logger.info(f"Analyzing UVM source in: {source_dir}")
        
        # Find all SystemVerilog files
        sv_files = list(source_dir.rglob("*.sv")) + list(source_dir.rglob("*.svh"))
        
        for sv_file in sv_files:
            self._parse_source_file(sv_file)
        
        self.hierarchy.calculate_depth()
        
        logger.info(
            f"Analyzed UVM source: {len(self.hierarchy.components)} components, "
            f"{len(self.hierarchy.sequences)} sequences"
        )
        
        return self.hierarchy
    
    def _parse_uvm_topology(self, log_text: str) -> None:
        """Parse UVM topology from log"""
        lines = log_text.split('\n')
        
        # Look for UVM topology report
        # Example:
        # UVM_INFO @ 0: reporter [RNTST] Running test my_test...
        # Name                     Type                      Size  Value
        # ----------------------------------------------------------------
        # uvm_test_top             my_test                   -     @336
        #   env                    my_env                    -     @344
        #     agent                my_agent                  -     @352
        #       sequencer          uvm_sequencer             -     @360
        #       driver             my_driver                 -     @368
        
        in_topology = False
        current_indent = 0
        parent_stack = []
        
        for line in lines:
            # Detect topology section
            if "UVM topology" in line or "UVM component hierarchy" in line:
                in_topology = True
                continue
            
            if not in_topology:
                continue
            
            # End of topology
            if line.strip() == "" or line.startswith("---"):
                if in_topology and self.hierarchy.components:
                    break
                continue
            
            # Parse component line
            # Format: "  component_name    component_type    -    @address"
            match = re.match(r'^(\s*)(\S+)\s+(\S+)\s+', line)
            if match:
                indent = len(match.group(1))
                name = match.group(2)
                comp_type = match.group(3)
                
                # Determine component type
                uvm_type = self._classify_component_type(name, comp_type)
                
                # Determine parent
                parent = None
                if indent > 0:
                    # Find parent based on indent
                    while parent_stack and parent_stack[-1][1] >= indent:
                        parent_stack.pop()
                    
                    if parent_stack:
                        parent = parent_stack[-1][0]
                
                # Create component
                component = UVMComponentData(
                    name=name,
                    type=uvm_type,
                    parent=parent
                )
                
                self.hierarchy.components[name] = component
                
                # Add to parent's children
                if parent and parent in self.hierarchy.components:
                    self.hierarchy.components[parent].children.append(name)
                
                # Update parent stack
                parent_stack.append((name, indent))
                
                # Track top test
                if uvm_type == UVMComponentType.TEST and not self.hierarchy.top_test:
                    self.hierarchy.top_test = name
                
                logger.debug(f"Found component: {name} (type: {uvm_type.value}, parent: {parent})")
    
    def _parse_uvm_phases(self, log_text: str) -> None:
        """Parse UVM phase execution from log"""
        lines = log_text.split('\n')
        
        # Look for phase execution messages
        # Example: "UVM_INFO @ 0: uvm_test_top.env [BUILD] Building environment..."
        
        for line in lines:
            # Match phase execution
            for phase in UVMPhase:
                if phase.value in line.lower():
                    # Extract component name
                    match = re.search(r'[@:][\s]*([a-zA-Z0-9_.]+)', line)
                    if match:
                        comp_name = match.group(1)
                        
                        # Find component (may need to extract base name)
                        for name, comp in self.hierarchy.components.items():
                            if name in comp_name:
                                comp.phases_used.add(phase)
                                break
    
    def _parse_factory_registrations(self, log_text: str) -> None:
        """Parse factory registrations from log"""
        # Look for factory override messages or registration info
        # Example: "UVM_INFO @ 0: reporter [FACTORY] Registering type my_driver..."
        
        for line in log_text.split('\n'):
            if "factory" in line.lower() and "register" in line.lower():
                # Extract type name
                match = re.search(r'type\s+([a-zA-Z0-9_]+)', line)
                if match:
                    type_name = match.group(1)
                    
                    # Mark component as factory registered
                    for comp in self.hierarchy.components.values():
                        if type_name in comp.name:
                            comp.factory_registered = True
    
    def _parse_source_file(self, file_path: Path) -> None:
        """Parse UVM source file for component/sequence definitions"""
        try:
            content = file_path.read_text()
            
            # Find UVM component definitions
            # Pattern: class my_driver extends uvm_driver
            comp_pattern = r'class\s+(\w+)\s+extends\s+(uvm_\w+)'
            for match in re.finditer(comp_pattern, content):
                class_name = match.group(1)
                base_class = match.group(2)
                
                comp_type = self._classify_component_type(class_name, base_class)
                
                if class_name not in self.hierarchy.components:
                    component = UVMComponentData(
                        name=class_name,
                        type=comp_type
                    )
                    self.hierarchy.components[class_name] = component
            
            # Find UVM sequence definitions
            seq_pattern = r'class\s+(\w+)\s+extends\s+(uvm_sequence)'
            for match in re.finditer(seq_pattern, content):
                seq_name = match.group(1)
                base_class = match.group(2)
                
                if seq_name not in self.hierarchy.sequences:
                    sequence = UVMSequenceData(
                        name=seq_name,
                        base_class=base_class
                    )
                    
                    # Check for body() implementation
                    if f"task body()" in content or f"virtual task body()" in content:
                        sequence.body_implemented = True
                    
                    # Check for factory registration
                    if f"`uvm_object_utils({seq_name})" in content:
                        sequence.factory_registered = True
                    
                    self.hierarchy.sequences[seq_name] = sequence
        
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
    
    def _classify_component_type(self, name: str, type_str: str) -> UVMComponentType:
        """Classify UVM component type from name and type string"""
        name_lower = name.lower()
        type_lower = type_str.lower()
        
        if "test" in name_lower or "test" in type_lower:
            return UVMComponentType.TEST
        elif "env" in name_lower or "env" in type_lower:
            return UVMComponentType.ENV
        elif "agent" in name_lower or "agent" in type_lower:
            return UVMComponentType.AGENT
        elif "sequencer" in name_lower or "sequencer" in type_lower:
            return UVMComponentType.SEQUENCER
        elif "driver" in name_lower or "driver" in type_lower:
            return UVMComponentType.DRIVER
        elif "monitor" in name_lower or "monitor" in type_lower:
            return UVMComponentType.MONITOR
        elif "scoreboard" in name_lower or "scoreboard" in type_lower:
            return UVMComponentType.SCOREBOARD
        elif "subscriber" in name_lower or "subscriber" in type_lower:
            return UVMComponentType.SUBSCRIBER
        else:
            return UVMComponentType.COMPONENT


# =============================================================================
# UVM CONFORMANCE SCORER
# =============================================================================

@dataclass
class UVMConformanceScoringConfig:
    """Configuration for UVM conformance scoring"""
    weight: float = 0.10  # Default Tier 2 weight
    min_hierarchy_depth: int = 3  # Minimum expected depth
    required_phases: Set[UVMPhase] = field(default_factory=lambda: {
        UVMPhase.BUILD,
        UVMPhase.CONNECT,
        UVMPhase.RUN
    })
    required_components: Set[UVMComponentType] = field(default_factory=lambda: {
        UVMComponentType.TEST,
        UVMComponentType.ENV,
        UVMComponentType.AGENT
    })


class UVMConformanceScorer:
    """
    Score UVM conformance
    
    Evaluates:
    - Component hierarchy structure
    - Sequence library usage
    - Phase implementation
    - Configuration usage
    - Factory registration
    """
    
    def __init__(self, config: Optional[UVMConformanceScoringConfig] = None):
        """
        Initialize UVM conformance scorer
        
        Args:
            config: Scoring configuration
        """
        self.config = config or UVMConformanceScoringConfig()
        self.analyzer = UVMAnalyzer()
        self.hierarchy: Optional[UVMHierarchyData] = None
    
    def score(
        self,
        log_path: Optional[Path] = None,
        source_dir: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate UVM conformance component score
        
        Args:
            log_path: Path to simulation log
            source_dir: Path to source directory (fallback)
        
        Returns:
            ComponentScore for UVM conformance
        
        Raises:
            ValueError: If neither log nor source provided
        """
        logger.info("Scoring UVM conformance")
        
        # Analyze UVM structure
        if log_path:
            self.hierarchy = self.analyzer.analyze_log(log_path)
        elif source_dir:
            self.hierarchy = self.analyzer.analyze_source(source_dir)
        else:
            raise ValueError("Either log_path or source_dir required")
        
        # Calculate sub-scores
        hierarchy_score = self._score_hierarchy()
        sequence_score = self._score_sequences()
        phase_score = self._score_phases()
        config_score = self._score_configuration()
        
        # Weighted combination
        score_value = (
            hierarchy_score * 0.30 +
            sequence_score * 0.25 +
            phase_score * 0.25 +
            config_score * 0.20
        )
        
        # Validate thresholds
        threshold_met = self._check_thresholds()
        
        # Generate metrics
        metrics = self._create_metrics()
        raw_metrics = self._get_raw_metrics(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        # Generate details
        details = self._generate_details(metrics)
        
        # Create component score
        component_score = ComponentScore(
            component_type=ComponentType.UVM_CONFORMANCE,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=0.70,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"UVM conformance score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _score_hierarchy(self) -> float:
        """Score component hierarchy structure"""
        if not self.hierarchy or not self.hierarchy.components:
            return 0.0
        
        score = 0.0
        
        # Has test component
        if self.hierarchy.top_test:
            score += 0.25
        
        # Has minimum depth
        if self.hierarchy.max_depth >= self.config.min_hierarchy_depth:
            score += 0.25
        
        # Has required component types
        found_types = {comp.type for comp in self.hierarchy.components.values()}
        required_found = len(self.config.required_components & found_types)
        score += (required_found / len(self.config.required_components)) * 0.50
        
        return min(1.0, score)
    
    def _score_sequences(self) -> float:
        """Score sequence library usage"""
        if not self.hierarchy or not self.hierarchy.sequences:
            return 0.5  # Neutral if no sequences found
        
        score = 0.0
        
        # Has sequences
        if self.hierarchy.sequences:
            score += 0.40
        
        # Body implemented
        body_impl = sum(1 for s in self.hierarchy.sequences.values() if s.body_implemented)
        if self.hierarchy.sequences:
            score += (body_impl / len(self.hierarchy.sequences)) * 0.30
        
        # Factory registered
        factory_reg = sum(1 for s in self.hierarchy.sequences.values() if s.factory_registered)
        if self.hierarchy.sequences:
            score += (factory_reg / len(self.hierarchy.sequences)) * 0.30
        
        return min(1.0, score)
    
    def _score_phases(self) -> float:
        """Score UVM phase usage"""
        if not self.hierarchy or not self.hierarchy.components:
            return 0.0
        
        # Check if required phases are used
        all_phases_used = set()
        for comp in self.hierarchy.components.values():
            all_phases_used.update(comp.phases_used)
        
        required_found = len(self.config.required_phases & all_phases_used)
        score = required_found / len(self.config.required_phases)
        
        return min(1.0, score)
    
    def _score_configuration(self) -> float:
        """Score configuration object usage"""
        if not self.hierarchy or not self.hierarchy.components:
            return 0.5  # Neutral
        
        # Check for factory registration (indicates good UVM practices)
        factory_reg = sum(1 for c in self.hierarchy.components.values() if c.factory_registered)
        
        if self.hierarchy.components:
            score = factory_reg / len(self.hierarchy.components)
        else:
            score = 0.5
        
        return min(1.0, score)
    
    def _check_thresholds(self) -> bool:
        """Check if UVM conformance meets thresholds"""
        if not self.hierarchy:
            return False
        
        # Must have minimum hierarchy depth
        if self.hierarchy.max_depth < self.config.min_hierarchy_depth:
            return False
        
        # Must have test component
        if not self.hierarchy.top_test:
            return False
        
        return True
    
    def _create_metrics(self) -> UVMConformanceMetrics:
        """Create UVM conformance metrics"""
        if not self.hierarchy:
            return UVMConformanceMetrics(
                uvm_version="unknown",
                component_hierarchy=0.0,
                sequence_usage=0.0,
                configuration_usage=0.0,
                phase_usage=0.0,
                overall_conformance=0.0
            )
        
        return UVMConformanceMetrics(
            uvm_version="1.2",  # Assume UVM 1.2
            component_hierarchy=self._score_hierarchy(),
            sequence_usage=self._score_sequences(),
            configuration_usage=self._score_configuration(),
            phase_usage=self._score_phases(),
            overall_conformance=(
                self._score_hierarchy() * 0.30 +
                self._score_sequences() * 0.25 +
                self._score_phases() * 0.25 +
                self._score_configuration() * 0.20
            )
        )
    
    def _get_raw_metrics(self, metrics: UVMConformanceMetrics) -> Dict[str, Any]:
        """Get raw UVM metrics"""
        if not self.hierarchy:
            return {}
        
        return {
            "uvm_version": metrics.uvm_version,
            "component_hierarchy": metrics.component_hierarchy,
            "sequence_usage": metrics.sequence_usage,
            "configuration_usage": metrics.configuration_usage,
            "phase_usage": metrics.phase_usage,
            "overall_conformance": metrics.overall_conformance,
            "total_components": len(self.hierarchy.components),
            "total_sequences": len(self.hierarchy.sequences),
            "hierarchy_depth": self.hierarchy.max_depth,
        }
    
    def _generate_details(self, metrics: UVMConformanceMetrics) -> str:
        """Generate human-readable details"""
        if not self.hierarchy:
            return "UVM conformance metrics not available"
        
        details = (
            f"UVM Conformance: {metrics.overall_conformance * 100:.2f}%\n"
            f"  Hierarchy:     {metrics.component_hierarchy * 100:.2f}%\n"
            f"  Sequences:     {metrics.sequence_usage * 100:.2f}%\n"
            f"  Phases:        {metrics.phase_usage * 100:.2f}%\n"
            f"  Configuration: {metrics.configuration_usage * 100:.2f}%\n"
            f"\n"
            f"  Components: {len(self.hierarchy.components)}\n"
            f"  Sequences:  {len(self.hierarchy.sequences)}\n"
            f"  Depth:      {self.hierarchy.max_depth}"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving UVM conformance"""
        if not self.hierarchy:
            return []
        
        recommendations = []
        
        # Hierarchy recommendations
        if self.hierarchy.max_depth < self.config.min_hierarchy_depth:
            recommendations.append(
                f"Increase component hierarchy depth to at least {self.config.min_hierarchy_depth} levels. "
                f"Current depth: {self.hierarchy.max_depth}. Add proper env/agent structure."
            )
        
        # Sequence recommendations
        if not self.hierarchy.sequences:
            recommendations.append(
                "No UVM sequences found. Implement sequence library for stimulus generation."
            )
        
        # Phase recommendations
        all_phases = set()
        for comp in self.hierarchy.components.values():
            all_phases.update(comp.phases_used)
        
        missing_phases = self.config.required_phases - all_phases
        if missing_phases:
            phase_names = [p.value for p in missing_phases]
            recommendations.append(
                f"Implement missing UVM phases: {', '.join(phase_names)}. "
                f"Use standard UVM phase execution model."
            )
        
        # Factory recommendations
        non_registered = sum(
            1 for c in self.hierarchy.components.values()
            if not c.factory_registered
        )
        if non_registered > len(self.hierarchy.components) * 0.5:
            recommendations.append(
                f"{non_registered} component(s) not factory registered. "
                f"Use `uvm_component_utils macros for proper factory registration."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """Generate actionable improvements for UVM conformance"""
        if not self.hierarchy:
            return []
        
        improvements = []
        metrics = self._create_metrics()
        
        # Hierarchy improvement
        if metrics.component_hierarchy < 0.80:
            impact = (0.80 - metrics.component_hierarchy) * 0.30 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.UVM_CONFORMANCE,
                priority="high" if metrics.component_hierarchy < 0.50 else "medium",
                current_value=metrics.component_hierarchy * 100,
                target_value=80.0,
                impact=impact,
                actions=[
                    "Implement proper UVM component hierarchy (test → env → agent)",
                    "Use standard UVM component types (driver, monitor, sequencer)",
                    "Ensure minimum 3-level hierarchy depth",
                    "Follow UVM naming conventions",
                ]
            ))
        
        # Phase usage improvement
        if metrics.phase_usage < 0.80:
            impact = (0.80 - metrics.phase_usage) * 0.25 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.UVM_CONFORMANCE,
                priority="medium",
                current_value=metrics.phase_usage * 100,
                target_value=80.0,
                impact=impact,
                actions=[
                    "Implement build_phase for component construction",
                    "Implement connect_phase for port connections",
                    "Use run_phase for test execution",
                    "Follow standard UVM phase execution flow",
                ]
            ))
        
        improvements.sort(key=lambda x: x.impact, reverse=True)
        return improvements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_uvm_conformance(
    log_path: Optional[Path] = None,
    source_dir: Optional[Path] = None,
    weight: float = 0.10
) -> ComponentScore:
    """
    Convenience function to score UVM conformance
    
    Args:
        log_path: Path to simulation log
        source_dir: Path to source directory
        weight: Weight for this component
    
    Returns:
        ComponentScore for UVM conformance
    """
    config = UVMConformanceScoringConfig(weight=weight)
    scorer = UVMConformanceScorer(config=config)
    return scorer.score(log_path, source_dir)
