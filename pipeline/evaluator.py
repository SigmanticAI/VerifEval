"""
VerifEval End-to-End Pipeline (Questa Version).

Complete evaluation pipeline using Siemens Questa:
1. Quality Gate (syntax checking)
2. Classify and Route
3. Build (vlog compilation)
4. Execute Tests (vsim simulation)
5. Coverage Analysis (vcover)
6. Scoring & Export
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
    
    # Questa configuration
    simulator: str = "questa"
    license_file: Optional[str] = None
    
    # Simulation
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
    
    # Legacy options (kept for compatibility but not used)
    auto_translate_uvm: bool = False
    use_llm_translation: bool = False
    llm_provider: str = "anthropic"


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
    
    Uses Siemens Questa for UVM simulation and coverage.
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
        self._simulator = None
        self._coverage_analyzer = None
        
        # Initialize Questa components if license available
        try:
            from questa.config import get_config, set_license
            from questa.simulator import QuestaSimulator
            from questa.coverage import QuestaCoverageAnalyzer
            
            # Set license if provided in config
            if self.config.license_file:
                set_license(self.config.license_file)
            
            questa_config = get_config()
            self._simulator = QuestaSimulator(questa_config)
            self._coverage_analyzer = QuestaCoverageAnalyzer(questa_config)
            
        except ImportError:
            pass  # Will handle in evaluate()
    
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
        
        # Check if project exists
        if not project_path.exists():
            result.errors.append(f"Project path does not exist: {project_path}")
            return self._finalize_result(result, start_time)
        
        # Set up output directory
        output_dir = self.config.output_dir or project_path / "eval_results"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Stage 1: Quality Gate (syntax check)
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
            
            # Stage 3: Build (vlog compilation)
            stage_result = self._run_build(project_path, routing)
            result.stages['build'] = stage_result
            
            if not stage_result.success:
                result.errors.extend(stage_result.errors)
                return self._finalize_result(result, start_time)
            
            # Stage 4: Execute Tests (vsim simulation)
            stage_result = self._run_tests(project_path, routing)
            result.stages['execute'] = stage_result
            result.warnings.extend(stage_result.warnings)
            
            # Stage 5: Coverage Analysis (vcover)
            if self.config.enable_coverage:
                stage_result = self._run_coverage_analysis(project_path, routing)
                result.stages['coverage'] = stage_result
            
            # Stage 6: Scoring
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
        """Run the quality gate (basic syntax checking)."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.QUALITY_GATE, success=True)
        
        try:
            # Find SV files
            sv_files = list(project_path.glob('**/*.sv')) + list(project_path.glob('**/*.v'))
            
            if not sv_files:
                result.data['skipped'] = True
                result.data['reason'] = "No SystemVerilog files found"
                return result
            
            # Basic syntax check using Questa vlog
            if self._simulator:
                from questa.config import get_config
                import subprocess
                
                config = get_config()
                errors = []
                warnings = []
                
                for sv_file in sv_files[:10]:  # Limit to first 10 files
                    try:
                        proc = subprocess.run(
                            [config.vlog_path, '-lint', '-sv', str(sv_file)],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            env=config.get_env()
                        )
                        
                        if '** Error' in proc.stderr:
                            errors.extend([l for l in proc.stderr.split('\n') if '** Error' in l])
                        if '** Warning' in proc.stderr:
                            warnings.extend([l for l in proc.stderr.split('\n') if '** Warning' in l])
                            
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass
                
                result.data = {
                    'total_files': len(sv_files),
                    'files_checked': min(len(sv_files), 10),
                    'critical_errors': len(errors),
                    'warnings': len(warnings),
                }
                
                result.success = len(errors) == 0
                
                if errors:
                    result.errors = errors[:5]
                if warnings:
                    result.warnings = warnings[:5]
            else:
                result.data['skipped'] = True
                result.warnings.append("Questa not available - skipping quality gate")
                
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
            import re
            
            # Find all files
            sv_files = list(project_path.glob('**/*.sv')) + list(project_path.glob('**/*.v'))
            
            # Classify by looking at file contents
            dut_files = []
            tb_files = []
            assertion_files = []
            
            tb_type = 'unknown'
            
            for f in sv_files:
                try:
                    content = f.read_text(errors='ignore')
                    
                    # Check for UVM
                    if 'uvm_pkg' in content or 'extends uvm_' in content:
                        tb_files.append(str(f.relative_to(project_path)))
                        tb_type = 'uvm_sv'
                    # Check for assertions
                    elif 'assert property' in content or 'assert ' in content:
                        assertion_files.append(str(f.relative_to(project_path)))
                    # Check for testbench
                    elif 'tb_' in f.name.lower() or 'test' in f.name.lower():
                        tb_files.append(str(f.relative_to(project_path)))
                    # Otherwise it's likely DUT
                    else:
                        dut_files.append(str(f.relative_to(project_path)))
                        
                except Exception:
                    pass
            
            # If we have UVM files, assume UVM type
            if tb_type == 'unknown' and tb_files:
                tb_type = 'uvm_sv'
            
            result.data['routing'] = {
                'tb_type': tb_type,
                'dut_files': dut_files,
                'tb_files': tb_files,
                'assertion_files': assertion_files,
                'chosen_simulator': 'questa',
            }
            
            result.success = len(sv_files) > 0
            
            if not sv_files:
                result.errors.append("No SystemVerilog files found")
            
        except Exception as e:
            result.errors.append(f"Classification failed: {str(e)}")
            result.success = False
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_build(self, project_path: Path, routing: Dict) -> StageResult:
        """Run build using Questa vlog."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.BUILD, success=False)
        
        try:
            if not self._simulator:
                result.errors.append("Questa simulator not available")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            # Get all source files
            dut_files = routing.get('dut_files', [])
            tb_files = routing.get('tb_files', [])
            all_files = [project_path / f for f in dut_files + tb_files]
            
            if not all_files:
                # Fallback: find all SV files
                all_files = list(project_path.glob('**/*.sv')) + list(project_path.glob('**/*.v'))
            
            if not all_files:
                result.errors.append("No source files found")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            # Create library and compile
            work_dir = project_path / "work"
            if self._simulator.create_library(work_dir):
                success, errors, warnings = self._simulator.compile(
                    source_files=all_files,
                    work_dir=work_dir,
                    enable_coverage=self.config.enable_coverage
                )
                
                result.success = success
                result.errors = errors[:5] if errors else []
                result.warnings = warnings[:5] if warnings else []
                result.data = {
                    'files_compiled': len(all_files),
                    'work_dir': str(work_dir),
                }
            else:
                result.errors.append("Failed to create work library")
            
        except Exception as e:
            result.errors.append(f"Build failed: {str(e)}")
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_tests(self, project_path: Path, routing: Dict) -> StageResult:
        """Execute tests using Questa vsim."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.EXECUTE, success=False)
        
        try:
            if not self._simulator:
                result.errors.append("Questa simulator not available")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            work_dir = project_path / "work"
            
            # Find top module (typically tb_top or similar)
            top_module = None
            tb_files = routing.get('tb_files', [])
            
            for f in tb_files:
                path = project_path / f
                if path.exists():
                    import re
                    content = path.read_text(errors='ignore')
                    match = re.search(r'module\s+(\w+)', content)
                    if match:
                        name = match.group(1)
                        if 'tb_top' in name.lower() or 'top' in name.lower():
                            top_module = name
                            break
            
            if not top_module:
                top_module = "tb_top"  # Default
            
            # Get UVM tests from verification plan if available
            uvm_tests = ['base_test']
            verif_plan = project_path / "verification_plan.json"
            if verif_plan.exists():
                try:
                    with open(verif_plan) as f:
                        plan = json.load(f)
                        if 'tests' in plan:
                            uvm_tests = [t.get('name', 'base_test') for t in plan['tests'][:3]]
                except Exception:
                    pass
            
            # Run simulation
            coverage_db = project_path / "coverage.ucdb"
            
            sim_result = self._simulator.simulate(
                top_module=top_module,
                work_dir=work_dir,
                uvm_test=uvm_tests[0],
                coverage_db=coverage_db,
                seed=self.config.random_seed
            )
            
            result.success = sim_result.simulation_success
            result.data = {
                'build_success_rate': 100.0 if sim_result.compile_success else 0.0,
                'sim_success_rate': 100.0 if sim_result.simulation_success else 0.0,
                'test_passed': sim_result.test_passed,
                'avg_coverage': sim_result.coverage_percent,
                'uvm_errors': sim_result.test_errors,
                'uvm_warnings': sim_result.test_warnings,
            }
            
            result.errors = sim_result.simulation_errors[:5]
            result.warnings = sim_result.simulation_warnings[:5]
            
        except Exception as e:
            result.errors.append(f"Test execution failed: {str(e)}")
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _run_coverage_analysis(self, project_path: Path, routing: Dict) -> StageResult:
        """Run coverage analysis using Questa vcover."""
        start = time.time()
        result = StageResult(stage=EvaluationStage.COVERAGE, success=True)
        
        try:
            if not self._coverage_analyzer:
                result.data['skipped'] = True
                result.warnings.append("Coverage analyzer not available")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            # Look for UCDB files
            ucdb_files = list(project_path.glob('**/*.ucdb'))
            
            if not ucdb_files:
                result.data['skipped'] = True
                result.warnings.append("No coverage data found")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            # Analyze coverage
            cov_result = self._coverage_analyzer.analyze(ucdb_files[0])
            
            result.data = {
                'line_coverage': cov_result.line_coverage,
                'branch_coverage': cov_result.branch_coverage,
                'toggle_coverage': cov_result.toggle_coverage,
                'functional_coverage': cov_result.functional_coverage,
                'total_coverage': cov_result.total_coverage,
            }
            
            result.errors.extend(cov_result.errors)
            
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
        
        # Coverage from coverage stage
        if 'coverage' in stages:
            cov_data = stages['coverage'].data
            if not cov_data.get('skipped'):
                scores['structural_coverage'] = cov_data.get('total_coverage', 0.0)
        
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
        description="VerifEval Pipeline - End-to-end testbench evaluation (Questa)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('project', type=Path,
                       help='Path to verification project')
    parser.add_argument('--output', '-o', type=Path,
                       help='Output directory for results')
    parser.add_argument('--license', type=str,
                       help='Questa license server (port@server)')
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
        license_file=args.license,
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
    print("VERIFEVAL PIPELINE RESULTS (Questa)")
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
