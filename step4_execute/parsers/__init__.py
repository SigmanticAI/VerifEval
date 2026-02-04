"""
Parsers package

Exports parser classes for different output formats.

Author: TB Eval Team
Version: 0.1.0
"""

from .cocotb_parser import (
    CocoTBResultsParser,
    CocoTBSummaryParser,
    CocoTBXMLValidator,
    parse_cocotb_results,
    validate_cocotb_results,
)

from .vunit_parser import (
    VUnitOutputParser,
    VUnitErrorParser,
    VUnitListParser,
    parse_vunit_output,
    parse_vunit_test_list,
    check_vunit_errors,
)

from .console_parser import (
    ConsoleParser,
    DiagnosticMessage,
    DiagnosticSummary,
    ErrorExtractor,
    MessageSeverity,
    MessageCategory,
    SourceLocation,
    parse_console_output,
    get_diagnostic_summary,
    extract_errors,
)

__all__ = [
    # CocoTB parser
    "CocoTBResultsParser",
    "CocoTBSummaryParser",
    "CocoTBXMLValidator",
    "parse_cocotb_results",
    "validate_cocotb_results",
    
    # VUnit parser
    "VUnitOutputParser",
    "VUnitErrorParser",
    "VUnitListParser",
    "parse_vunit_output",
    "parse_vunit_test_list",
    "check_vunit_errors",
    
    # Console parser
    "ConsoleParser",
    "DiagnosticMessage",
    "DiagnosticSummary",
    "ErrorExtractor",
    "MessageSeverity",
    "MessageCategory",
    "SourceLocation",
    "parse_console_output",
    "get_diagnostic_summary",
    "extract_errors",
]
