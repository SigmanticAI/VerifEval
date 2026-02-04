"""
Step 3: Build & Orchestrate
===========================

This module handles the build and orchestration phase of testbench evaluation:
- VUnit project setup and configuration
- Simulator configuration (Questa, Verilator, GHDL)
- Compilation management
- Test discovery

Main Components:
- VUnitOrchestrator: Main orchestration class
- BuildConfig: Build configuration
- BuildManifest: Output of build phase

Usage:
    from step3_build_orchestrate import VUnitOrchestrator, BuildConfig
    
    orchestrator = VUnitOrchestrator(
        submission_dir=Path("./my_project"),
        route_json=Path("./my_project/route.json")
    )
    
    manifest = orchestrator.build()
    
    if manifest.is_ready_for_execution():
        print(f"Ready to run {manifest.get_test_count()} tests")
"""

__version__ = "0.1.0"
__author__ = "TB Eval Team"

from .models import (
    # Enums
    BuildStatus,
    FailureMode,
    CoverageType,
    SimulatorType,
    LicenseType,
    LicenseStatus,
    TestStatus,
    # License
    LicenseInfo,
    # Simulator configs
    BaseSimulatorConfig,
    QuestaConfig,
    VerilatorConfig,
    GHDLConfig,
    # Compilation
    CompilationError,
    LibraryCompilationResult,
    CompilationResult,
    # Tests
    TestCase,
    TestDiscoveryResult,
    # Build
    CoverageConfig,
    BuildConfig,
    VUnitProjectInfo,
    BuildManifest,
    BuildError,
)

from .config import (
    BuildConfigManager,
    ConfigError,
    ConfigValidationResult,
    RouteInfo,
    EnvironmentVariables,
    load_build_config,
    create_default_config_file,
)

# Orchestrator will be added after implementation
# from .orchestrator import VUnitOrchestrator

__all__ = [
    # Version
    "__version__",
    # Enums
    "BuildStatus",
    "FailureMode",
    "CoverageType",
    "SimulatorType",
    "LicenseType",
    "LicenseStatus",
    "TestStatus",
    # License
    "LicenseInfo",
    # Simulator configs
    "BaseSimulatorConfig",
    "QuestaConfig",
    "VerilatorConfig",
    "GHDLConfig",
    # Compilation
    "CompilationError",
    "LibraryCompilationResult",
    "CompilationResult",
    # Tests
    "TestCase",
    "TestDiscoveryResult",
    # Build
    "CoverageConfig",
    "BuildConfig",
    "VUnitProjectInfo",
    "BuildManifest",
    "BuildError",
    # Config
    "BuildConfigManager",
    "ConfigError",
    "ConfigValidationResult",
    "RouteInfo",
    "EnvironmentVariables",
    "load_build_config",
    "create_default_config_file",
    # Orchestrator
    # "VUnitOrchestrator",
    "VUnitOrchestrator",
    "OrchestratorPhase",
    "OrchestratorState",
    "OrchestratorCallbacks",
    "PhaseResult",
    "build_project",


]
