"""
step7_score.questa — Questa integration for Tier 2 scoring

This sub-package handles:
    - License and tool availability detection
    - Functional coverage parsing (SystemVerilog covergroups)
    - Assertion coverage analysis (SVA properties)
    - UVM conformance checking

The ``license_checker`` module is the entry-point used by the
``TestbenchAnalyzer`` to decide whether Tier 2 scoring is possible.

Quick check::

    from step7_score.questa import is_tier2_available
    if is_tier2_available():
        print("Questa detected — Tier 2 scoring enabled")
"""

from .license_checker import (
    QuestaLicenseChecker,
    QuestaCapabilities,
    QuestaToolInfo,
    check_questa_availability,
    is_questa_available,
    is_tier2_available,
    get_questa_version,
    print_questa_status,
)

__all__ = [
    "QuestaLicenseChecker",
    "QuestaCapabilities",
    "QuestaToolInfo",
    "check_questa_availability",
    "is_questa_available",
    "is_tier2_available",
    "get_questa_version",
    "print_questa_status",
]
