"""
Track Handlers for Step 3: Build & Orchestrate
==============================================

This module provides track-specific build and execution handlers:

- Track A (CocoTBTrack): Python-based testbenches (CocoTB, PyUVM)
  - Uses Verilator with --coverage
  - Generates Makefile for CocoTB execution
  - Direct Python test execution

- Track B (HDLTrack): HDL-based testbenches (VUnit, SV, VHDL, UVM)
  - Uses VUnit orchestration
  - Supports Verilator, GHDL, Questa
  - Special UVM handling with Questa

Usage:
    from build_orchestrate.tracks import get_track_handler
    
    track = get_track_handler(route_info, build_config, submission_dir)
    
    # Validate prerequisites
    issues = track.validate_prerequisites()
    
    # Run build pipeline
    build_result = track.build()
    
    # Get execution command for Step 4
    exec_cmd = track.get_execution_command()
"""

from .base import BaseTrack, TrackBuildResult, TrackCapabilities
from .track_a import CocoTBTrack
from .track_b import HDLTrack

__all__ = [
    # Base
    "BaseTrack",
    "TrackBuildResult",
    "TrackCapabilities",
    # Implementations
    "CocoTBTrack",
    "HDLTrack",
    # Factory
    "get_track_handler",
    "TrackType",
]


class TrackType:
    """Track type constants matching Step 2 Track enum"""
    A = "A"  # CocoTB/PyUVM
    B = "B"  # VUnit/HDL/UVM
    C = "C"  # Commercial only (future)


def get_track_handler(
    route_info,  # RouteInfo from config.py
    build_config,  # BuildConfig from models.py
    submission_dir,
) -> BaseTrack:
    """
    Factory function to get appropriate track handler
    
    Args:
        route_info: Routing information from Step 2
        build_config: Build configuration
        submission_dir: Path to submission directory
    
    Returns:
        Appropriate track handler instance
    
    Raises:
        ValueError: If track type is not supported
    """
    from pathlib import Path
    
    submission_dir = Path(submission_dir)
    track = route_info.track if hasattr(route_info, 'track') else route_info.get('track', 'B')
    
    if track == TrackType.A:
        return CocoTBTrack(
            submission_dir=submission_dir,
            route_info=route_info,
            build_config=build_config,
        )
    elif track in [TrackType.B, TrackType.C]:
        return HDLTrack(
            submission_dir=submission_dir,
            route_info=route_info,
            build_config=build_config,
        )
    else:
        raise ValueError(f"Unsupported track type: {track}")
