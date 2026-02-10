"""
Routing decision engine - core logic for track assignment
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

from ..models import (
    DetectionResult, RoutingDecision, QualityReport,
    TBType, Track, Simulator, Language
)
from .confidence import ConfidenceScorer
from .simulator_selector import SimulatorSelector


class RoutingEngine:
    """
    Main routing decision engine
    Determines execution track and creates routing decision
    """
    
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.confidence_scorer = ConfidenceScorer()
        self.simulator_selector = SimulatorSelector()
    
    def create_routing_decision(
        self,
        detection_results: List[DetectionResult],
        dut_files: List[Path],
        tb_files: List[Path],
        quality_report: Optional[QualityReport] = None,
        top_module: Optional[str] = None,
        preferred_simulator: Optional[str] = None
    ) -> RoutingDecision:
        """
        Create routing decision from detection results
        
        Args:
            detection_results: List of TB type detection results
            dut_files: List of DUT file paths
            tb_files: List of testbench file paths
            quality_report: Optional quality gate report
            top_module: Optional top module name
            preferred_simulator: Optional simulator preference
        
        Returns:
            RoutingDecision object with all routing information
        """
        # Select best detection
        if not detection_results:
            return self._create_unknown_routing(dut_files, tb_files, quality_report)
        
        best_detection = self.confidence_scorer.select_best_detection(detection_results)
        
        # Calculate final confidence
        final_confidence = self.confidence_scorer.calculate_detection_confidence(
            detection_results, quality_report
        )
        
        # Assign track
        track = self._assign_track(best_detection.tb_type)
        
        # Select simulator
        simulator = self.simulator_selector.select_simulator(
            tb_type=best_detection.tb_type,
            language=best_detection.language,
            preferred=preferred_simulator
        )
        
        # Determine entrypoint
        entrypoint = self._determine_entrypoint(
            best_detection.tb_type,
            tb_files,
            top_module
        )
        
        # Generate recommendations and warnings
        recommendations = self._generate_recommendations(best_detection, simulator)
        warnings = self._generate_warnings(best_detection, quality_report, final_confidence)
        errors = self._generate_errors(best_detection, quality_report)
        
        # Check quality gate status
        quality_gate_passed = self._check_quality_gate(quality_report)
        
        # Create routing decision
        routing = RoutingDecision(
            tb_type=best_detection.tb_type.value,
            track=track.value,
            entrypoint=entrypoint,
            chosen_simulator=simulator.value,
            language=best_detection.language.value,
            confidence=final_confidence,
            detection_method=best_detection.detection_method,
            dut_files=[str(f.relative_to(self.root_dir)) for f in dut_files],
            tb_files=[str(f.relative_to(self.root_dir)) for f in tb_files],
            top_module=top_module,
            quality_gate_passed=quality_gate_passed,
            quality_metrics=quality_report.to_dict() if quality_report else None,
            recommendations=recommendations,
            warnings=warnings,
            errors=errors
        )
        
        return routing
    
    def _assign_track(self, tb_type: TBType) -> Track:
        """Assign execution track based on TB type"""
        track_mapping = {
            TBType.COCOTB: Track.A,
            TBType.PYUVM: Track.A,
            TBType.VUNIT: Track.B,
            TBType.SYSTEMVERILOG: Track.B,
            TBType.VHDL: Track.B,
            TBType.UVM_SV: Track.B,  # Questa -> updated for uvm compatibility
            TBType.UNKNOWN: Track.B  # Default to B with warnings
        }
        
        return track_mapping.get(tb_type, Track.B)
    
    def _determine_entrypoint(
        self,
        tb_type: TBType,
        tb_files: List[Path],
        top_module: Optional[str]
    ) -> str:
        """Determine the entrypoint file/module for execution"""
        
        if not tb_files:
            return ""
        
        # CocoTB: Look for Python test file
        if tb_type == TBType.COCOTB:
            for f in tb_files:
                if f.suffix == '.py' and ('test' in f.stem.lower()):
                    return str(f.relative_to(self.root_dir))
            # Default to first Python file
            python_files = [f for f in tb_files if f.suffix == '.py']
            if python_files:
                return str(python_files[0].relative_to(self.root_dir))
        
        # PyUVM: Look for main test file
        elif tb_type == TBType.PYUVM:
            for f in tb_files:
                if f.suffix == '.py' and any(x in f.stem.lower() for x in ['test', 'tb', 'top']):
                    return str(f.relative_to(self.root_dir))
            python_files = [f for f in tb_files if f.suffix == '.py']
            if python_files:
                return str(python_files[0].relative_to(self.root_dir))
        
        # VUnit: Look for run.py
        elif tb_type == TBType.VUNIT:
            for f in tb_files:
                if f.suffix == '.py' and 'run' in f.stem.lower():
                    return str(f.relative_to(self.root_dir))
            # Look for any Python file (runner script)
            for f in tb_files:
                if f.suffix == '.py':
                    return str(f.relative_to(self.root_dir))
        
        # HDL testbenches: Use top_module or guess from filenames
        elif tb_type in [TBType.SYSTEMVERILOG, TBType.VHDL, TBType.UVM_SV]:
            if top_module:
                return top_module
            
            # Look for file with 'top' or 'tb' in name
            for f in tb_files:
                if any(x in f.stem.lower() for x in ['top', 'tb', 'test']):
                    return str(f.relative_to(self.root_dir))
            
            # Default to first TB file
            if tb_files:
                return str(tb_files[0].relative_to(self.root_dir))
        
        # Default: first testbench file
        return str(tb_files[0].relative_to(self.root_dir))
    
    def _generate_recommendations(
        self,
        detection: DetectionResult,
        simulator: Simulator
    ) -> List[str]:
        """Generate recommendations based on detection and routing"""
        recommendations = []
        
        # UVM-SV detected
        if detection.tb_type == TBType.UVM_SV:
            if simulator == Simulator.QUESTA:
                recommendations.append(
                    "✅ UVM SystemVerilog detected. Questa simulator will be used."
                )
                recommendations.append(
                    "💡 Ensure Questa license is properly configured in .tbeval.yaml"
                )
            else:
                # ← UPDATED: Questa not configured
                recommendations.append(
                    "⚠️  UVM SystemVerilog detected but Questa not configured."
                )
            recommendations.append(
                "💡 To run UVM testbenches, configure Questa in .tbeval.yaml:"
            )
            recommendations.append(
                "   preferred_simulator: 'questa'"
            )
            recommendations.append(
                "💡 Alternative: Migrate to pyuvm for open-source compatibility: "
                "https://github.com/pyuvm/pyuvm"
            )
        
        # Low confidence detection
        if detection.confidence < 0.7:
            recommendations.append(
                "💡 Low detection confidence. Consider adding a manifest file (submission.yaml) "
                "to explicitly specify testbench type."
            )
        
        # Verilator selected but may have limitations
        if simulator == Simulator.VERILATOR:
            if detection.language == Language.VHDL:
                recommendations.append(
                    "💡 Verilator does not support VHDL. Switching to GHDL recommended."
                )
        
        return recommendations
    
    def _generate_warnings(
        self,
        detection: DetectionResult,
        quality_report: Optional[QualityReport],
        confidence: float
    ) -> List[str]:
        """Generate warnings"""
        warnings = []
        
        # Quality warnings
        if quality_report:
            if quality_report.warnings > 20:
                warnings.append(
                    f"⚠️  {quality_report.warnings} linting warnings detected. "
                    "Consider reviewing code quality."
                )
        
        # Confidence warnings
        if confidence < 0.5:
            warnings.append(
                "⚠️  Low routing confidence. Manual verification recommended."
            )
        
        # Mixed language detection
        if detection.language == Language.MIXED:
            warnings.append(
                "⚠️  Mixed language project detected. Ensure proper language separation."
            )
        
        return warnings
    
    def _generate_errors(
        self,
        detection: DetectionResult,
        quality_report: Optional[QualityReport]
    ) -> List[str]:
        """Generate blocking errors"""
        errors = []
        
        # Quality gate failures
        if quality_report and quality_report.critical_errors > 0:
            errors.append(
                f"❌ {quality_report.critical_errors} critical syntax/lint errors detected. "
                "Fix errors before proceeding."
            )
        
        # UVM-SV without Questa configured (but not a hard error anymore)
        if detection.tb_type == TBType.UVM_SV:
            # Check if Questa is configured
            # This check would happen in the orchestrator, not here
            pass  # ← REMOVED: No longer a blocking error
            
        
        return errors
    
    def _check_quality_gate(self, quality_report: Optional[QualityReport]) -> bool:
        """Check if quality gate passed"""
        if not quality_report:
            return True  # No quality gate = pass
        
        # Fail if critical errors
        if quality_report.critical_errors > 0:
            return False
        
        # Otherwise pass (warnings are advisory)
        return True
    
    def _create_unknown_routing(
        self,
        dut_files: List[Path],
        tb_files: List[Path],
        quality_report: Optional[QualityReport]
    ) -> RoutingDecision:
        """Create routing decision for unknown TB type"""
        return RoutingDecision(
            tb_type=TBType.UNKNOWN.value,
            track=Track.B.value,
            entrypoint="",
            chosen_simulator=Simulator.VERILATOR.value,
            language=Language.SYSTEMVERILOG.value,
            confidence=0.0,
            detection_method="failed",
            dut_files=[str(f.relative_to(self.root_dir)) for f in dut_files],
            tb_files=[str(f.relative_to(self.root_dir)) for f in tb_files],
            quality_gate_passed=False,
            quality_metrics=quality_report.to_dict() if quality_report else None,
            recommendations=[
                "💡 Could not detect testbench type. Please create a manifest file (submission.yaml)"
            ],
            warnings=[
                "⚠️  Unknown testbench type - cannot determine execution strategy"
            ],
            errors=[
                "❌ Testbench type detection failed. Manual intervention required."
            ]
        )


class UVMHandler:
    """Special handler for UVM testbenches"""
    
    @staticmethod
    def generate_pyuvm_migration_guide(sv_files: List[Path]) -> Dict[str, Any]:
        """Generate migration guide from UVM-SV to pyuvm"""
        return {
            "migration_guide": {
                "overview": "Migrate from SystemVerilog UVM to Python pyuvm",
                "steps": [
                    "1. Install pyuvm: pip install pyuvm",
                    "2. Convert UVM components to Python classes",
                    "3. Replace `uvm_component` extends with Python inheritance",
                    "4. Convert SystemVerilog sequences to Python async functions",
                    "5. Update configuration database calls to pyuvm ConfigDB"
                ],
                "resources": [
                    "https://github.com/pyuvm/pyuvm",
                    "https://pyuvm.github.io/pyuvm/",
                ],
                "example_conversion": {
                    "systemverilog": """
class my_test extends uvm_test;
    `uvm_component_utils(my_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        // test code
        phase.drop_objection(this);
    endtask
endclass
""",
                    "pyuvm": """
from pyuvm import *

class MyTest(uvm_test):
    def __init__(self, name, parent):
        super().__init__(name, parent)
    
    async def run_phase(self):
        self.raise_objection()
        # test code
        self.drop_objection()
"""
                },
                "automated_tools": [
                    "Manual conversion required - no automated tool available yet"
                ]
            }
        }
    
    @staticmethod
    def check_uvm_compatibility(detection: DetectionResult) -> Dict[str, Any]:
        """Check UVM compatibility with open source tools"""
        return {
            "uvm_compatibility": {
                "detected_type": "SystemVerilog UVM",
                "open_source_support": "Limited",
                "commercial_sim_required": True,
                "alternatives": [
                    {
                        "name": "pyuvm",
                        "language": "Python",
                        "compatibility": "Full open-source",
                        "effort": "Medium (manual conversion required)"
                    },
                    {
                        "name": "SVUnit",
                        "language": "SystemVerilog",
                        "compatibility": "Partial (simpler unit testing)",
                        "effort": "Low (if suitable for use case)"
                    }
                ],
                "commercial_simulators": [
                    "Cadence Xcelium",
                    "Synopsys VCS",
                    "Mentor Questa"
                ]
            }
        }
