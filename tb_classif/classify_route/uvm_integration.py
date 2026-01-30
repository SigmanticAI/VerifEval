"""
UVM-SV to Python Translation Integration.

Integrates the UVM translator into the classification and routing pipeline.
When UVM-SV is detected, automatically translates to Python/cocotb.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..detectors.models import (
    DetectionResult, RoutingDecision, TBType, Track, 
    Simulator, Language, QualityReport
)


class UVMTranslationIntegrator:
    """
    Integrates UVM translation into the classification pipeline.
    
    When UVM-SV testbench is detected:
    1. Offer automatic translation to Python/cocotb
    2. Run translation if requested
    3. Update routing decision to use translated files
    """
    
    def __init__(self, 
                 auto_translate: bool = True,
                 use_llm: bool = True,
                 llm_provider: str = "anthropic"):
        """
        Initialize the integration.
        
        Args:
            auto_translate: Automatically translate UVM-SV when detected
            use_llm: Use LLM for translation (False = templates only)
            llm_provider: LLM provider (anthropic or openai)
        """
        self.auto_translate = auto_translate
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self._translator = None
        
    def _get_translator(self):
        """Lazy load the translator to avoid import issues."""
        if self._translator is None:
            try:
                from uvm_translator import UVMTranslator, TranslationMode
                self._translator = UVMTranslator(
                    mode=TranslationMode.COCOTB,
                    llm_provider=self.llm_provider
                )
            except ImportError:
                self._translator = None
        return self._translator
    
    def check_and_translate(self,
                           detection_result: DetectionResult,
                           project_dir: Path,
                           dut_files: List[Path],
                           tb_files: List[Path]) -> Dict[str, Any]:
        """
        Check if UVM-SV detected and translate if needed.
        
        Args:
            detection_result: Result from TB type detection
            project_dir: Project root directory
            dut_files: List of DUT file paths
            tb_files: List of testbench file paths
            
        Returns:
            Dictionary with translation results and updated routing info
        """
        result = {
            'translation_performed': False,
            'translation_success': False,
            'translated_dir': None,
            'translated_files': [],
            'new_tb_type': detection_result.tb_type,
            'new_track': self._get_track(detection_result.tb_type),
            'new_simulator': self._get_simulator(detection_result.tb_type),
            'errors': [],
            'warnings': [],
            'notes': []
        }
        
        # Check if UVM-SV detected
        if detection_result.tb_type != TBType.UVM_SV:
            result['notes'].append("Not UVM-SV testbench - no translation needed")
            return result
        
        # UVM-SV detected
        result['notes'].append("UVM-SV testbench detected - translation required for open-source tools")
        
        if not self.auto_translate:
            result['warnings'].append(
                "UVM-SV detected but auto_translate is disabled. "
                "Enable auto_translate or translate manually."
            )
            return result
        
        # Attempt translation
        translator = self._get_translator()
        
        if translator is None:
            # Fall back to template-based translation
            result['notes'].append("Using template-based translation (uvm_translator not available)")
            return self._translate_with_templates(project_dir, dut_files, tb_files, result)
        
        try:
            # Run LLM-based translation
            output_dir = project_dir / "translated_cocotb"
            
            from uvm_translator import TranslationResult
            translation_result = translator.translate_project(project_dir, output_dir)
            
            result['translation_performed'] = True
            result['translation_success'] = translation_result.success
            result['translated_dir'] = str(output_dir)
            result['translated_files'] = [f.filename for f in translation_result.files]
            
            if translation_result.success:
                # Update TB type to cocotb
                result['new_tb_type'] = TBType.COCOTB
                result['new_track'] = Track.A
                result['new_simulator'] = Simulator.VERILATOR
                result['notes'].append("Successfully translated UVM-SV to cocotb")
            else:
                result['errors'].extend(translation_result.errors)
                
            result['warnings'].extend(translation_result.warnings)
            result['notes'].extend(translation_result.notes)
            
        except Exception as e:
            result['errors'].append(f"Translation failed: {str(e)}")
            # Fall back to templates
            return self._translate_with_templates(project_dir, dut_files, tb_files, result)
        
        return result
    
    def _translate_with_templates(self, 
                                  project_dir: Path,
                                  dut_files: List[Path],
                                  tb_files: List[Path],
                                  result: Dict[str, Any]) -> Dict[str, Any]:
        """Fall back to template-based translation."""
        try:
            from uvm_translator.runner import UVMTranslationRunner
            from uvm_translator.translator import TranslationMode
            
            runner = UVMTranslationRunner(
                mode=TranslationMode.COCOTB,
                use_llm=False,  # Templates only
                verbose=False
            )
            
            output_dir = project_dir / "translated_cocotb"
            translation_results = runner.translate(
                input_path=project_dir,
                output_dir=output_dir,
                validate=True,
                auto_fix=True
            )
            
            result['translation_performed'] = True
            result['translation_success'] = translation_results['success']
            result['translated_dir'] = str(output_dir)
            result['translated_files'] = translation_results.get('files_generated', [])
            
            if translation_results['success']:
                result['new_tb_type'] = TBType.COCOTB
                result['new_track'] = Track.A
                result['new_simulator'] = Simulator.VERILATOR
                result['notes'].append("Translated using templates (no LLM)")
            else:
                result['errors'].extend(translation_results.get('errors', []))
                
        except Exception as e:
            result['errors'].append(f"Template translation failed: {str(e)}")
            result['translation_success'] = False
        
        return result
    
    def _get_track(self, tb_type: TBType) -> Track:
        """Get execution track for TB type."""
        track_mapping = {
            TBType.COCOTB: Track.A,
            TBType.PYUVM: Track.A,
            TBType.VUNIT: Track.B,
            TBType.SYSTEMVERILOG: Track.B,
            TBType.VHDL: Track.B,
            TBType.UVM_SV: Track.C,
            TBType.UNKNOWN: Track.B
        }
        return track_mapping.get(tb_type, Track.B)
    
    def _get_simulator(self, tb_type: TBType) -> Simulator:
        """Get default simulator for TB type."""
        sim_mapping = {
            TBType.COCOTB: Simulator.VERILATOR,
            TBType.PYUVM: Simulator.VERILATOR,
            TBType.VUNIT: Simulator.VERILATOR,
            TBType.SYSTEMVERILOG: Simulator.VERILATOR,
            TBType.VHDL: Simulator.GHDL,
            TBType.UVM_SV: Simulator.COMMERCIAL_REQUIRED,
            TBType.UNKNOWN: Simulator.VERILATOR
        }
        return sim_mapping.get(tb_type, Simulator.VERILATOR)
    
    def update_routing_with_translation(self,
                                        original_routing: RoutingDecision,
                                        translation_result: Dict[str, Any]) -> RoutingDecision:
        """
        Update routing decision with translation results.
        
        Args:
            original_routing: Original routing decision
            translation_result: Result from check_and_translate
            
        Returns:
            Updated RoutingDecision
        """
        if not translation_result['translation_success']:
            # Add translation errors to routing
            original_routing.errors.extend(translation_result['errors'])
            original_routing.warnings.extend(translation_result['warnings'])
            return original_routing
        
        # Create updated routing for translated testbench
        translated_dir = Path(translation_result['translated_dir'])
        
        # Find translated test files
        translated_tb_files = list(translated_dir.glob('*.py'))
        
        # Update routing
        return RoutingDecision(
            tb_type=translation_result['new_tb_type'].value,
            track=translation_result['new_track'].value,
            entrypoint=self._find_entrypoint(translated_tb_files),
            chosen_simulator=translation_result['new_simulator'].value,
            language=Language.PYTHON.value,
            confidence=original_routing.confidence,
            detection_method="translated_from_uvm_sv",
            dut_files=original_routing.dut_files,
            tb_files=[str(f) for f in translated_tb_files],
            top_module=original_routing.top_module,
            quality_gate_passed=True,  # Translation passed
            quality_metrics=original_routing.quality_metrics,
            recommendations=[
                "✓ UVM-SV testbench was automatically translated to cocotb",
                "💡 Review translated code in: " + str(translated_dir),
                "💡 Run with: make SIM=verilator"
            ],
            warnings=translation_result['warnings'],
            errors=translation_result['errors']
        )
    
    def _find_entrypoint(self, tb_files: List[Path]) -> str:
        """Find the test entrypoint in translated files."""
        for f in tb_files:
            if 'test' in f.stem.lower():
                return str(f)
        # Default to first Python file
        if tb_files:
            return str(tb_files[0])
        return ""


def create_translation_report(translation_result: Dict[str, Any],
                             output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Create a detailed translation report.
    
    Args:
        translation_result: Result from UVMTranslationIntegrator
        output_path: Optional path to save report
        
    Returns:
        Report dictionary
    """
    report = {
        'timestamp': datetime.now().isoformat(),
        'translation_performed': translation_result['translation_performed'],
        'success': translation_result['translation_success'],
        'output_directory': translation_result['translated_dir'],
        'files_generated': translation_result['translated_files'],
        'original_tb_type': 'uvm_sv',
        'translated_tb_type': translation_result['new_tb_type'].value if hasattr(translation_result['new_tb_type'], 'value') else str(translation_result['new_tb_type']),
        'execution_track': translation_result['new_track'].value if hasattr(translation_result['new_track'], 'value') else str(translation_result['new_track']),
        'simulator': translation_result['new_simulator'].value if hasattr(translation_result['new_simulator'], 'value') else str(translation_result['new_simulator']),
        'errors': translation_result['errors'],
        'warnings': translation_result['warnings'],
        'notes': translation_result['notes'],
    }
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    return report

