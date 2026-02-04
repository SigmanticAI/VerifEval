#!/usr/bin/env python3
"""
Step 3 Orchestrator: Build & Orchestrate
========================================

Main orchestration class that coordinates the entire Step 3 pipeline:

1. Load configuration (route.json + .tbeval.yaml)
2. Detect or generate VUnit project
3. Configure simulator (Questa/Verilator/GHDL)
4. Compile all sources
5. Discover tests
6. Generate build manifest

This is the main entry point for Step 3.

Author: TB Eval Team
Version: 0.1.0
"""

import json
import os
import sys
import time
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from .tracks import get_track_handler, TrackBuildResult

from .models import (
    BuildStatus,
    FailureMode,
    BuildConfig,
    BuildManifest,
    BuildError,
    SimulatorType,
    CompilationResult,
    CompilationError,
    LibraryCompilationResult,
    TestCase,
    TestDiscoveryResult,
    TestStatus,
    VUnitProjectInfo,
    CoverageConfig,
)
from .config import (
    BuildConfigManager,
    RouteInfo,
    ConfigValidationResult,
    load_build_config,
)
from .project import (
    VUnitProjectDetector,
    VUnitProjectGenerator,
    ExistingVUnitProject,
    GeneratedProject,
)
from .simulators import (
    BaseSimulator,
    QuestaSimulator,
    SimulatorCapabilities,
)
from .simulators.license import LicenseCheckResult


# =============================================================================
# ORCHESTRATOR PHASES
# =============================================================================

class OrchestratorPhase(Enum):
    """Phases of the orchestration pipeline"""
    INIT = "initialization"
    CONFIG = "configuration"
    PROJECT_SETUP = "project_setup"
    SIMULATOR_CONFIG = "simulator_config"
    COMPILATION = "compilation"
    TEST_DISCOVERY = "test_discovery"
    TRACK_BUILD = "track_build"
    FINALIZE = "finalize"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PhaseResult:
    """Result of a single phase"""
    phase: OrchestratorPhase
    success: bool
    duration_ms: float = 0.0
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class OrchestratorState:
    """
    Current state of the orchestrator
    
    Tracks progress through phases and accumulated results.
    """
    current_phase: OrchestratorPhase = OrchestratorPhase.INIT
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    
    # Accumulated data
    route_info: Optional[RouteInfo] = None
    build_config: Optional[BuildConfig] = None
    simulator: Optional[BaseSimulator] = None
    vunit_project: Optional[VUnitProjectInfo] = None
    compilation_result: Optional[CompilationResult] = None
    test_discovery: Optional[TestDiscoveryResult] = None
    
    # Error tracking
    track_handler: Optional[Any] = None  # BaseTrack instance
    track_result: Optional[TrackBuildResult] = None
    all_errors: List[str] = field(default_factory=list)
    all_warnings: List[str] = field(default_factory=list)
    
    def add_phase_result(self, result: PhaseResult) -> None:
        """Add result for a phase"""
        self.phase_results[result.phase.value] = result
        self.all_errors.extend(result.errors)
        self.all_warnings.extend(result.warnings)
    
    def get_total_duration_ms(self) -> float:
        """Get total duration so far"""
        return (time.time() - self.start_time) * 1000
    
    def is_failed(self) -> bool:
        """Check if any phase failed"""
        return self.current_phase == OrchestratorPhase.FAILED


# =============================================================================
# CALLBACKS AND HOOKS
# =============================================================================

@dataclass
class OrchestratorCallbacks:
    """
    Callbacks for orchestrator events
    
    Allows external code to hook into orchestrator progress.
    """
    on_phase_start: Optional[Callable[[OrchestratorPhase], None]] = None
    on_phase_complete: Optional[Callable[[PhaseResult], None]] = None
    on_error: Optional[Callable[[str, OrchestratorPhase], None]] = None
    on_warning: Optional[Callable[[str, OrchestratorPhase], None]] = None
    on_progress: Optional[Callable[[str], None]] = None


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class VUnitOrchestrator:
    """
    Main orchestrator for Step 3: Build & Orchestrate
    
    Coordinates the entire build process:
    1. Configuration loading
    2. VUnit project setup
    3. Simulator configuration
    4. Source compilation
    5. Test discovery
    6. Build manifest generation
    
    Usage:
        orchestrator = VUnitOrchestrator(
            submission_dir=Path("./my_project"),
            route_json_path=Path("./my_project/route.json")
        )
        
        manifest = orchestrator.run()
        
        if manifest.is_success():
            print(f"Build successful! {manifest.get_test_count()} tests discovered")
        else:
            print("Build failed:", manifest.errors)
    
    With callbacks:
        def on_progress(msg):
            print(f"[PROGRESS] {msg}")
        
        orchestrator = VUnitOrchestrator(...)
        orchestrator.callbacks.on_progress = on_progress
        manifest = orchestrator.run()
    """
    
    def __init__(
        self,
        submission_dir: Path,
        route_json_path: Optional[Path] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize orchestrator
        
        Args:
            submission_dir: Path to submission directory
            route_json_path: Path to route.json from Step 2
            config_overrides: CLI/programmatic configuration overrides
            output_dir: Output directory (default: submission_dir/.tbeval)
        """
        self.submission_dir = Path(submission_dir).resolve()
        self.route_json_path = route_json_path or (self.submission_dir / "route.json")
        self.config_overrides = config_overrides or {}
        self.output_dir = output_dir or (self.submission_dir / ".tbeval")
        
        # State tracking
        self.state = OrchestratorState()
        
        # Callbacks
        self.callbacks = OrchestratorCallbacks()
        
        # Internal components (initialized during run)
        self._config_manager: Optional[BuildConfigManager] = None
        self._project_detector: Optional[VUnitProjectDetector] = None
        self._project_generator: Optional[VUnitProjectGenerator] = None
    
    # =========================================================================
    # MAIN ENTRY POINTS
    # =========================================================================
    
    def run(self) -> BuildManifest:
        """
        Run the complete build orchestration pipeline
        
        Returns:
            BuildManifest with build results
        """
        try:
            # Phase 1: Configuration
            self._run_phase(
                OrchestratorPhase.CONFIG,
                self._phase_configuration
            )
            
            # Phase 2: Project Setup
            self._run_phase(
                OrchestratorPhase.PROJECT_SETUP,
                self._phase_project_setup
            )
            
            # Phase 3: Simulator Configuration
            self._run_phase(
                OrchestratorPhase.SIMULATOR_CONFIG,
                self._phase_simulator_config
            )

            #Phase 4 Track build
            self._run_phase(OrchestratorPhase.TRACK_BUILD, self._phase_track_build)
            
            # Phase 5: Finalize
            self._run_phase(
                OrchestratorPhase.FINALIZE,
                self._phase_finalize
            )
            
            self.state.current_phase = OrchestratorPhase.COMPLETE
            
        except BuildError as e:
            self._handle_error(str(e), e.stage)
            
        except Exception as e:
            self._handle_error(f"Unexpected error: {str(e)}", "unknown")
        
        # Generate and return manifest
        return self._generate_manifest()
    
    def run_until(self, phase: OrchestratorPhase) -> BuildManifest:
        """
        Run orchestration up to (and including) a specific phase
        
        Args:
            phase: Phase to stop at
        
        Returns:
            BuildManifest with partial results
        """
        phases = [
            (OrchestratorPhase.CONFIG, self._phase_configuration),
            (OrchestratorPhase.PROJECT_SETUP, self._phase_project_setup),
            (OrchestratorPhase.SIMULATOR_CONFIG, self._phase_simulator_config),
            (OrchestratorPhase.COMPILATION, self._phase_compilation),
            (OrchestratorPhase.TEST_DISCOVERY, self._phase_test_discovery),
            (OrchestratorPhase.FINALIZE, self._phase_finalize),
        ]
        
        try:
            for phase_enum, phase_func in phases:
                self._run_phase(phase_enum, phase_func)
                
                if phase_enum == phase:
                    break
                    
        except BuildError as e:
            self._handle_error(str(e), e.stage)
        except Exception as e:
            self._handle_error(f"Unexpected error: {str(e)}", "unknown")
        
        return self._generate_manifest()
    
    # =========================================================================
    # PHASE IMPLEMENTATIONS
    # =========================================================================
    
    def _phase_configuration(self) -> PhaseResult:
        """
        Phase 1: Load and validate configuration
        
        - Load route.json from Step 2
        - Load .tbeval.yaml configuration
        - Merge with CLI overrides
        - Validate configuration
        """
        result = PhaseResult(phase=OrchestratorPhase.CONFIG, success=True)
        
        self._progress("Loading configuration...")
        
        # Check route.json exists
        if not self.route_json_path.exists():
            result.success = False
            result.errors.append(
                f"route.json not found: {self.route_json_path}\n"
                "Run Step 2 (classify) first."
            )
            return result
        
        # Load configuration
        self._config_manager = BuildConfigManager(self.submission_dir)
        
        try:
            self.state.build_config = self._config_manager.load(
                route_json_path=self.route_json_path,
                cli_overrides=self.config_overrides
            )
            self.state.route_info = self._config_manager.get_route_info()
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to load configuration: {str(e)}")
            return result
        
        # Validate configuration
        validation = self._config_manager.validate(self.state.build_config)
        
        if not validation.valid:
            if self.state.build_config.failure_mode == FailureMode.BLOCKING:
                result.success = False
                result.errors.extend([str(e) for e in validation.errors])
            else:
                result.warnings.extend([str(e) for e in validation.errors])
        
        result.warnings.extend([str(w) for w in validation.warnings])
        
        # Store configuration info
        result.data = {
            "route_json": str(self.route_json_path),
            "config_file": str(self._config_manager.get_config_file_path()),
            "tb_type": self.state.route_info.tb_type if self.state.route_info else None,
            "simulator": self.state.build_config.simulator.value,
        }
        
        result.message = f"Configuration loaded: {self.state.build_config.project_name}"
        self._progress(result.message)
        
        return result
    
    def _phase_project_setup(self) -> PhaseResult:
        """
        Phase 2: Setup VUnit project
        
        - Detect existing VUnit setup
        - Generate run.py if needed
        - Configure project structure
        """
        result = PhaseResult(phase=OrchestratorPhase.PROJECT_SETUP, success=True)
        
        self._progress("Setting up VUnit project...")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._project_detector = VUnitProjectDetector(self.submission_dir)
        self._project_generator = VUnitProjectGenerator(self.submission_dir)
        
        # Check for existing VUnit setup
        existing_project = self._project_detector.detect()
        
        if existing_project and existing_project.usable:
            self._progress(f"Found existing VUnit setup: {existing_project.run_script}")
            
            self.state.vunit_project = VUnitProjectInfo(
                run_py_path=str(existing_project.run_script),
                generated=False,
                libraries=existing_project.libraries,
                simulator_name=existing_project.simulator or "modelsim",
            )
            
            result.data["existing_project"] = True
            result.data["run_script"] = str(existing_project.run_script)
            result.warnings.extend(existing_project.issues)
            
        else:
            # Generate new VUnit project
            self._progress("Generating VUnit project...")
            
            try:
                generated = self._project_generator.generate(
                    route=self.state.route_info,
                    build_config=self.state.build_config,
                    output_dir=self.output_dir
                )
                
                self.state.vunit_project = VUnitProjectInfo(
                    run_py_path=str(generated.run_script),
                    generated=True,
                    output_path=str(self.output_dir / "vunit_out"),
                )
                
                result.data["existing_project"] = False
                result.data["run_script"] = str(generated.run_script)
                result.data["template_used"] = generated.template_used
                result.warnings.extend(generated.warnings)
                
                if generated.makefile:
                    result.data["makefile"] = str(generated.makefile)
                    
            except Exception as e:
                result.success = False
                result.errors.append(f"Failed to generate VUnit project: {str(e)}")
                return result
        
        result.message = f"VUnit project ready: {self.state.vunit_project.run_py_path}"
        self._progress(result.message)
        
        return result
    
    def _phase_simulator_config(self) -> PhaseResult:
        """
        Phase 3: Configure simulator
        
        - Detect simulator installation
        - Validate license (for commercial sims)
        - Configure simulator options
        """
        result = PhaseResult(phase=OrchestratorPhase.SIMULATOR_CONFIG, success=True)
        
        simulator_type = self.state.build_config.simulator
        self._progress(f"Configuring simulator: {simulator_type.value}...")
        
        # Create simulator instance based on type
        if simulator_type in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            self.state.simulator = QuestaSimulator(
                self.state.build_config.simulator_config
            )
        elif simulator_type == SimulatorType.VERILATOR:
            # Use skeleton for now
            from .simulators.verilator import VerilatorSimulator
            self.state.simulator = VerilatorSimulator(
                self.state.build_config.simulator_config
            )
        elif simulator_type == SimulatorType.GHDL:
            from .simulators.ghdl import GHDLSimulator
            self.state.simulator = GHDLSimulator(
                self.state.build_config.simulator_config
            )
        else:
            result.success = False
            result.errors.append(f"Unsupported simulator: {simulator_type.value}")
            return result
        
        # Check simulator availability
        if not self.state.simulator.is_available():
            error_msg = f"Simulator '{simulator_type.value}' is not available"
            
            if self.state.build_config.failure_mode == FailureMode.BLOCKING:
                result.success = False
                result.errors.append(error_msg)
                return result
            else:
                result.warnings.append(error_msg)
        
        # Get simulator info
        sim_info = self.state.simulator.get_info()
        result.data["simulator_info"] = sim_info
        
        # Check license for commercial simulators
        if simulator_type in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            questa_sim: QuestaSimulator = self.state.simulator
            license_result = questa_sim.check_license()
            
            result.data["license"] = license_result.to_dict()
            
            if not license_result.is_valid():
                if self.state.build_config.failure_mode == FailureMode.BLOCKING:
                    result.success = False
                    result.errors.append(f"License error: {license_result.message}")
                    return result
                else:
                    result.warnings.append(f"License warning: {license_result.message}")
        
        # Validate for project requirements
        project_requirements = {
            "tb_type": self.state.route_info.tb_type,
            "language": self.state.route_info.language,
        }
        validation_issues = self.state.simulator.validate_for_project(project_requirements)
        
        for issue in validation_issues:
            if "not support" in issue.lower():
                result.success = False
                result.errors.append(issue)
            else:
                result.warnings.append(issue)
        
        result.message = f"Simulator configured: {sim_info.get('name', simulator_type.value)}"
        if sim_info.get('version'):
            result.message += f" v{sim_info['version']}"
        
        self._progress(result.message)
        
        return result
    
    def _phase_compilation(self) -> PhaseResult:
        """
        Phase 4: Compile sources
        
        - Run VUnit compilation
        - Capture errors and warnings
        - Handle compilation failures
        """
        result = PhaseResult(phase=OrchestratorPhase.COMPILATION, success=True)
        
        self._progress("Compiling sources...")
        
        # Prepare compilation
        run_script = Path(self.state.vunit_project.run_py_path)
        
        if not run_script.exists():
            result.success = False
            result.errors.append(f"Run script not found: {run_script}")
            return result
        
        # Build VUnit command for compilation only
        vunit_cmd = [
            sys.executable,
            str(run_script),
            "--compile",  # Compile only, don't run
            f"--output-path={self.output_dir / 'vunit_out'}",
        ]
        
        # Add parallel jobs
        if self.state.build_config.parallel_jobs > 1:
            vunit_cmd.append(f"-p={self.state.build_config.parallel_jobs}")
        
        # Add clean flag if needed
        if self.state.build_config.clean_build:
            vunit_cmd.append("--clean")
        
        # Run compilation
        start_time = time.time()
        
        try:
            # Get simulator environment
            env = os.environ.copy()
            if self.state.simulator:
                sim_env = self.state.simulator.get_environment()
                env.update(sim_env.env_vars)
            
            self._progress(f"Running: {' '.join(vunit_cmd)}")
            
            compile_result = subprocess.run(
                vunit_cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=env,
                cwd=str(run_script.parent),
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Parse compilation output
            compilation = self._parse_compilation_output(
                compile_result.stdout,
                compile_result.stderr,
                compile_result.returncode,
                duration_ms
            )
            
            self.state.compilation_result = compilation
            
            if not compilation.is_success():
                if self.state.build_config.failure_mode == FailureMode.BLOCKING:
                    result.success = False
                    result.errors.append("Compilation failed")
                    for err in compilation.get_all_errors():
                        result.errors.append(str(err))
                else:
                    result.warnings.append("Compilation had errors")
                    for err in compilation.get_all_errors():
                        result.warnings.append(str(err))
            
            result.data["compilation"] = compilation.to_dict()
            result.duration_ms = duration_ms
            
        except subprocess.TimeoutExpired:
            result.success = False
            result.errors.append("Compilation timed out after 10 minutes")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Compilation failed: {str(e)}")
        
        if result.success:
            result.message = f"Compilation successful ({self.state.compilation_result.total_files} files)"
        else:
            result.message = "Compilation failed"
        
        self._progress(result.message)
        
        return result
    
    def _phase_test_discovery(self) -> PhaseResult:
        """
        Phase 5: Discover tests
        
        - Run VUnit to list tests
        - Parse UVM tests if applicable
        - Build test list
        """
        result = PhaseResult(phase=OrchestratorPhase.TEST_DISCOVERY, success=True)
        
        self._progress("Discovering tests...")
        
        # Run VUnit with --list flag to discover tests
        run_script = Path(self.state.vunit_project.run_py_path)
        
        vunit_cmd = [
            sys.executable,
            str(run_script),
            "--list",
            f"--output-path={self.output_dir / 'vunit_out'}",
        ]
        
        start_time = time.time()
        
        try:
            env = os.environ.copy()
            if self.state.simulator:
                sim_env = self.state.simulator.get_environment()
                env.update(sim_env.env_vars)
            
            list_result = subprocess.run(
                vunit_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                cwd=str(run_script.parent),
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Parse test list
            tests = self._parse_test_list(list_result.stdout)
            
            # For UVM projects, also parse UVM test names
            if self.state.route_info.tb_type == "uvm_sv":
                uvm_tests = self._discover_uvm_tests()
                tests.extend(uvm_tests)
            
            # Create discovery result
            self.state.test_discovery = TestDiscoveryResult(
                tests=tests,
                discovery_method="vunit" if self.state.route_info.tb_type != "uvm_sv" else "uvm",
                duration_ms=duration_ms,
            )
            
            result.data["test_count"] = len(tests)
            result.data["tests"] = [t.to_dict() for t in tests[:20]]  # First 20
            
            if len(tests) == 0:
                result.warnings.append("No tests discovered")
            
        except subprocess.TimeoutExpired:
            result.warnings.append("Test discovery timed out")
            self.state.test_discovery = TestDiscoveryResult(tests=[])
            
        except Exception as e:
            result.warnings.append(f"Test discovery failed: {str(e)}")
            self.state.test_discovery = TestDiscoveryResult(tests=[])
        
        test_count = len(self.state.test_discovery.tests) if self.state.test_discovery else 0
        result.message = f"Discovered {test_count} tests"
        self._progress(result.message)
        
        return result
    # Add new method after _phase_test_discovery (around line 450):

    def _phase_track_build(self) -> PhaseResult:
        """
        Phase: Track-specific build
        
        - Initialize track handler (A or B)
        - Run track-specific compilation
        - Track-specific test discovery
        - Prepare execution environment
        """
        result = PhaseResult(phase=OrchestratorPhase.TRACK_BUILD, success=True)
        
        self._progress("Running track-specific build...")
        
        try:
            # Get track handler based on route info
            self.state.track_handler = get_track_handler(
                route_info=self.state.route_info,
                build_config=self.state.build_config,
                submission_dir=self.submission_dir,
            )
            
            track_name = self.state.track_handler.get_track_name()
            self._progress(f"Using {track_name}")
            
            # Validate prerequisites
            prereq_errors = self.state.track_handler.validate_prerequisites()
            if prereq_errors:
                for err in prereq_errors:
                    if self.state.build_config.failure_mode == FailureMode.BLOCKING:
                        result.errors.append(err)
                    else:
                        result.warnings.append(err)
                
                if result.errors:
                    result.success = False
                    return result
            
            # Run track build pipeline
            track_result = self.state.track_handler.build()
            self.state.track_result = track_result
            
            if not track_result.success:
                result.success = False
                result.errors.extend(track_result.errors)
            
            result.warnings.extend(track_result.warnings)
            
            # Store results
            result.data = {
                "track": track_name,
                "compilation_success": track_result.compilation.is_success() if track_result.compilation else False,
                "tests_found": track_result.tests_discovered.total_count if track_result.tests_discovered else 0,
                "execution_command": track_result.execution_command,
            }
            
            # Use track's test discovery result
            if track_result.tests_discovered:
                self.state.test_discovery = track_result.tests_discovered
            
            # Use track's compilation result
            if track_result.compilation:
                self.state.compilation_result = track_result.compilation
            
            result.message = f"{track_name}: {result.data.get('tests_found', 0)} tests ready"
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Track build failed: {str(e)}")
        
        self._progress(result.message if result.success else "Track build failed")
        
        return result
    
    def _phase_finalize(self) -> PhaseResult:
        """
        Phase 6: Finalize build
        
        - Save build manifest
        - Generate summary
        - Cleanup if needed
        """
        result = PhaseResult(phase=OrchestratorPhase.FINALIZE, success=True)
        
        self._progress("Finalizing build...")
        
        # Save intermediate outputs
        try:
            # Save simulator config
            sim_config_path = self.output_dir / "simulator_config.json"
            if self.state.simulator:
                with open(sim_config_path, 'w') as f:
                    json.dump(self.state.simulator.get_info(), f, indent=2)
                result.data["simulator_config_path"] = str(sim_config_path)
            
            # Create compilation log
            if self.state.compilation_result:
                log_dir = self.output_dir / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                
                compile_log = log_dir / "compile.log"
                with open(compile_log, 'w') as f:
                    f.write(f"Compilation completed at {datetime.now().isoformat()}\n")
                    f.write(f"Status: {self.state.compilation_result.status.value}\n")
                    f.write(f"Files: {self.state.compilation_result.total_files}\n")
                    f.write(f"Errors: {self.state.compilation_result.total_errors}\n")
                    f.write(f"Warnings: {self.state.compilation_result.total_warnings}\n")
                
                result.data["compile_log"] = str(compile_log)
            
        except Exception as e:
            result.warnings.append(f"Failed to save some outputs: {str(e)}")
        
        result.message = "Build finalized"
        self._progress(result.message)
        
        return result
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _run_phase(
        self,
        phase: OrchestratorPhase,
        phase_func: Callable[[], PhaseResult]
    ) -> None:
        """Run a single phase with timing and callbacks"""
        # Notify phase start
        if self.callbacks.on_phase_start:
            self.callbacks.on_phase_start(phase)
        
        self.state.current_phase = phase
        start_time = time.time()
        
        try:
            result = phase_func()
            result.duration_ms = (time.time() - start_time) * 1000
            
        except Exception as e:
            result = PhaseResult(
                phase=phase,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                errors=[f"Phase failed with exception: {str(e)}"]
            )
        
        # Store result
        self.state.add_phase_result(result)
        
        # Notify phase complete
        if self.callbacks.on_phase_complete:
            self.callbacks.on_phase_complete(result)
        
        # Handle failure
        if not result.success:
            if self.state.build_config and self.state.build_config.failure_mode == FailureMode.BLOCKING:
                self.state.current_phase = OrchestratorPhase.FAILED
                raise BuildError(
                    message=result.errors[0] if result.errors else "Phase failed",
                    stage=phase.value
                )
    
    def _handle_error(self, message: str, stage: str) -> None:
        """Handle an error during orchestration"""
        self.state.current_phase = OrchestratorPhase.FAILED
        self.state.all_errors.append(f"[{stage}] {message}")
        
        if self.callbacks.on_error:
            self.callbacks.on_error(message, OrchestratorPhase(stage) if stage in [p.value for p in OrchestratorPhase] else OrchestratorPhase.FAILED)
    
    def _progress(self, message: str) -> None:
        """Report progress"""
        if self.callbacks.on_progress:
            self.callbacks.on_progress(message)
    
    def _parse_compilation_output(
        self,
        stdout: str,
        stderr: str,
        return_code: int,
        duration_ms: float
    ) -> CompilationResult:
        """Parse VUnit/simulator compilation output"""
        result = CompilationResult(
            duration_ms=duration_ms,
        )
        
        # Determine status from return code
        if return_code == 0:
            result.status = BuildStatus.SUCCESS
        else:
            result.status = BuildStatus.FAILURE
        
        # Parse output for errors and warnings
        combined_output = stdout + "\n" + stderr
        errors = []
        warnings = []
        
        # Common error patterns
        error_patterns = [
            r'(?:Error|ERROR):\s*(.+)',
            r'\*\*\s*Error:\s*(.+)',
            r'(?:Fatal|FATAL):\s*(.+)',
        ]
        
        warning_patterns = [
            r'(?:Warning|WARNING):\s*(.+)',
            r'\*\*\s*Warning:\s*(.+)',
        ]
        
        import re
        
        for line in combined_output.split('\n'):
            for pattern in error_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    errors.append(CompilationError(
                        file="",
                        line=0,
                        severity="error",
                        message=match.group(1).strip()
                    ))
                    break
            
            for pattern in warning_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    warnings.append(CompilationError(
                        file="",
                        line=0,
                        severity="warning",
                        message=match.group(1).strip()
                    ))
                    break
        
        # Create library result
        lib_result = LibraryCompilationResult(
            library_name="work",
            success=(return_code == 0),
            errors=errors,
            warnings=warnings,
        )
        
        result.libraries = [lib_result]
        result.total_errors = len(errors)
        result.total_warnings = len(warnings)
        
        # Count files (simple heuristic)
        file_pattern = r'(?:Compiling|Analyzing)\s+(.+\.(?:sv|v|vhd|vhdl))'
        files = re.findall(file_pattern, combined_output, re.IGNORECASE)
        result.total_files = len(set(files))
        
        return result
    
    def _parse_test_list(self, output: str) -> List[TestCase]:
        """Parse VUnit --list output"""
        tests = []
        
        # VUnit list format: library.test_bench.test_name
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse test name
            parts = line.split('.')
            if len(parts) >= 2:
                library = parts[0] if len(parts) >= 3 else "work"
                testbench = parts[-2] if len(parts) >= 2 else "unknown"
                test_name = parts[-1]
                
                tests.append(TestCase(
                    name=test_name,
                    full_name=line,
                    testbench=testbench,
                    library=library,
                    test_type="vunit",
                    status=TestStatus.READY,
                ))
        
        return tests
    
    def _discover_uvm_tests(self) -> List[TestCase]:
        """Discover UVM test classes from source files"""
        tests = []
        
        import re
        
        # Pattern to find UVM test classes
        uvm_test_pattern = r'class\s+(\w+)\s+extends\s+uvm_test'
        
        for tb_file in self.state.route_info.tb_files:
            file_path = self.submission_dir / tb_file
            if file_path.exists() and file_path.suffix in ['.sv', '.svh']:
                try:
                    content = file_path.read_text(errors='ignore')
                    for match in re.finditer(uvm_test_pattern, content):
                        test_name = match.group(1)
                        tests.append(TestCase(
                            name=test_name,
                            full_name=f"uvm.{test_name}",
                            testbench="uvm_top",
                            test_type="uvm",
                            status=TestStatus.READY,
                            plusargs=[f"+UVM_TESTNAME={test_name}"],
                        ))
                except Exception:
                    pass
        
        return tests
    
    def _generate_manifest(self) -> BuildManifest:
        """Generate the final build manifest"""
        # Determine overall status
        if self.state.is_failed():
            status = BuildStatus.FAILURE
        elif self.state.all_errors:
            status = BuildStatus.WARNING
        elif self.state.compilation_result and not self.state.compilation_result.is_success():
            status = BuildStatus.FAILURE
        else:
            status = BuildStatus.SUCCESS
        
        manifest = BuildManifest(
            build_status=status,
            timestamp=datetime.now().isoformat(),
            duration_ms=self.state.get_total_duration_ms(),
            route_json_path=str(self.route_json_path),
            submission_dir=str(self.submission_dir),
            vunit_project=self.state.vunit_project,
            simulator_config=self.state.build_config.simulator_config if self.state.build_config else None,
            compilation=self.state.compilation_result,
            tests_discovered=self.state.test_discovery,
            coverage_config=self.state.build_config.coverage if self.state.build_config else None,
            errors=self.state.all_errors,
            warnings=self.state.all_warnings,
        )

        if self.state.track_result:
            manifest.execution_command = self.state.track_result.execution_command
            manifest.execution_env = self.state.track_result.execution_env
            manifest.execution_cwd = self.state.track_result.execution_cwd
        
        # Save manifest
        manifest_path = self.output_dir / "build_manifest.json"
        manifest.save(manifest_path)
        
        return manifest
    
    # =========================================================================
    # PUBLIC QUERY METHODS
    # =========================================================================
    
    def get_state(self) -> OrchestratorState:
        """Get current orchestrator state"""
        return self.state
    
    def get_phase_result(self, phase: OrchestratorPhase) -> Optional[PhaseResult]:
        """Get result for a specific phase"""
        return self.state.phase_results.get(phase.value)
    
    def is_complete(self) -> bool:
        """Check if orchestration completed successfully"""
        return self.state.current_phase == OrchestratorPhase.COMPLETE
    
    def is_failed(self) -> bool:
        """Check if orchestration failed"""
        return self.state.is_failed()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def build_project(
    submission_dir: Path,
    route_json_path: Optional[Path] = None,
    simulator: Optional[str] = None,
    coverage: bool = True,
    failure_mode: str = "advisory",
    verbose: bool = False,
) -> BuildManifest:
    """
    Convenience function to build a project
    
    Args:
        submission_dir: Path to submission directory
        route_json_path: Path to route.json (optional)
        simulator: Simulator to use (optional)
        coverage: Enable coverage collection
        failure_mode: 'blocking' or 'advisory'
        verbose: Print progress messages
    
    Returns:
        BuildManifest with results
    """
    # Build config overrides
    overrides = {
        "failure_mode": failure_mode,
    }
    
    if simulator:
        overrides["simulator"] = simulator
    
    if not coverage:
        overrides["no_coverage"] = True
    
    # Create orchestrator
    orchestrator = VUnitOrchestrator(
        submission_dir=Path(submission_dir),
        route_json_path=Path(route_json_path) if route_json_path else None,
        config_overrides=overrides,
    )
    
    # Setup verbose callback
    if verbose:
        orchestrator.callbacks.on_progress = lambda msg: print(f"[BUILD] {msg}")
        orchestrator.callbacks.on_phase_start = lambda p: print(f"\n>>> Starting phase: {p.value}")
        orchestrator.callbacks.on_phase_complete = lambda r: print(
            f"<<< Phase {r.phase.value}: {'OK' if r.success else 'FAILED'} ({r.duration_ms:.0f}ms)"
        )
    
    # Run build
    return orchestrator.run()


# =============================================================================
# CLI SUPPORT
# =============================================================================

def main():
    """CLI entry point for Step 3"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Step 3: Build & Orchestrate - Compile and prepare for test execution"
    )
    
    parser.add_argument(
        "submission_dir",
        type=Path,
        help="Path to submission directory"
    )
    
    parser.add_argument(
        "--route", "-r",
        type=Path,
        default=None,
        help="Path to route.json (default: submission_dir/route.json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output directory (default: submission_dir/.tbeval)"
    )
    
    parser.add_argument(
        "--simulator", "-s",
        choices=["questa", "modelsim", "verilator", "ghdl"],
        default=None,
        help="Override simulator selection"
    )
    
    parser.add_argument(
        "--coverage/--no-coverage",
        default=True,
        help="Enable/disable coverage collection"
    )
    
    parser.add_argument(
        "--failure-mode",
        choices=["blocking", "advisory"],
        default="advisory",
        help="How to handle failures"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only"
    )
    
    args = parser.parse_args()
    
    # Run build
    manifest = build_project(
        submission_dir=args.submission_dir,
        route_json_path=args.route,
        simulator=args.simulator,
        coverage=args.coverage,
        failure_mode=args.failure_mode,
        verbose=args.verbose and not args.json,
    )
    
    # Output
    if args.json:
        print(manifest.to_json())
    else:
        print("\n" + "=" * 60)
        print(" BUILD SUMMARY")
        print("=" * 60)
        print(f"Status: {manifest.build_status.value.upper()}")
        print(f"Duration: {manifest.duration_ms:.0f}ms")
        print(f"Tests Discovered: {manifest.get_test_count()}")
        
        if manifest.errors:
            print(f"\nErrors ({len(manifest.errors)}):")
            for err in manifest.errors:
                print(f"  ✗ {err}")
        
        if manifest.warnings:
            print(f"\nWarnings ({len(manifest.warnings)}):")
            for warn in manifest.warnings:
                print(f"  ⚠ {warn}")
        
        print("=" * 60)
        
        if manifest.is_ready_for_execution():
            print("✓ Build successful - ready for execution")
        else:
            print("✗ Build failed - see errors above")
    
    # Exit code
    return 0 if manifest.is_success() else 1


if __name__ == "__main__":
    sys.exit(main())
