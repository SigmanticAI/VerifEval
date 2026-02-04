"""
Output handling for test execution

This module provides utilities for:
- Real-time output streaming
- Output filtering and formatting
- Progress indicators
- Colored output
- Log file management

Author: TB Eval Team
Version: 0.1.0
"""

import sys
import re
from typing import Optional, Callable, List, TextIO
from enum import Enum
from pathlib import Path
from datetime import datetime


class OutputLevel(Enum):
    """Output verbosity level"""
    MINIMAL = "minimal"
    NORMAL = "normal"
    VERBOSE = "verbose"
    DEBUG = "debug"


class ColorCode:
    """ANSI color codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


class OutputFormatter:
    """
    Formats output with colors and styles
    
    Features:
    - Colored output with disable option
    - Status symbols (✓, ✗, ⚠, etc.)
    - Progress indicators
    - Timestamp prefixes
    """
    
    def __init__(self, use_color: bool = True):
        """
        Initialize formatter
        
        Args:
            use_color: Whether to use colored output
        """
        self.use_color = use_color and self._supports_color()
    
    @staticmethod
    def _supports_color() -> bool:
        """Check if terminal supports color"""
        # Check if stdout is a TTY
        if not hasattr(sys.stdout, 'isatty'):
            return False
        if not sys.stdout.isatty():
            return False
        
        # Check TERM environment variable
        import os
        term = os.environ.get('TERM', '')
        if term == 'dumb':
            return False
        
        return True
    
    def colorize(self, text: str, color: str) -> str:
        """
        Apply color to text
        
        Args:
            text: Text to colorize
            color: Color code from ColorCode
        
        Returns:
            Colored text (or plain if colors disabled)
        """
        if not self.use_color:
            return text
        return f"{color}{text}{ColorCode.RESET}"
    
    def success(self, text: str) -> str:
        """Format success message (green)"""
        return self.colorize(text, ColorCode.GREEN)
    
    def error(self, text: str) -> str:
        """Format error message (red)"""
        return self.colorize(text, ColorCode.RED)
    
    def warning(self, text: str) -> str:
        """Format warning message (yellow)"""
        return self.colorize(text, ColorCode.YELLOW)
    
    def info(self, text: str) -> str:
        """Format info message (cyan)"""
        return self.colorize(text, ColorCode.CYAN)
    
    def dim(self, text: str) -> str:
        """Format dim text"""
        return self.colorize(text, ColorCode.DIM)
    
    def bold(self, text: str) -> str:
        """Format bold text"""
        if not self.use_color:
            return text
        return f"{ColorCode.BOLD}{text}{ColorCode.RESET}"
    
    def status_symbol(self, status: str) -> str:
        """
        Get colored status symbol
        
        Args:
            status: Status string (passed, failed, error, etc.)
        
        Returns:
            Colored symbol
        """
        symbols = {
            'passed': ('✓', ColorCode.GREEN),
            'failed': ('✗', ColorCode.RED),
            'error': ('⚠', ColorCode.YELLOW),
            'skipped': ('○', ColorCode.DIM),
            'timeout': ('⏱', ColorCode.YELLOW),
            'crashed': ('💥', ColorCode.RED),
            'running': ('⟳', ColorCode.CYAN),
            'pending': ('⋯', ColorCode.DIM),
        }
        
        symbol, color = symbols.get(status.lower(), ('?', ColorCode.WHITE))
        return self.colorize(symbol, color)
    
    def progress_bar(
        self,
        current: int,
        total: int,
        width: int = 40,
        prefix: str = "",
        suffix: str = "",
    ) -> str:
        """
        Create progress bar
        
        Args:
            current: Current progress
            total: Total items
            width: Bar width in characters
            prefix: Text before bar
            suffix: Text after bar
        
        Returns:
            Formatted progress bar string
        """
        if total == 0:
            percent = 100.0
        else:
            percent = (current / total) * 100
        
        filled = int(width * current // total) if total > 0 else width
        bar = '█' * filled + '░' * (width - filled)
        
        result = f"{prefix}|{bar}| {current}/{total} ({percent:.1f}%) {suffix}"
        
        if self.use_color:
            # Color the filled portion
            result = result.replace('█', self.colorize('█', ColorCode.CYAN))
            result = result.replace('░', self.colorize('░', ColorCode.DIM))
        
        return result
    
    def format_duration(self, ms: float) -> str:
        """
        Format duration in human-readable form
        
        Args:
            ms: Duration in milliseconds
        
        Returns:
            Formatted duration (e.g., "1.23s", "125ms")
        """
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.2f}s"
        else:
            minutes = int(ms / 60000)
            seconds = (ms % 60000) / 1000
            return f"{minutes}m {seconds:.1f}s"
    
    def format_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")


class StreamingOutputHandler:
    """
    Handles real-time output streaming with filtering
    
    Features:
    - Real-time output streaming
    - Output level filtering
    - Pattern-based filtering (warnings, errors)
    - Line buffering
    - Multiple output destinations
    """
    
    def __init__(
        self,
        level: OutputLevel = OutputLevel.NORMAL,
        formatter: Optional[OutputFormatter] = None,
        output_stream: TextIO = sys.stdout,
        show_timestamps: bool = False,
    ):
        """
        Initialize streaming handler
        
        Args:
            level: Output verbosity level
            formatter: Output formatter (creates default if None)
            output_stream: Where to write output
            show_timestamps: Whether to show timestamps
        """
        self.level = level
        self.formatter = formatter or OutputFormatter()
        self.output_stream = output_stream
        self.show_timestamps = show_timestamps
        
        # Line buffer for incomplete lines
        self.line_buffer = ""
        
        # Patterns for highlighting
        self.error_patterns = [
            re.compile(r'error:', re.IGNORECASE),
            re.compile(r'fatal:', re.IGNORECASE),
            re.compile(r'exception:', re.IGNORECASE),
        ]
        
        self.warning_patterns = [
            re.compile(r'warning:', re.IGNORECASE),
            re.compile(r'warn:', re.IGNORECASE),
        ]
    
    def write(self, text: str) -> None:
        """
        Write text to output
        
        Args:
            text: Text to write
        """
        # Add to buffer
        self.line_buffer += text
        
        # Process complete lines
        while '\n' in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split('\n', 1)
            self._write_line(line)
    
    def _write_line(self, line: str) -> None:
        """Write a complete line with formatting"""
        # Skip empty lines in minimal mode
        if self.level == OutputLevel.MINIMAL and not line.strip():
            return
        
        # Apply formatting based on content
        formatted_line = self._format_line(line)
        
        # Add timestamp if requested
        if self.show_timestamps:
            timestamp = self.formatter.format_timestamp()
            formatted_line = f"[{timestamp}] {formatted_line}"
        
        # Write to stream
        self.output_stream.write(formatted_line + '\n')
        self.output_stream.flush()
    
    def _format_line(self, line: str) -> str:
        """Apply formatting to line based on content"""
        # Check for errors
        for pattern in self.error_patterns:
            if pattern.search(line):
                return self.formatter.error(line)
        
        # Check for warnings
        for pattern in self.warning_patterns:
            if pattern.search(line):
                return self.formatter.warning(line)
        
        # Check for test result indicators
        if 'PASS' in line.upper() or '✓' in line:
            return self.formatter.success(line)
        elif 'FAIL' in line.upper() or '✗' in line:
            return self.formatter.error(line)
        
        # Return as-is
        return line
    
    def flush(self) -> None:
        """Flush any remaining buffered output"""
        if self.line_buffer:
            self._write_line(self.line_buffer)
            self.line_buffer = ""
        self.output_stream.flush()


class MultiOutputHandler:
    """
    Write output to multiple destinations
    
    Useful for writing to console and log file simultaneously.
    """
    
    def __init__(self):
        """Initialize multi-output handler"""
        self.handlers: List[StreamingOutputHandler] = []
    
    def add_handler(self, handler: StreamingOutputHandler) -> None:
        """
        Add output handler
        
        Args:
            handler: Handler to add
        """
        self.handlers.append(handler)
    
    def write(self, text: str) -> None:
        """
        Write to all handlers
        
        Args:
            text: Text to write
        """
        for handler in self.handlers:
            handler.write(text)
    
    def flush(self) -> None:
        """Flush all handlers"""
        for handler in self.handlers:
            handler.flush()


class TestOutputLogger:
    """
    Manages test output logging
    
    Creates log files for test output and manages log organization.
    """
    
    def __init__(self, logs_directory: Path):
        """
        Initialize test output logger
        
        Args:
            logs_directory: Root directory for logs
        """
        self.logs_directory = Path(logs_directory)
        self.logs_directory.mkdir(parents=True, exist_ok=True)
    
    def get_log_path(self, test_name: str, outcome: Optional[str] = None) -> Path:
        """
        Get log file path for test
        
        Args:
            test_name: Test name
            outcome: Test outcome (for organization)
        
        Returns:
            Path to log file
        """
        # Sanitize test name for filename
        safe_name = re.sub(r'[^\w\-_\.]', '_', test_name)
        
        # Organize by outcome if provided
        if outcome:
            log_dir = self.logs_directory / outcome
        else:
            log_dir = self.logs_directory
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{safe_name}_{timestamp}.log"
        
        return log_file
    
    def create_log_file(
        self,
        test_name: str,
        outcome: Optional[str] = None
    ) -> TextIO:
        """
        Create and open log file for test
        
        Args:
            test_name: Test name
            outcome: Test outcome
        
        Returns:
            Open file handle
        """
        log_path = self.get_log_path(test_name, outcome)
        
        # Write header
        log_file = open(log_path, 'w')
        log_file.write(f"{'=' * 80}\n")
        log_file.write(f"Test: {test_name}\n")
        log_file.write(f"Started: {datetime.now().isoformat()}\n")
        log_file.write(f"{'=' * 80}\n\n")
        log_file.flush()
        
        return log_file
