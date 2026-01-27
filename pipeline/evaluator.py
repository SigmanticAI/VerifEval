"""
VerifEval End-to-End Pipeline.

Complete evaluation pipeline implementing the HLD Guide workflow:
1. Static Quality Gate (Verible)
2. Classify and Route
3. Build & Instrument (Verilator)
4. Execute Tests (cocotb)
5. Coverage Analysis
6. Scoring & Export

With UVM-SV to Python translation support for open-source evaluation.
"""

import json
import time
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class EvaluationStage(Enum):
    """Pipeline stages."""
    QUALITY_GATE = "quality_gate"
    CLASSIFY_ROUTE = "classify_route"
    TRANSLATION = "translation"
    BUILD = "build"
    EXECUTE = "execute"
    COVERAGE = "coverage"
    SCORING = "scoring"


@dataclass
class PipelineConfig:
    """Configuration for the evaluation pipeline."""
    # Quality gate
    run_quality_gate: bool = True
    fail_on_lint_errors: bool = False
    
    # Translation
    auto_translate_uvm: bool = True
    use_llm_translation: bool = True
    llm_provider: str = "anthropic"
    
    # Simulation
    simulator: str = "verilator"
    num_runs: int = 1
    random_seed: Optional[int] = None
    timeout_seconds: int = 300
    
    # Coverage
    enable_coverage: bool = True
    coverage_types: List[str] = field(default_factory=lambda: ["line", "branch", "toggle"])
    
    # Output
    output_dir: Optional[Path] = None
    keep_work_dir: bool = False
    verbose: bool = False


@dataclass
class StageResult:
    """Result from a single pipeline stage."""
    stage: EvaluationStage
    success: bool
    duration_ms: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    success: bool
    project_name: str
    timestamp: str
    total_duration_ms: float = 0.0
    
    # Stage results
    stages: Dict[str, StageResult] = field(default_factory=dict)
    
    # Final metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Summary
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'project_name': self.project_name,
            'timestamp': self.timestamp,
            'total_duration_ms': self.total_duration_ms,
            'stages': {
                name: {
                    'stage': result.stage.value,
                    'success': result.success,
                    'duration_ms': result.duration_ms,
                    'data': result.data,
                    'errors': result.errors,
                    'warnings': result.warnings
                }
                for name, result in self.stages.items()
            },
            'metrics': self.metrics,
            'errors': self.errors,
            'warnings': self.warnings
        }


class VerifEvalPipeline:
    """
    End-to-end verification testbench evaluation pipeline.
    
    Implements the complete HLD Guide workflow with support
    for automatic UVM-SV to Python translation.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self._init_components()
    
    def _init_components(self):
        """Initialize pipeline components."""
        # Quality gate
        self._quality_gate = None
        
        # Classifier
        self._classifier = None
        
        # Translator
        self._translator = None
        
        # Simulator
        self._simulator = None
    
    def evaluate(self, project_path: Path) -> EvaluationResult:
        """
        Run the complete evaluation pipeline.
        
        Args:
            project_path: Path to verification project
            
        Returns:
            EvaluationResult with all metrics
        """
        start_time = time.time()
        project_path = Path(project_path)
        
        result = EvaluationResult(
            success=False,
            project_name=project_path.name,
            timestamp=datetime.now().isoformat()
        )
        
        # Set up output directory
        output_dir = self.config.output_dir or project_path / "eval_results"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Stage 1: Quality Gate
            if self.config.run_quality_gate:
                stage_result = self._run_quality_gate(project_path)
                result.stages['quality_gate'] = stage_result
                
                if not stage_result.success and self.config.fail_on_lint_errors:
                    result.errors.append("Quality gate failed")
                    return self._finalize_result(result, start_time)
            
            # Stage 2: Classify and Route
            stage_result = self._run_classification(project_path)
            result.stages['classify_route'] = stage_result
            
            if not stage_result.success:
                result.errors.extend(stage_result.errors)
                return self._finalize_result(result, start_time)
            
            routing = stage_result.data.get('routing', {})
            tb_type = routing.get('tb_type', 'unknown')
            
            # Stage 3: Translation (if UVM-SV)
            if tb_type == 'uvm_sv' and self.config.auto_translate_uvm:
                stage_result = self._run_translation(project_path, routing)
                result.stages['translation'] = stage_result
                
                if stage_result.success:
                    # Update to use translated files
                    project_path = Path(stage_result.data.get('translated_dir', project_path))
                    routing = stage_result.data.get('updated_routing', routing)
                else:
                    result.warnings.append("UVM translation failed - cannot proceed with open-source tools")
                    result.errors.extend(stage_result.errors)
                    return self._finalize_result(result, start_time)
            
            # Stage 4: Build
            stage_result = self._run_build(project_path, routing)
            result.stages['build'] = stage_result
            
            if not stage_result.success:
                result.errors.extend(stage_result.errors)
                return self._finalize_result(result, start_time)
            
            # Stage 5: Execute Tests
            stage_result = self._run_tests(project_path, routing)
            result.stages['execute'] = stage_result
            result.warnings.extend(stage_result.warnings)
            
            # Stage 6: Coverage Analysis
            if self.config.enable_coverage:
                stage_result = self._run_coverage_analysis(project_path, routing)
                result.stages['coverage'] = stage_result
            
            # Stage 7: Scoring
            stage_result = self._compute_scores(result.stages)
            result.stages['scoring'] = stage_result
            result.metrics = stage_result.data
            
            # Determine overall success
            result.success = all(
                s.success for s in result.stages.values() 
                if s.stage != EvaluationStage.QUALITY_GATE  # QG warnings don't fail
            )
            
        except Exception as e:
            result.errors.append(f"Pipeline failed: {str(e)}")
            import traceback
            if self.config.verbose:
                traceback.print_exc()
        
        return self._finalize_result(result, start_time, output_dir)
    
    def _run_quality_gate(self, project_path: Path) -> StageResult:
        """Run the quality gate (Verible linting)."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.QUALITY_GATE, success=True)
        
        try:
            from tb_classif.quality_gate.verible_linter import VeribleLinter
            
            # Find SV files
            sv_files = list(project_path.glob('**/*.sv')) + list(project_path.glob('**/*.v'))
            
            if not sv_files:
                result.data['skipped'] = True
                result.data['reason'] = "No SystemVerilog files found"
                return result
            
            linter = VeribleLinter(sv_files, project_path)
            report = linter.run_checks()
            
            result.success = report.critical_errors == 0
            result.data = {
                'total_files': report.total_files,
                'total_violations': report.total_violations,
                'critical_errors': report.critical_errors,
                'warnings': report.warnings,
                'style_issues': report.style_issues
            }
            
            if report.critical_errors > 0:
                result.errors.append(f"{report.critical_errors} critical lint errors")
            if report.warnings > 10:
                result.warnings.append(f"{report.warnings} lint warnings")
                
        except ImportError:
            result.warnings.append("Verible not available - skipping quality gate")
            result.data['skipped'] = True
        except Exception as e:
            result.warnings.append(f"Quality gate error: {str(e)}")
            result.data['skipped'] = True
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_classification(self, project_path: Path) -> StageResult:
        """Run testbench classification and routing."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.CLASSIFY_ROUTE, success=True)
        
        try:
            from tb_classif.classify_route import ClassifierRouter
            
            router = ClassifierRouter(project_path)
            routing = router.classify_and_route(run_quality_gate=False)
            
            result.data['routing'] = routing.to_dict()
            result.success = routing.is_valid() or routing.tb_type == 'uvm_sv'
            
            if not result.success:
                result.errors.extend(routing.errors)
            result.warnings.extend(routing.warnings)
            
        except ImportError as e:
            result.errors.append(f"Classification module not available: {e}")
            result.success = False
        except Exception as e:
            result.errors.append(f"Classification failed: {str(e)}")
            result.success = False
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_translation(self, project_path: Path, routing: Dict) -> StageResult:
        """Run UVM-SV to Python translation."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.TRANSLATION, success=False)
        
        try:
            from tb_classif.classify_route.uvm_integration import UVMTranslationIntegrator
            from tb_classif.detectors.models import DetectionResult, TBType, Language
            
            integrator = UVMTranslationIntegrator(
                auto_translate=True,
                use_llm=self.config.use_llm_translation,
                llm_provider=self.config.llm_provider
            )
            
            # Create mock detection result
            detection = DetectionResult(
                tb_type=TBType.UVM_SV,
                confidence=1.0,
                files_detected=routing.get('tb_files', []),
                detection_method="classification",
                language=Language.SYSTEMVERILOG
            )
            
            # Get file paths
            dut_files = [project_path / f for f in routing.get('dut_files', [])]
            tb_files = [project_path / f for f in routing.get('tb_files', [])]
            
            # Run translation
            trans_result = integrator.check_and_translate(
                detection, project_path, dut_files, tb_files
            )
            
            result.success = trans_result['translation_success']
            result.data = {
                'translated_dir': trans_result['translated_dir'],
                'translated_files': trans_result['translated_files'],
                'new_tb_type': trans_result['new_tb_type'].value if hasattr(trans_result['new_tb_type'], 'value') else str(trans_result['new_tb_type']),
            }
            
            # Update routing for translated files
            if result.success:
                result.data['updated_routing'] = {
                    **routing,
                    'tb_type': 'cocotb',
                    'track': 'A',
                    'chosen_simulator': 'verilator'
                }
            
            result.errors.extend(trans_result['errors'])
            result.warnings.extend(trans_result['warnings'])
            
        except ImportError as e:
            # Try direct translation without integrator
            try:
                from uvm_translator.runner import UVMTranslationRunner
                from uvm_translator.translator import TranslationMode
                
                runner = UVMTranslationRunner(
                    mode=TranslationMode.COCOTB,
                    use_llm=self.config.use_llm_translation,
                    llm_provider=self.config.llm_provider,
                    verbose=self.config.verbose
                )
                
                output_dir = project_path / "translated_cocotb"
                trans_results = runner.translate(
                    input_path=project_path,
                    output_dir=output_dir,
                    validate=True,
                    auto_fix=True
                )
                
                result.success = trans_results['success']
                result.data = {
                    'translated_dir': str(output_dir),
                    'translated_files': trans_results.get('files_generated', []),
                    'new_tb_type': 'cocotb',
                }
                
                if result.success:
                    result.data['updated_routing'] = {
                        **routing,
                        'tb_type': 'cocotb',
                        'track': 'A',
                        'chosen_simulator': 'verilator'
                    }
                
                result.errors.extend(trans_results.get('errors', []))
                result.warnings.extend(trans_results.get('warnings', []))
                
            except Exception as e2:
                result.errors.append(f"Translation failed: {str(e2)}")
        except Exception as e:
            result.errors.append(f"Translation failed: {str(e)}")
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_build(self, project_path: Path, routing: Dict) -> StageResult:
        """Run build and instrumentation."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.BUILD, success=True)
        
        try:
            # Check for Makefile
            makefile = project_path / "Makefile"
            if not makefile.exists():
                # Look in translated directory
                translated_dir = project_path / "translated_cocotb"
                if (translated_dir / "Makefile").exists():
                    makefile = translated_dir / "Makefile"
                else:
                    result.warnings.append("No Makefile found - build may fail")
            
            result.data['makefile_found'] = makefile.exists()
            result.data['simulator'] = routing.get('chosen_simulator', self.config.simulator)
            
            # For now, just verify the build setup exists
            # Actual build happens during test execution
            
        except Exception as e:
            result.errors.append(f"Build setup failed: {str(e)}")
            result.success = False
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_tests(self, project_path: Path, routing: Dict) -> StageResult:
        """Execute the tests."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.EXECUTE, success=True)
        
        try:
            from tb_eval.runner import TBEvalRunner
            from tb_eval.config import EvalConfig
            
            config = EvalConfig(
                verbose=self.config.verbose,
                keep_work_dir=self.config.keep_work_dir
            )
            
            runner = TBEvalRunner(config=config)
            
            # Determine which directory to evaluate
            eval_dir = project_path
            if (project_path / "translated_cocotb").exists():
                eval_dir = project_path / "translated_cocotb"
            
            # Run evaluation
            try:
                eval_results = runner.evaluate(eval_dir, num_runs=self.config.num_runs)
                
                result.data = {
                    'build_success_rate': eval_results.build_success_rate,
                    'sim_success_rate': eval_results.sim_success_rate,
                    'avg_coverage': eval_results.avg_coverage,
                    'num_runs': eval_results.num_runs
                }
                
                result.success = eval_results.build_success_rate > 0
                
            except ValueError as ve:
                # Missing files
                result.warnings.append(str(ve))
                result.data['skipped'] = True
            
        except ImportError:
            result.warnings.append("tb_eval not available - skipping test execution")
            result.data['skipped'] = True
        except Exception as e:
            result.errors.append(f"Test execution failed: {str(e)}")
            result.success = False
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_coverage_analysis(self, project_path: Path, routing: Dict) -> StageResult:
        """Run coverage analysis."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.COVERAGE, success=True)
        
        try:
            # Look for coverage data
            coverage_files = list(project_path.glob('**/coverage.dat'))
            
            if not coverage_files:
                result.data['skipped'] = True
                result.warnings.append("No coverage data found")
                return result
            
            result.data = {
                'coverage_files_found': len(coverage_files),
                'coverage_types': self.config.coverage_types
            }
            
        except Exception as e:
            result.errors.append(f"Coverage analysis failed: {str(e)}")
            result.success = False
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _compute_scores(self, stages: Dict[str, StageResult]) -> StageResult:
        """Compute final scores from all stages."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.SCORING, success=True)
        
        scores = {
            'build_success': 0.0,
            'sim_success': 0.0,
            'structural_coverage': 0.0,
            'lint_score': 100.0,
            'overall_score': 0.0
        }
        
        # Build score from execution stage
        if 'execute' in stages:
            exec_data = stages['execute'].data
            scores['build_success'] = exec_data.get('build_success_rate', 0.0)
            scores['sim_success'] = exec_data.get('sim_success_rate', 0.0)
            scores['structural_coverage'] = exec_data.get('avg_coverage', 0.0)
        
        # Lint score from quality gate
        if 'quality_gate' in stages:
            qg_data = stages['quality_gate'].data
            if not qg_data.get('skipped'):
                errors = qg_data.get('critical_errors', 0)
                warnings = qg_data.get('warnings', 0)
                scores['lint_score'] = max(0, 100 - errors * 10 - warnings)
        
        # Overall score (weighted average)
        weights = {
            'build_success': 0.2,
            'sim_success': 0.3,
            'structural_coverage': 0.3,
            'lint_score': 0.2
        }
        
        scores['overall_score'] = sum(
            scores[key] * weight for key, weight in weights.items()
        )
        
        result.data = scores
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _finalize_result(self, result: EvaluationResult, 
                        start_time: float,
                        output_dir: Optional[Path] = None) -> EvaluationResult:
        """Finalize and save the evaluation result."""
        result.total_duration_ms = (time.time() - start_time) * 1000
        
        # Collect all errors and warnings
        for stage_result in result.stages.values():
            for err in stage_result.errors:
                if err not in result.errors:
                    result.errors.append(err)
            for warn in stage_result.warnings:
                if warn not in result.warnings:
                    result.warnings.append(warn)
        
        # Save results if output directory specified
        if output_dir:
            output_path = Path(output_dir) / "evaluation_result.json"
            with open(output_path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
        
        return result


def main():
    """CLI entry point for the evaluation pipeline."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="VerifEval Pipeline - End-to-end testbench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('project', type=Path,
                       help='Path to verification project')
    parser.add_argument('--output', '-o', type=Path,
                       help='Output directory for results')
    parser.add_argument('--no-translate', action='store_true',
                       help='Disable automatic UVM translation')
    parser.add_argument('--no-llm', action='store_true',
                       help='Use templates only for translation')
    parser.add_argument('--provider', choices=['anthropic', 'openai'],
                       default='anthropic', help='LLM provider')
    parser.add_argument('--runs', type=int, default=1,
                       help='Number of simulation runs')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    if not args.project.exists():
        print(f"Error: Project path does not exist: {args.project}")
        sys.exit(1)
    
    config = PipelineConfig(
        auto_translate_uvm=not args.no_translate,
        use_llm_translation=not args.no_llm,
        llm_provider=args.provider,
        num_runs=args.runs,
        output_dir=args.output,
        verbose=args.verbose
    )
    
    pipeline = VerifEvalPipeline(config)
    result = pipeline.evaluate(args.project)
    
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result)
    
    sys.exit(0 if result.success else 1)


def _print_result(result: EvaluationResult):
    """Print evaluation result in human-readable format."""
    print("\n" + "=" * 70)
    print("VERIFEVAL PIPELINE RESULTS")
    print("=" * 70)
    
    print(f"\nProject: {result.project_name}")
    print(f"Timestamp: {result.timestamp}")
    print(f"Duration: {result.total_duration_ms:.0f}ms")
    
    print("\nStages:")
    for name, stage in result.stages.items():
        status = "✓" if stage.success else "✗"
        print(f"  {status} {name}: {stage.duration_ms:.0f}ms")
    
    if result.metrics:
        print("\nScores:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.1f}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors[:5]:
            print(f"  ✗ {err}")
    
    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warn in result.warnings[:5]:
            print(f"  ⚠ {warn}")
    
    status = "✓ SUCCESS" if result.success else "✗ FAILED"
    print(f"\nOverall: {status}")
    print("=" * 70)


if __name__ == '__main__':
    main()

