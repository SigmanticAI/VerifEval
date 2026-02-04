"""
Process management for test execution

This module handles:
- Subprocess execution with timeouts
- Output streaming and capture
- Resource monitoring
- Graceful termination (SIGTERM → SIGKILL)
- Process result collection

Author: TB Eval Team
Version: 0.1.0
"""

import asyncio
import os
import signal
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import psutil
import subprocess
from datetime import datetime

from ..models import ProcessResult, CapturedOutput


class ProcessManager:
    """
    Manages subprocess execution with advanced features
    
    Features:
    - Timeout with graceful shutdown (SIGTERM → SIGKILL)
    - Real-time output streaming
    - Output size limits and truncation
    - Resource monitoring (memory, CPU)
    - Environment variable management
    - Working directory handling
    """
    
    def __init__(
        self,
        max_output_size_mb: int = 50,
        stream_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize process manager
        
        Args:
            max_output_size_mb: Maximum output size before truncation
            stream_callback: Optional callback for real-time output streaming
        """
        self.max_output_size_bytes = max_output_size_mb * 1024 * 1024
        self.stream_callback = stream_callback
    
    async def run(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[float] = None,
        grace_period_seconds: float = 10.0,
        log_file: Optional[Path] = None,
    ) -> ProcessResult:
        """
        Execute command with timeout and monitoring
        
        Args:
            command: Command and arguments to execute
            cwd: Working directory
            env: Environment variables (merged with os.environ)
            timeout_seconds: Timeout in seconds (None = no timeout)
            grace_period_seconds: Grace period between SIGTERM and SIGKILL
            log_file: Optional path to save full output
        
        Returns:
            ProcessResult with execution details
        """
        start_time = time.time()
        
        # Prepare environment
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        
        # Prepare log file
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_file, 'w')
        else:
            log_handle = None
        
        # Create output handler
        output_handler = OutputHandler(
            max_size_bytes=self.max_output_size_bytes,
            stream_callback=self.stream_callback,
            log_handle=log_handle,
        )
        
        # Execute process
        try:
            if timeout_seconds:
                result = await self._run_with_timeout(
                    command=command,
                    cwd=cwd,
                    env=exec_env,
                    timeout_seconds=timeout_seconds,
                    grace_period_seconds=grace_period_seconds,
                    output_handler=output_handler,
                )
            else:
                result = await self._run_without_timeout(
                    command=command,
                    cwd=cwd,
                    env=exec_env,
                    output_handler=output_handler,
                )
        
        finally:
            if log_handle:
                log_handle.close()
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Build ProcessResult
        captured_output = output_handler.get_captured_output()
        if log_file:
            captured_output.log_file = str(log_file)
        
        return ProcessResult(
            command=command,
            exit_code=result['exit_code'],
            output=captured_output,
            duration_ms=duration_ms,
            timed_out=result.get('timed_out', False),
            killed=result.get('killed', False),
            signal=result.get('signal'),
            peak_memory_mb=result.get('peak_memory_mb'),
            peak_cpu_percent=result.get('peak_cpu_percent'),
        )
    
    async def _run_without_timeout(
        self,
        command: List[str],
        cwd: Optional[Path],
        env: Dict[str, str],
        output_handler: 'OutputHandler',
    ) -> Dict[str, Any]:
        """Run command without timeout"""
        
        # Start process
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        
        # Monitor process
        monitor_task = asyncio.create_task(
            self._monitor_process(process.pid)
        )
        
        # Stream output
        await asyncio.gather(
            output_handler.stream_stdout(process.stdout),
            output_handler.stream_stderr(process.stderr),
        )
        
        # Wait for completion
        exit_code = await process.wait()
        
        # Get monitoring results
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        monitoring_data = getattr(monitor_task, 'result_data', {})
        
        return {
            'exit_code': exit_code,
            'timed_out': False,
            'killed': False,
            'peak_memory_mb': monitoring_data.get('peak_memory_mb'),
            'peak_cpu_percent': monitoring_data.get('peak_cpu_percent'),
        }
    
    async def _run_with_timeout(
        self,
        command: List[str],
        cwd: Optional[Path],
        env: Dict[str, str],
        timeout_seconds: float,
        grace_period_seconds: float,
        output_handler: 'OutputHandler',
    ) -> Dict[str, Any]:
        """Run command with timeout"""
        
        # Start process
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        
        # Monitor process
        monitor_task = asyncio.create_task(
            self._monitor_process(process.pid)
        )
        
        # Stream output
        output_task = asyncio.create_task(
            asyncio.gather(
                output_handler.stream_stdout(process.stdout),
                output_handler.stream_stderr(process.stderr),
            )
        )
        
        # Wait with timeout
        try:
            exit_code = await asyncio.wait_for(
                process.wait(),
                timeout=timeout_seconds
            )
            
            # Normal completion
            await output_task  # Ensure output is fully captured
            
            monitor_task.cancel()
            monitoring_data = getattr(monitor_task, 'result_data', {})
            
            return {
                'exit_code': exit_code,
                'timed_out': False,
                'killed': False,
                'peak_memory_mb': monitoring_data.get('peak_memory_mb'),
                'peak_cpu_percent': monitoring_data.get('peak_cpu_percent'),
            }
        
        except asyncio.TimeoutError:
            # Timeout - graceful shutdown
            return await self._handle_timeout(
                process=process,
                grace_period_seconds=grace_period_seconds,
                output_task=output_task,
                monitor_task=monitor_task,
            )
    
    async def _handle_timeout(
        self,
        process: asyncio.subprocess.Process,
        grace_period_seconds: float,
        output_task: asyncio.Task,
        monitor_task: asyncio.Task,
    ) -> Dict[str, Any]:
        """Handle process timeout with graceful shutdown"""
        
        # Send SIGTERM
        try:
            process.terminate()
        except ProcessLookupError:
            pass  # Already dead
        
        # Wait grace period
        try:
            exit_code = await asyncio.wait_for(
                process.wait(),
                timeout=grace_period_seconds
            )
            
            # Terminated gracefully
            signal_num = signal.SIGTERM
        
        except asyncio.TimeoutError:
            # Force kill with SIGKILL
            try:
                process.kill()
            except ProcessLookupError:
                pass
            
            exit_code = await process.wait()
            signal_num = signal.SIGKILL
        
        # Ensure output is captured
        try:
            await asyncio.wait_for(output_task, timeout=5.0)
        except asyncio.TimeoutError:
            output_task.cancel()
        
        # Get monitoring data
        monitor_task.cancel()
        monitoring_data = getattr(monitor_task, 'result_data', {})
        
        return {
            'exit_code': exit_code,
            'timed_out': True,
            'killed': True,
            'signal': signal_num,
            'peak_memory_mb': monitoring_data.get('peak_memory_mb'),
            'peak_cpu_percent': monitoring_data.get('peak_cpu_percent'),
        }
    
    async def _monitor_process(self, pid: int):
        """Monitor process resource usage"""
        try:
            process = psutil.Process(pid)
            
            peak_memory_mb = 0.0
            peak_cpu_percent = 0.0
            
            while True:
                try:
                    # Get memory usage
                    mem_info = process.memory_info()
                    memory_mb = mem_info.rss / (1024 * 1024)
                    peak_memory_mb = max(peak_memory_mb, memory_mb)
                    
                    # Get CPU usage
                    cpu_percent = process.cpu_percent(interval=0.1)
                    peak_cpu_percent = max(peak_cpu_percent, cpu_percent)
                    
                    # Store results
                    asyncio.current_task().result_data = {
                        'peak_memory_mb': peak_memory_mb,
                        'peak_cpu_percent': peak_cpu_percent,
                    }
                    
                    await asyncio.sleep(0.5)
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        except Exception:
            pass  # Monitoring is best-effort


class OutputHandler:
    """
    Handles process output capture and streaming
    
    Features:
    - Separate stdout/stderr capture
    - Combined output in execution order
    - Size limits with truncation
    - Real-time streaming to callback
    - File logging
    """
    
    def __init__(
        self,
        max_size_bytes: int,
        stream_callback: Optional[Callable[[str], None]] = None,
        log_handle: Optional[Any] = None,
    ):
        self.max_size_bytes = max_size_bytes
        self.stream_callback = stream_callback
        self.log_handle = log_handle
        
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []
        self.combined_lines: List[str] = []
        
        self.total_bytes = 0
        self.truncated = False
    
    async def stream_stdout(self, stream):
        """Stream stdout"""
        if stream is None:
            return
        
        async for line in stream:
            line_str = line.decode('utf-8', errors='replace')
            self._add_line(line_str, 'stdout')
    
    async def stream_stderr(self, stream):
        """Stream stderr"""
        if stream is None:
            return
        
        async for line in stream:
            line_str = line.decode('utf-8', errors='replace')
            self._add_line(line_str, 'stderr')
    
    def _add_line(self, line: str, source: str):
        """Add line to buffers"""
        line_bytes = len(line.encode('utf-8'))
        
        # Check size limit
        if self.total_bytes + line_bytes > self.max_size_bytes:
            if not self.truncated:
                truncation_msg = "\n[... OUTPUT TRUNCATED - SIZE LIMIT EXCEEDED ...]\n"
                self.combined_lines.append(truncation_msg)
                if self.log_handle:
                    self.log_handle.write(truncation_msg)
                self.truncated = True
            return
        
        self.total_bytes += line_bytes
        
        # Add to appropriate buffer
        if source == 'stdout':
            self.stdout_lines.append(line)
        else:
            self.stderr_lines.append(line)
        
        self.combined_lines.append(line)
        
        # Stream to callback
        if self.stream_callback:
            self.stream_callback(line)
        
        # Write to log file
        if self.log_handle:
            self.log_handle.write(line)
            self.log_handle.flush()
    
    def get_captured_output(self) -> CapturedOutput:
        """Get captured output"""
        return CapturedOutput(
            stdout=''.join(self.stdout_lines),
            stderr=''.join(self.stderr_lines),
            combined=''.join(self.combined_lines),
            truncated=self.truncated,
            size_bytes=self.total_bytes,
        )
