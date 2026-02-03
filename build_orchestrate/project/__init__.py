"""
VUnit Project Setup Module
==========================

This module handles VUnit project detection and generation:
- Detecting existing VUnit configurations
- Generating run.py from templates
- Configuring for different TB types and simulators

Main Components:
- VUnitProjectDetector: Detect existing VUnit setup
- VUnitProjectGenerator: Generate run.py from templates
- TemplateManager: Manage Jinja2 templates

Usage:
    from step3_build_orchestrate.project import VUnitProjectGenerator
    
    generator = VUnitProjectGenerator(submission_dir)
    run_py_path = generator.generate(route_info, build_config)
"""

from .detector import VUnitProjectDetector, ExistingVUnitProject
from .generator import (
    VUnitProjectGenerator,
    TemplateManager,
    GeneratedProject,
    GenerationConfig,
)

__all__ = [
    # Detector
    "VUnitProjectDetector",
    "ExistingVUnitProject",
    # Generator
    "VUnitProjectGenerator",
    "TemplateManager",
    "GeneratedProject",
    "GenerationConfig",
]
