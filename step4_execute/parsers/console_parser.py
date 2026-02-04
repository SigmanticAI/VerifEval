"""
Generic console output parser

Parses console output for errors, warnings, and diagnostics.
Works with output from various simulators and tools.

Author: TB Eval Team
Version: 0.1.0
"""

import re
from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class MessageSeverity(Enum):
    """Message severity levels"""
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class MessageCategory(Enum):
    """Message categories"""
    SYNTAX_ERROR = "syntax_error"
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    ASSERTION_FAILURE = "assertion_failure"
    LINT_WARNING = "lint_warning"
    SIMULATOR_WARNING = "simulator_warning"
    TIMING_VIOLATION = "timing_violation"
    LICENSE_ERROR = "license_error"
    FILE_NOT_FOUND = "file_not_found"
    UNKNOWN = "unknown"


@dataclass
class SourceLocation:
    """Source code location"""
    file_path: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    
    def __str__(self) -> str:
        """String representation"""
        if not self.file_path:
            return "unknown location"
        
        result = str(self.file_path)
        if self.line:
            result += f":{self.line}"
            if self.column:
                result += f":{self.column}"
        
        return result


@dataclass
class DiagnosticMessage:
    """
    A diagnostic message from console output
    
    Attributes:
        severity: Message severity (error, warning, etc.)
        category: Message category
        message: The actual message text
        location: Source location if available
        tool: Tool that generated the message
        code: Error/warning code if available
        raw_line: Original line from output
    """
    severity: MessageSeverity
    category: MessageCategory
    message: str
    location: SourceLocation = field(default_factory=SourceLocation)
    tool: Optional[str] = None
    code: Optional[str] = None
    raw_line: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation"""
        parts = [self.severity.value.upper()]
        
        if self.location.file_path:
            parts.append(str(self.location))
        
        if self.code:
            parts.append(f"[{self.code}]")
        
        parts.append(self.message)
        
        return " ".join(parts)


class ConsoleParser:
    """
    Generic console output parser
    
    Supports multiple simulators and tools:
    - Verilator
    - ModelSim/Questa
    - VCS
    - GHDL
    - Icarus Verilog
    - Yosys
    - Verible
    """
    
    def __init__(self):
        """Initialize parser with patterns for various tools"""
        
        # Verilator patterns
        self.verilator_patterns = [
            # %Error: file.v:42:1: syntax error
            re.compile(
                r'%(?P<severity>Error|Warning|Info|Fatal)(?:-[A-Z_]+)?: '
                r'(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): '
                r'(?P<message>.+)$'
            ),
            # %Error: message without location
            re.compile(
                r'%(?P<severity>Error|Warning|Info|Fatal)(?:-[A-Z_]+)?: '
                r'(?P<message>.+)$'
            ),
        ]
        
        # ModelSim/Questa patterns
        self.modelsim_patterns = [
            # ** Error: (vlog-2110) file.sv(42): syntax error
            re.compile(
                r'\*\* (?P<severity>Error|Warning|Note|Fatal): '
                r'\((?P<code>[a-z]+-\d+)\) '
                r'(?P<file>[^(]+)\((?P<line>\d+)\): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
            # ** Error: (vcom-11) Could not find work.package
            re.compile(
                r'\*\* (?P<severity>Error|Warning|Note|Fatal): '
                r'\((?P<code>[a-z]+-\d+)\) '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
            # ** Error: message without code
            re.compile(
                r'\*\* (?P<severity>Error|Warning|Note|Fatal): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
        ]
        
        # GHDL patterns
        self.ghdl_patterns = [
            # file.vhd:42:1:error: syntax error
            re.compile(
                r'(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):'
                r'(?P<severity>error|warning|note): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
            # ghdl:error: message
            re.compile(
                r'ghdl:(?P<severity>error|warning|note): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
        ]
        
        # VCS patterns
        self.vcs_patterns = [
            # Error-[ID] file.sv, line 42: message
            re.compile(
                r'(?P<severity>Error|Warning)-\[(?P<code>[A-Z_]+)\] '
                r'(?P<file>[^,]+), line (?P<line>\d+): '
                r'(?P<message>.+)$'
            ),
            # Error: message
            re.compile(
                r'(?P<severity>Error|Warning): '
                r'(?P<message>.+)$'
            ),
        ]
        
        # Icarus Verilog patterns
        self.icarus_patterns = [
            # file.v:42: error: message
            re.compile(
                r'(?P<file>[^:]+):(?P<line>\d+): '
                r'(?P<severity>error|warning|sorry): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
        ]
        
        # Yosys patterns
        self.yosys_patterns = [
            # ERROR: message in file.v:42
            re.compile(
                r'(?P<severity>ERROR|WARNING): '
                r'(?P<message>.+?) in '
                r'(?P<file>[^:]+):(?P<line>\d+)',
                re.IGNORECASE
            ),
            # ERROR: message
            re.compile(
                r'(?P<severity>ERROR|WARNING): '
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
        ]
        
        # Verible patterns
        self.verible_patterns = [
            # file.sv:42:1: message [rule-name]
            re.compile(
                r'(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): '
                r'(?P<message>.+?) '
                r'\[(?P<code>[^\]]+)\]$'
            ),
        ]
        
        # Generic patterns (fallback)
        self.generic_patterns = [
            # "ERROR: message"
            re.compile(
                r'^(?P<severity>FATAL|ERROR|WARNING|INFO):\s+'
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
            # "Error: message"
            re.compile(
                r'^(?P<severity>Fatal|Error|Warning|Info):\s+'
                r'(?P<message>.+)$',
                re.IGNORECASE
            ),
        ]
        
        # Assertion patterns
        self.assertion_patterns = [
            re.compile(r'assertion\s+(?:violation|failure|failed)', re.IGNORECASE),
            re.compile(r'assert.*?failed', re.IGNORECASE),
            re.compile(r'check.*?failed', re.IGNORECASE),
        ]
        
        # License error patterns
        self.license_patterns = [
            re.compile(r'license.*?(?:error|failed|not found|expired)', re.IGNORECASE),
            re.compile(r'FLEXlm.*?error', re.IGNORECASE),
            re.compile(r'no.*?license.*?available', re.IGNORECASE),
        ]
        
        # File not found patterns
        self.file_not_found_patterns = [
            re.compile(r'(?:file|cannot|unable to).*?(?:not found|does not exist)', re.IGNORECASE),
            re.compile(r'no such file', re.IGNORECASE),
        ]
        
        # All pattern groups
        self.all_pattern_groups = [
            ('verilator', self.verilator_patterns),
            ('modelsim', self.modelsim_patterns),
            ('ghdl', self.ghdl_patterns),
            ('vcs', self.vcs_patterns),
            ('icarus', self.icarus_patterns),
            ('yosys', self.yosys_patterns),
            ('verible', self.verible_patterns),
            ('generic', self.generic_patterns),
        ]
    
    def parse(self, console_output: str) -> List[DiagnosticMessage]:
        """
        Parse console output for diagnostic messages
        
        Args:
            console_output: Console output text
        
        Returns:
            List of diagnostic messages
        """
        messages = []
        seen_messages = set()  # For deduplication
        
        for line in console_output.split('\n'):
            line = line.rstrip()
            
            if not line:
                continue
            
            # Try to parse line
            message = self._parse_line(line)
            
            if message:
                # Deduplicate
                message_key = (
                    message.severity,
                    message.message,
                    str(message.location)
                )
                
                if message_key not in seen_messages:
                    messages.append(message)
                    seen_messages.add(message_key)
        
        return messages
    
    def _parse_line(self, line: str) -> Optional[DiagnosticMessage]:
        """
        Parse a single line for diagnostic message
        
        Args:
            line: Line to parse
        
        Returns:
            DiagnosticMessage or None
        """
        # Try each pattern group
        for tool, patterns in self.all_pattern_groups:
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    return self._create_message(match, tool, line)
        
        return None
    
    def _create_message(
        self,
        match: re.Match,
        tool: str,
        raw_line: str
    ) -> DiagnosticMessage:
        """
        Create DiagnosticMessage from regex match
        
        Args:
            match: Regex match object
            tool: Tool name
            raw_line: Original line
        
        Returns:
            DiagnosticMessage
        """
        groups = match.groupdict()
        
        # Parse severity
        severity_str = groups.get('severity', 'error').lower()
        severity_map = {
            'fatal': MessageSeverity.FATAL,
            'error': MessageSeverity.ERROR,
            'warning': MessageSeverity.WARNING,
            'warn': MessageSeverity.WARNING,
            'note': MessageSeverity.INFO,
            'info': MessageSeverity.INFO,
            'sorry': MessageSeverity.ERROR,  # Icarus uses "sorry" for errors
        }
        severity = severity_map.get(severity_str, MessageSeverity.ERROR)
        
        # Parse location
        location = SourceLocation(
            file_path=groups.get('file'),
            line=int(groups['line']) if groups.get('line') else None,
            column=int(groups['col']) if groups.get('col') else None,
        )
        
        # Get message
        message = groups.get('message', '').strip()
        
        # Get error code
        code = groups.get('code')
        
        # Determine category
        category = self._categorize_message(message, severity)
        
        return DiagnosticMessage(
            severity=severity,
            category=category,
            message=message,
            location=location,
            tool=tool,
            code=code,
            raw_line=raw_line,
        )
    
    def _categorize_message(
        self,
        message: str,
        severity: MessageSeverity
    ) -> MessageCategory:
        """
        Categorize a diagnostic message
        
        Args:
            message: Message text
            severity: Message severity
        
        Returns:
            MessageCategory
        """
        message_lower = message.lower()
        
        # Check for assertions
        for pattern in self.assertion_patterns:
            if pattern.search(message):
                return MessageCategory.ASSERTION_FAILURE
        
        # Check for license errors
        for pattern in self.license_patterns:
            if pattern.search(message):
                return MessageCategory.LICENSE_ERROR
        
        # Check for file not found
        for pattern in self.file_not_found_patterns:
            if pattern.search(message):
                return MessageCategory.FILE_NOT_FOUND
        
        # Check for syntax errors
        if 'syntax' in message_lower:
            return MessageCategory.SYNTAX_ERROR
        
        # Check for timing violations
        if 'timing' in message_lower or 'setup' in message_lower or 'hold' in message_lower:
            return MessageCategory.TIMING_VIOLATION
        
        # Check for lint warnings
        if 'lint' in message_lower or 'style' in message_lower:
            return MessageCategory.LINT_WARNING
        
        # Categorize by severity
        if severity == MessageSeverity.ERROR or severity == MessageSeverity.FATAL:
            # Check if it's a compile error
            compile_keywords = ['undeclared', 'undefined', 'not found', 'unknown', 'missing']
            if any(kw in message_lower for kw in compile_keywords):
                return MessageCategory.COMPILE_ERROR
            
            return MessageCategory.RUNTIME_ERROR
        
        elif severity == MessageSeverity.WARNING:
            return MessageCategory.SIMULATOR_WARNING
        
        return MessageCategory.UNKNOWN
    
    def get_errors(self, messages: List[DiagnosticMessage]) -> List[DiagnosticMessage]:
        """Get only error messages"""
        return [
            m for m in messages
            if m.severity in [MessageSeverity.ERROR, MessageSeverity.FATAL]
        ]
    
    def get_warnings(self, messages: List[DiagnosticMessage]) -> List[DiagnosticMessage]:
        """Get only warning messages"""
        return [m for m in messages if m.severity == MessageSeverity.WARNING]
    
    def has_errors(self, messages: List[DiagnosticMessage]) -> bool:
        """Check if there are any errors"""
        return any(
            m.severity in [MessageSeverity.ERROR, MessageSeverity.FATAL]
            for m in messages
        )
    
    def get_by_category(
        self,
        messages: List[DiagnosticMessage],
        category: MessageCategory
    ) -> List[DiagnosticMessage]:
        """Get messages by category"""
        return [m for m in messages if m.category == category]


class DiagnosticSummary:
    """
    Summary of diagnostic messages
    """
    
    def __init__(self, messages: List[DiagnosticMessage]):
        """
        Initialize summary
        
        Args:
            messages: List of diagnostic messages
        """
        self.messages = messages
        
        # Count by severity
        self.fatal_count = sum(1 for m in messages if m.severity == MessageSeverity.FATAL)
        self.error_count = sum(1 for m in messages if m.severity == MessageSeverity.ERROR)
        self.warning_count = sum(1 for m in messages if m.severity == MessageSeverity.WARNING)
        self.info_count = sum(1 for m in messages if m.severity == MessageSeverity.INFO)
        
        # Count by category
        self.by_category: Dict[MessageCategory, int] = {}
        for message in messages:
            self.by_category[message.category] = self.by_category.get(message.category, 0) + 1
        
        # Count by tool
        self.by_tool: Dict[str, int] = {}
        for message in messages:
            if message.tool:
                self.by_tool[message.tool] = self.by_tool.get(message.tool, 0) + 1
        
        # Affected files
        self.affected_files: Set[str] = {
            m.location.file_path
            for m in messages
            if m.location.file_path
        }
    
    @property
    def total_count(self) -> int:
        """Total message count"""
        return len(self.messages)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return self.error_count > 0 or self.fatal_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total': self.total_count,
            'fatal': self.fatal_count,
            'errors': self.error_count,
            'warnings': self.warning_count,
            'info': self.info_count,
            'by_category': {
                cat.value: count
                for cat, count in self.by_category.items()
            },
            'by_tool': self.by_tool,
            'affected_files': list(self.affected_files),
        }
    
    def __str__(self) -> str:
        """String representation"""
        lines = [
            f"Diagnostic Summary:",
            f"  Total:    {self.total_count}",
            f"  Fatal:    {self.fatal_count}",
            f"  Errors:   {self.error_count}",
            f"  Warnings: {self.warning_count}",
            f"  Info:     {self.info_count}",
        ]
        
        if self.by_category:
            lines.append("  By category:")
            for cat, count in sorted(self.by_category.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"    {cat.value}: {count}")
        
        if self.affected_files:
            lines.append(f"  Affected files: {len(self.affected_files)}")
        
        return "\n".join(lines)


class ErrorExtractor:
    """
    Extracts key error information for test failure messages
    """
    
    @staticmethod
    def get_primary_error(messages: List[DiagnosticMessage]) -> Optional[DiagnosticMessage]:
        """
        Get the primary/root error message
        
        Args:
            messages: List of diagnostic messages
        
        Returns:
            Primary error or None
        """
        # Prioritize fatal errors
        fatal = [m for m in messages if m.severity == MessageSeverity.FATAL]
        if fatal:
            return fatal[0]
        
        # Then regular errors
        errors = [m for m in messages if m.severity == MessageSeverity.ERROR]
        if errors:
            # Prioritize certain categories
            for category in [
                MessageCategory.ASSERTION_FAILURE,
                MessageCategory.SYNTAX_ERROR,
                MessageCategory.COMPILE_ERROR,
            ]:
                category_errors = [e for e in errors if e.category == category]
                if category_errors:
                    return category_errors[0]
            
            return errors[0]
        
        return None
    
    @staticmethod
    def get_failure_summary(messages: List[DiagnosticMessage]) -> str:
        """
        Get a concise failure summary
        
        Args:
            messages: List of diagnostic messages
        
        Returns:
            Summary string
        """
        primary = ErrorExtractor.get_primary_error(messages)
        
        if not primary:
            return "Unknown error"
        
        # Build summary
        parts = []
        
        if primary.location.file_path:
            parts.append(f"in {Path(primary.location.file_path).name}")
            if primary.location.line:
                parts.append(f"line {primary.location.line}")
        
        parts.append(primary.message[:100])
        
        return " ".join(parts)


# Utility functions

def parse_console_output(output: str) -> List[DiagnosticMessage]:
    """
    Convenience function to parse console output
    
    Args:
        output: Console output text
    
    Returns:
        List of diagnostic messages
    """
    parser = ConsoleParser()
    return parser.parse(output)


def get_diagnostic_summary(output: str) -> DiagnosticSummary:
    """
    Get diagnostic summary from console output
    
    Args:
        output: Console output text
    
    Returns:
        DiagnosticSummary
    """
    messages = parse_console_output(output)
    return DiagnosticSummary(messages)


def extract_errors(output: str) -> List[str]:
    """
    Extract error messages from console output
    
    Args:
        output: Console output text
    
    Returns:
        List of error message strings
    """
    messages = parse_console_output(output)
    errors = [m for m in messages if m.severity in [MessageSeverity.ERROR, MessageSeverity.FATAL]]
    return [str(e) for e in errors]


# Example usage and testing
if __name__ == "__main__":
    # Example outputs from various tools
    examples = {
        'verilator': """
%Error: adder.sv:42:1: syntax error, unexpected IDENTIFIER
%Warning-WIDTH: adder.sv:15:8: Operator ASSIGNW expects 8 bits on the RHS, but RHS's CONST '32'h100' generates 9 bits.
%Error-PINCONNECT: top.sv:28:12: Port connection width mismatch: Expecting 8 bits but got 16 bits
        """,
        
        'modelsim': """
** Error: (vlog-2110) adder.sv(42): Illegal reference to net "data".
** Warning: (vlog-2600) [TFMPC] - Too few port connections for 'adder'.  Expected 3, found 2.
** Error: (vcom-11) Could not find work.package_name.
        """,
        
        'ghdl': """
adder.vhd:42:1:error: syntax error
adder.vhd:45:10:warning: signal "unused" is never used
ghdl:error: cannot continue due to previous errors
        """,
        
        'vcs': """
Error-[SE] Syntax error
  Following verilog source has syntax error :
  "adder.sv", 42: token is 'end'
Warning-[LCA-FEATURES-ENABLED] License usage warning
        """,
    }
    
    parser = ConsoleParser()
    
    for tool, output in examples.items():
        print(f"\n{'=' * 60}")
        print(f"Parsing {tool.upper()} output:")
        print(f"{'=' * 60}")
        
        messages = parser.parse(output)
        
        for msg in messages:
            print(f"{msg.severity.value.upper():8} [{msg.category.value}] {msg.message[:60]}")
            if msg.location.file_path:
                print(f"         at {msg.location}")
        
        # Summary
        summary = DiagnosticSummary(messages)
        print(f"\n{summary}")
