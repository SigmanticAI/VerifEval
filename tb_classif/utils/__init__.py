"""
Utility Module
==============

Common utilities for file validation and project structure checking.

Components:
- FileValidator: Validates individual files (existence, syntax)
- ProjectValidator: Validates entire project structure

Usage:
    from step2_classify_route.utils import FileValidator, ProjectValidator
    
    # Validate single file
    valid, msg = FileValidator.validate_file_exists(path)
    
    # Validate project
    validator = ProjectValidator(root_dir)
    results = validator.validate_project(dut_files, tb_files)
"""

from .validators import FileValidator, ProjectValidator

__all__ = [
    "FileValidator",
    "ProjectValidator",
]
