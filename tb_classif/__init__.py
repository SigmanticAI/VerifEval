"""
Step 2: Classify and Route Submission
=====================================

This module classifies RTL testbench submissions and routes them
to the appropriate execution track (CocoTB/Python or VUnit/HDL).

Main Components:
- ClassifierRouter: Main orchestration class
- RoutingDecision: Output data structure
- QualityReport: Static analysis results

Usage:
    from step2_classify_route import ClassifierRouter
    
    router = ClassifierRouter(Path("./my_project"))
    routing = router.classify_and_route()
    
    if routing.is_valid():
        print(f"Track: {routing.track}")
        print(f"Simulator: {routing.chosen_simulator}")
"""

__version__ = "0.1.0"
__author__ = "TB Eval Team"

from .orchestrator import ClassifierRouter
from .config import ConfigManager, ProjectConfig
from .models import (
    # Enums
    TBType,
    Track,
    Simulator,
    Language,
    QualityStatus,
    # Data classes
    RoutingDecision,
    QualityReport,
    DetectionResult,
    Violation,
    FileQualityReport,
)

__all__ = [
    # Main classes
    "ClassifierRouter",
    "ConfigManager",
    "ProjectConfig",
    # Enums
    "TBType",
    "Track", 
    "Simulator",
    "Language",
    "QualityStatus",
    # Data classes
    "RoutingDecision",
    "QualityReport",
    "DetectionResult",
    "Violation",
    "FileQualityReport",
]
