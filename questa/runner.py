"""
Questa Evaluation Runner - Main orchestrator for Questa-based evaluations.

This module provides the top-level interface for running UVM testbench simulations
and SVA formal verification using Questa One tools.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .config import QuestaConfig, WORK_DIR
from .simulator import QuestaSimulator, QuestaSimulationResult
from .formal import QuestaFormalChecker, QuestaFormalResult
from .coverage import QuestaCoverageMetrics


@dataclass
class QuestaEvalResult:
    """Result of a complete Questa evaluation run."""
    project_name: str
    success: bool = False
    
    # Timestamps
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    
    # Simulation results (UVM)
    simulation_results: List[QuestaSimulationResult] = field(default_factory=list)
    
    # Formal results (SVA)
    formal_results: List[QuestaFormalResult] = field(default_factory=list)
    
    # Coverage metrics
    coverage_metrics: Optional[QuestaCoverageMetrics] = None
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Configuration used
    config_used: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "project_name": self.project_name,
            "success": self.success,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "simulation_results": [
                {
                    "build_success": r.build_success,
                    "sim_success": r.sim_success,
                    "tests_passed": r.tests_passed,
                    "tests_failed": r.tests_failed,
                    "line_coverage": r.line_coverage,
                    "toggle_coverage": r.toggle_coverage,
                    "fsm_coverage": r.fsm_coverage,
                    "branch_coverage": r.branch_coverage,
                    "assertion_coverage": r.assertion_coverage,
                    "functional_coverage": r.functional_coverage,
                } for r in self.simulation_results
            ],
            "formal_results": [
                {
                    "parse_success": r.parse_success,
                    "formal_success": r.formal_success,
                    "assertions_found": r.assertions_found,
                    "assertions_proven": r.assertions_proven,
                    "assertions_failed": r.assertions_failed,
                    "assertions_unproven": r.assertions_unproven,
                    "proof_rate": r.proof_rate,
                    "cover_points_found": r.cover_points_found,
                    "cover_points_reached": r.cover_points_reached,
                } for r in self.formal_results
            ],
            "coverage_metrics": self.coverage_metrics.to_dict() if self.coverage_metrics else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "config_used": self.config_used
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class QuestaEvalRunner:
    """
    Main runner for Questa-based evaluations.
    
    Supports:
    - UVM testbench simulation using QuestaSim
    - SVA formal verification using QuestaFormal
    - Combined simulation + formal workflows
    """
    
    def __init__(self, config: QuestaConfig = None):
        """
        Initialize the Questa evaluation runner.
        
        Args:
            config: Questa configuration. Uses defaults if not provided.
        """
        self.config = config or QuestaConfig()
        self.simulator = None
        self.formal_checker = None
        
        # Lazy initialization of tools
        self._tools_verified = False
    
    def _verify_tools(self):
        """Verify that required Questa tools are available."""
        if self._tools_verified:
            return
        
        try:
            self.simulator = QuestaSimulator(self.config)
            if self.config.enable_formal:
                self.formal_checker = QuestaFormalChecker(self.config)
            self._tools_verified = True
        except RuntimeError as e:
            raise RuntimeError(
                f"Questa tool verification failed: {e}\n"
                "Ensure Questa One is installed and in your PATH.\n"
                "If you have a license server, set LM_LICENSE_FILE or use --license_file."
            )
    
    def evaluate(self, project_path: Path, top_module: str, 
                 test_name: Optional[str] = None, 
                 num_runs: int = 1) -> QuestaEvalResult:
        """
        Evaluate a verification project using Questa tools.
        
        Args:
            project_path: Path to the project directory containing RTL and TB files.
            top_module: Top-level module name.
            test_name: UVM test name to run (optional, for UVM testbenches).
            num_runs: Number of simulation runs to perform.
            
        Returns:
            QuestaEvalResult with evaluation results.
        """
        result = QuestaEvalResult(project_name=project_path.name)
        result.start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        start = time.time()
        
        # Store config for reporting
        result.config_used = {
            "enable_coverage": self.config.enable_coverage,
            "enable_formal": self.config.enable_formal,
            "bounded_depth": self.config.bounded_depth,
            "simulation_timeout_sec": self.config.simulation_timeout_sec,
            "num_runs": num_runs,
            "test_name": test_name
        }
        
        try:
            # Verify tools
            self._verify_tools()
            
            # Discover files
            design_files, tb_files, sva_files = self._discover_files(project_path)
            
            if not design_files:
                result.errors.append("No design files (.sv, .v) found in project.")
                result.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                result.duration_ms = (time.time() - start) * 1000
                return result
            
            if self.config.verbose:
                print(f"Found {len(design_files)} design files, {len(tb_files)} TB files, {len(sva_files)} SVA files")
            
            # Run simulations (if TB files exist or explicit test_name)
            if tb_files or test_name:
                for run_id in range(1, num_runs + 1):
                    if self.config.verbose:
                        print(f"\n=== Simulation Run {run_id}/{num_runs} ===")
                    
                    sim_result = self.simulator.run_simulation(
                        project_path=project_path,
                        design_files=design_files,
                        tb_files=tb_files,
                        top_module=top_module,
                        test_name=test_name,
                        run_id=run_id
                    )
                    result.simulation_results.append(sim_result)
                    
                    if not sim_result.build_success:
                        result.warnings.append(f"Run {run_id}: Build failed")
                    elif not sim_result.sim_success:
                        result.warnings.append(f"Run {run_id}: Simulation failed")
                
                # Aggregate coverage metrics
                if self.config.enable_coverage:
                    result.coverage_metrics = self._aggregate_coverage(
                        project_path.name, result.simulation_results
                    )
            
            # Run formal verification (if enabled and SVA files exist)
            if self.config.enable_formal and sva_files:
                if self.config.verbose:
                    print(f"\n=== Formal Verification ===")
                
                formal_result = self.formal_checker.run_formal(
                    project_path=project_path,
                    design_files=design_files,
                    sva_files=sva_files,
                    top_module=top_module
                )
                result.formal_results.append(formal_result)
                
                if not formal_result.formal_success:
                    result.warnings.append("Formal verification did not complete successfully")
            
            # Determine overall success
            sim_success = all(r.sim_success for r in result.simulation_results) if result.simulation_results else True
            formal_success = all(r.formal_success for r in result.formal_results) if result.formal_results else True
            result.success = sim_success and formal_success
            
        except Exception as e:
            result.errors.append(str(e))
            if self.config.verbose:
                import traceback
                traceback.print_exc()
        
        result.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        result.duration_ms = (time.time() - start) * 1000
        
        return result
    
    def _discover_files(self, project_path: Path):
        """
        Discover design, testbench, and SVA files in a project.
        
        Returns:
            Tuple of (design_files, tb_files, sva_files)
        """
        design_files = []
        tb_files = []
        sva_files = []
        
        # Common patterns for file discovery
        design_patterns = ['*.sv', '*.v', '*.vhd', '*.vhdl']
        tb_patterns = ['tb_*.sv', '*_tb.sv', 'tb/*.sv', 'test*.sv']
        sva_patterns = ['*_assertions.sv', '*_sva.sv', 'assertions/*.sv', '*_props.sv']
        
        # Scan for all Verilog/SystemVerilog files
        all_sv_files = list(project_path.rglob('*.sv')) + list(project_path.rglob('*.v'))
        
        for f in all_sv_files:
            # Skip generated files
            if 'work' in str(f).lower() or '__pycache__' in str(f):
                continue
            
            filename = f.name.lower()
            rel_path = str(f.relative_to(project_path)).lower()
            
            # Categorize file
            if any(pattern in filename for pattern in ['_assertions', '_sva', '_props', '_cover']):
                sva_files.append(f)
            elif any(pattern in filename for pattern in ['tb_', '_tb', 'test_']):
                tb_files.append(f)
            elif 'tb/' in rel_path or 'test/' in rel_path:
                tb_files.append(f)
            elif 'assertions/' in rel_path:
                sva_files.append(f)
            else:
                design_files.append(f)
        
        return design_files, tb_files, sva_files
    
    def _aggregate_coverage(self, project_name: str, 
                           sim_results: List[QuestaSimulationResult]) -> QuestaCoverageMetrics:
        """Aggregate coverage metrics from multiple simulation runs."""
        metrics = QuestaCoverageMetrics(project_name=project_name)
        
        for sim_result in sim_results:
            if sim_result.sim_success:
                metrics.add_run(sim_result)
        
        return metrics
    
    def print_results(self, result: QuestaEvalResult):
        """Print evaluation results in a formatted way."""
        print("\n" + "=" * 60)
        print(f"QUESTA EVALUATION RESULTS: {result.project_name}")
        print("=" * 60)
        
        print(f"\nOverall Success: {'✓ PASS' if result.success else '✗ FAIL'}")
        print(f"Duration: {result.duration_ms:.2f} ms")
        
        # Simulation results
        if result.simulation_results:
            print("\n--- Simulation Results ---")
            total_runs = len(result.simulation_results)
            successful_builds = sum(1 for r in result.simulation_results if r.build_success)
            successful_sims = sum(1 for r in result.simulation_results if r.sim_success)
            
            print(f"  Runs: {total_runs}")
            print(f"  Build Success: {successful_builds}/{total_runs}")
            print(f"  Simulation Success: {successful_sims}/{total_runs}")
            
            # Average coverage
            if result.coverage_metrics:
                print(f"\n  --- Coverage Metrics ---")
                print(f"    Line Coverage:       {result.coverage_metrics.avg_line_coverage:.1f}%")
                print(f"    Toggle Coverage:     {result.coverage_metrics.avg_toggle_coverage:.1f}%")
                print(f"    FSM Coverage:        {result.coverage_metrics.avg_fsm_coverage:.1f}%")
                print(f"    Branch Coverage:     {result.coverage_metrics.avg_branch_coverage:.1f}%")
                print(f"    Assertion Coverage:  {result.coverage_metrics.avg_assertion_coverage:.1f}%")
                print(f"    Functional Coverage: {result.coverage_metrics.avg_functional_coverage:.1f}%")
                print(f"    Overall Coverage:    {result.coverage_metrics.overall_coverage:.1f}%")
        
        # Formal results
        if result.formal_results:
            print("\n--- Formal Verification Results ---")
            for i, fr in enumerate(result.formal_results, 1):
                print(f"  Run {i}:")
                print(f"    Parse Success: {'✓' if fr.parse_success else '✗'}")
                print(f"    Formal Success: {'✓' if fr.formal_success else '✗'}")
                print(f"    Assertions: {fr.assertions_proven}/{fr.assertions_found} proven ({fr.proof_rate:.1f}%)")
                if fr.cover_points_found > 0:
                    print(f"    Cover Points: {fr.cover_points_reached}/{fr.cover_points_found} reached ({fr.cover_rate:.1f}%)")
        
        # Errors and warnings
        if result.errors:
            print("\n--- Errors ---")
            for err in result.errors:
                print(f"  ✗ {err}")
        
        if result.warnings:
            print("\n--- Warnings ---")
            for warn in result.warnings:
                print(f"  ⚠ {warn}")
        
        print("\n" + "=" * 60)


def print_results_table(results: List[QuestaEvalResult]):
    """Print a summary table of multiple evaluation results."""
    print("\n" + "=" * 80)
    print("QUESTA EVALUATION SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Project':<30} {'Status':<10} {'Sim':<8} {'Formal':<8} {'Coverage':<10}")
    print("-" * 80)
    
    for result in results:
        status = "PASS" if result.success else "FAIL"
        
        # Simulation stats
        if result.simulation_results:
            sim_success = sum(1 for r in result.simulation_results if r.sim_success)
            sim_total = len(result.simulation_results)
            sim_str = f"{sim_success}/{sim_total}"
        else:
            sim_str = "N/A"
        
        # Formal stats
        if result.formal_results:
            formal_success = sum(1 for r in result.formal_results if r.formal_success)
            formal_total = len(result.formal_results)
            formal_str = f"{formal_success}/{formal_total}"
        else:
            formal_str = "N/A"
        
        # Coverage
        if result.coverage_metrics:
            coverage_str = f"{result.coverage_metrics.overall_coverage:.1f}%"
        else:
            coverage_str = "N/A"
        
        print(f"{result.project_name:<30} {status:<10} {sim_str:<8} {formal_str:<8} {coverage_str:<10}")
    
    print("-" * 80)
    total = len(results)
    passed = sum(1 for r in results if r.success)
    print(f"Total: {passed}/{total} passed")
    print("=" * 80)

