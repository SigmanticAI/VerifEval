"""
File Discovery Module
=====================

Handles file discovery and manifest parsing for submissions.

Components:
- FileFinder: Scans directories to find DUT and testbench files
- ManifestParser: Parses submission.yaml manifest files

File Discovery Strategy:
1. Check manifest for explicit file lists
2. Scan known DUT directories (rtl/, src/, design/)
3. Scan known TB directories (tb/, test/, testbench/)
4. Fall back to pattern matching in root

Usage:
    from step2_classify_route.discovery import FileFinder, ManifestParser
    
    # Find files automatically
    finder = FileFinder(root_dir, config)
    dut_files = finder.find_dut_files()
    tb_files = finder.find_testbench_files()
    
    # Or use manifest
    parser = ManifestParser(root_dir)
    manifest = parser.load_manifest()
    dut_files = parser.get_dut_files()
"""

from .file_finder import FileFinder
from .manifest_parser import ManifestParser

__all__ = [
    "FileFinder",
    "ManifestParser",
]
