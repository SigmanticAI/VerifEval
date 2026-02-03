"""
VUnit Project Generator
=======================

Generates VUnit run.py scripts from templates based on:
- Testbench type (CocoTB, UVM, VUnit native, plain HDL)
- Simulator (Questa, Verilator, GHDL)
- Project configuration

Author: TB Eval Team
Version: 0.1.0
"""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ..models import BuildConfig, SimulatorType, CoverageConfig
from ..config import RouteInfo


@dataclass
class GenerationConfig:
    """
    Configuration for run.py generation
    
    Attributes:
        tb_type: Testbench type (cocotb, uvm_sv, vunit, systemverilog, vhdl)
        track: Execution track (A or B)
        simulator: Target simulator
        dut_files: List of DUT source files
        tb_files: List of testbench files
        top_module: Top module name
        libraries: Library configuration
        coverage_enabled: Enable coverage collection
        uvm_tests: List of UVM test names (for UVM projects)
        cocotb_module: CocoTB module name (for CocoTB projects)
        extra_compile_options: Additional compile options
        extra_sim_options: Additional simulation options
        output_path: VUnit output path
    """
    tb_type: str = "systemverilog"
    track: str = "B"
    simulator: SimulatorType = SimulatorType.QUESTA
    dut_files: List[str] = field(default_factory=list)
    tb_files: List[str] = field(default_factory=list)
    top_module: Optional[str] = None
    libraries: Dict[str, List[str]] = field(default_factory=lambda: {"work": []})
    coverage_enabled: bool = True
    uvm_tests: List[str] = field(default_factory=list)
    cocotb_module: Optional[str] = None
    extra_compile_options: Dict[str, List[str]] = field(default_factory=dict)
    extra_sim_options: Dict[str, List[str]] = field(default_factory=dict)
    output_path: str = "vunit_out"
    
    @classmethod
    def from_route_and_build(
        cls,
        route: RouteInfo,
        build_config: BuildConfig
    ) -> "GenerationConfig":
        """Create GenerationConfig from route.json and build config"""
        return cls(
            tb_type=route.tb_type,
            track=route.track,
            simulator=build_config.simulator,
            dut_files=route.dut_files,
            tb_files=route.tb_files,
            top_module=route.top_module,
            coverage_enabled=build_config.coverage.enabled,
            output_path=f"{build_config.output_dir}/vunit_out",
        )


@dataclass
class GeneratedProject:
    """
    Result of project generation
    
    Attributes:
        run_script: Path to generated run.py
        makefile: Path to generated Makefile (for CocoTB)
        support_files: List of additional generated files
        template_used: Name of template used
        generation_time: When generated
        warnings: Generation warnings
    """
    run_script: Path
    makefile: Optional[Path] = None
    support_files: List[Path] = field(default_factory=list)
    template_used: str = ""
    generation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_script": str(self.run_script),
            "makefile": str(self.makefile) if self.makefile else None,
            "support_files": [str(f) for f in self.support_files],
            "template_used": self.template_used,
            "generation_time": self.generation_time,
            "warnings": self.warnings,
        }


class TemplateManager:
    """
    Manages Jinja2 templates for run.py generation
    
    Templates are loaded from the templates/ directory and
    rendered with project-specific context.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template manager
        
        Args:
            templates_dir: Path to templates directory (default: ./templates)
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2 is required for template generation. "
                "Install with: pip install jinja2"
            )
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        
        # Register custom filters
        self._register_filters()
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters"""
        self.env.filters['quote'] = lambda s: f'"{s}"'
        self.env.filters['path_join'] = lambda parts: '/'.join(parts)
        self.env.filters['to_python_list'] = self._to_python_list
        self.env.filters['basename'] = lambda p: Path(p).name
        self.env.filters['stem'] = lambda p: Path(p).stem
    
    def _to_python_list(self, items: List[str]) -> str:
        """Convert list to Python list literal"""
        if not items:
            return "[]"
        quoted = [f'"{item}"' for item in items]
        return "[\n        " + ",\n        ".join(quoted) + ",\n    ]"
    
    def get_template(self, template_name: str):
        """Get a template by name"""
        return self.env.get_template(template_name)
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with context
        
        Args:
            template_name: Name of template file
            context: Template context variables
        
        Returns:
            Rendered template string
        """
        template = self.get_template(template_name)
        return template.render(**context)
    
    def get_template_for_tb_type(self, tb_type: str) -> str:
        """
        Get appropriate template name for testbench type
        
        Args:
            tb_type: Testbench type (cocotb, uvm_sv, vunit, etc.)
        
        Returns:
            Template filename
        """
        mapping = {
            "cocotb": "cocotb_run.py.j2",
            "pyuvm": "cocotb_run.py.j2",  # PyUVM uses similar setup
            "uvm_sv": "uvm_run.py.j2",
            "vunit": "base_run.py.j2",
            "systemverilog": "sv_run.py.j2",
            "vhdl": "vhdl_run.py.j2",
        }
        
        return mapping.get(tb_type, "base_run.py.j2")


class VUnitProjectGenerator:
    """
    Generates VUnit project files from templates
    
    Usage:
        generator = VUnitProjectGenerator(submission_dir)
        result = generator.generate(route_info, build_config)
        
        print(f"Generated: {result.run_script}")
    """
    
    def __init__(self, submission_dir: Path):
        """
        Initialize generator
        
        Args:
            submission_dir: Path to submission directory
        """
        self.submission_dir = Path(submission_dir)
        self.template_manager = TemplateManager()
    
    def generate(
        self,
        route: RouteInfo,
        build_config: BuildConfig,
        output_dir: Optional[Path] = None
    ) -> GeneratedProject:
        """
        Generate VUnit project files
        
        Args:
            route: Route information from Step 2
            build_config: Build configuration
            output_dir: Output directory (default: submission_dir/.tbeval)
        
        Returns:
            GeneratedProject with paths to generated files
        """
        # Create generation config
        gen_config = GenerationConfig.from_route_and_build(route, build_config)
        
        # Determine output directory
        if output_dir is None:
            output_dir = self.submission_dir / build_config.output_dir
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create vunit_project subdirectory
        project_dir = output_dir / "vunit_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Select template based on TB type
        template_name = self.template_manager.get_template_for_tb_type(gen_config.tb_type)
        
        # Build template context
        context = self._build_context(gen_config, build_config, project_dir)
        
        # Render template
        run_py_content = self.template_manager.render(template_name, context)
        
        # Write run.py
        run_py_path = project_dir / "run.py"
        run_py_path.write_text(run_py_content)
        
        # Make executable on Unix
        if os.name != 'nt':
            run_py_path.chmod(0o755)
        
        # Create result
        result = GeneratedProject(
            run_script=run_py_path,
            template_used=template_name,
        )
        
        # Generate additional files if needed
        if gen_config.tb_type in ["cocotb", "pyuvm"]:
            makefile_path = self._generate_cocotb_makefile(gen_config, project_dir)
            result.makefile = makefile_path
            result.support_files.append(makefile_path)
        
        return result
    
    def _build_context(
        self,
        gen_config: GenerationConfig,
        build_config: BuildConfig,
        project_dir: Path
    ) -> Dict[str, Any]:
        """Build template context"""
        # Calculate relative paths from project_dir to submission_dir
        rel_path = os.path.relpath(self.submission_dir, project_dir)
        
        # Process file paths
        dut_files = [f"{rel_path}/{f}" for f in gen_config.dut_files]
        tb_files = [f"{rel_path}/{f}" for f in gen_config.tb_files]
        
        # Separate files by type
        sv_files = [f for f in dut_files + tb_files if Path(f).suffix in ['.sv', '.v', '.svh', '.vh']]
        vhdl_files = [f for f in dut_files + tb_files if Path(f).suffix in ['.vhd', '.vhdl']]
        
        # Get simulator name for VUnit
        simulator_name = self._get_vunit_simulator_name(build_config.simulator)
        
        context = {
            # Basic info
            "project_name": build_config.project_name,
            "tb_type": gen_config.tb_type,
            "track": gen_config.track,
            "generation_time": datetime.now().isoformat(),
            "framework_version": "0.1.0",
            
            # Paths
            "submission_dir": str(self.submission_dir),
            "rel_path": rel_path,
            "output_path": gen_config.output_path,
            
            # Files
            "dut_files": dut_files,
            "tb_files": tb_files,
            "sv_files": sv_files,
            "vhdl_files": vhdl_files,
            "all_files": dut_files + tb_files,
            
            # Module info
            "top_module": gen_config.top_module,
            "libraries": gen_config.libraries,
            
            # Simulator
            "simulator": build_config.simulator.value,
            "simulator_name": simulator_name,
            
            # Coverage
            "coverage_enabled": gen_config.coverage_enabled,
            "coverage_types": [t.value for t in build_config.coverage.types],
            
            # Simulator-specific options
            "compile_options": self._get_compile_options(build_config),
            "sim_options": self._get_sim_options(build_config),
            
            # UVM specific
            "uvm_tests": gen_config.uvm_tests,
            "uvm_verbosity": getattr(build_config.simulator_config, 'uvm_verbosity', 'UVM_MEDIUM')
                if build_config.simulator_config else 'UVM_MEDIUM',
            
            # CocoTB specific
            "cocotb_module": gen_config.cocotb_module or self._detect_cocotb_module(gen_config.tb_files),
        }
        
        return context
    
    def _get_vunit_simulator_name(self, simulator: SimulatorType) -> str:
        """Get simulator name as recognized by VUnit"""
        mapping = {
            SimulatorType.QUESTA: "modelsim",
            SimulatorType.MODELSIM: "modelsim",
            SimulatorType.GHDL: "ghdl",
            SimulatorType.VERILATOR: "modelsim",  # VUnit doesn't directly support Verilator
            SimulatorType.ICARUS: "modelsim",
        }
        return mapping.get(simulator, "modelsim")
    
    def _get_compile_options(self, build_config: BuildConfig) -> Dict[str, List[str]]:
        """Get compile options for template"""
        options = {}
        
        if build_config.simulator in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            options["vlog_flags"] = [
                "-sv",
                "+acc=r",
                "-timescale", "1ns/1ps",
            ]
            options["vcom_flags"] = [
                "-2008",
            ]
            
            # Add coverage flags
            if build_config.coverage.enabled:
                options["vlog_flags"].extend(["+cover=bcesft"])
                options["vcom_flags"].extend(["+cover=bcesft"])
        
        elif build_config.simulator == SimulatorType.GHDL:
            options["ghdl_flags"] = [
                "--std=08",
            ]
        
        return options
    
    def _get_sim_options(self, build_config: BuildConfig) -> Dict[str, List[str]]:
        """Get simulation options for template"""
        options = {}
        
        if build_config.simulator in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            options["vsim_flags"] = [
                "-voptargs=+acc",
            ]
            
            if build_config.coverage.enabled:
                options["vsim_flags"].extend([
                    "-coverage",
                ])
        
        return options
    
    def _detect_cocotb_module(self, tb_files: List[str]) -> str:
        """Detect CocoTB module name from test files"""
        for tb_file in tb_files:
            if tb_file.endswith('.py'):
                # Use file stem as module name
                return Path(tb_file).stem
        return "test_module"
    
    def _generate_cocotb_makefile(
        self,
        gen_config: GenerationConfig,
        project_dir: Path
    ) -> Path:
        """Generate Makefile for CocoTB execution"""
        # Calculate paths
        rel_path = os.path.relpath(self.submission_dir, project_dir)
        
        # Get DUT files (Verilog/SystemVerilog)
        verilog_sources = [
            f"{rel_path}/{f}" for f in gen_config.dut_files
            if Path(f).suffix in ['.sv', '.v']
        ]
        
        makefile_content = f'''# Auto-generated CocoTB Makefile
# Generated by TB Eval Framework

# Simulation configuration
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = {" ".join(verilog_sources)}

# Toplevel module
TOPLEVEL = {gen_config.top_module or "top"}

# Python test module
MODULE = {gen_config.cocotb_module or "test_module"}

# Coverage settings
EXTRA_ARGS += --coverage

# Include cocotb's make rules
include $(shell cocotb-config --makefiles)/Makefile.sim

# Clean target
clean::
\t-rm -rf __pycache__ results.xml *.vcd
'''
        
        makefile_path = project_dir / "Makefile"
        makefile_path.write_text(makefile_content)
        
        return makefile_path


# =============================================================================
# STANDALONE USAGE
# =============================================================================

def generate_vunit_project(
    submission_dir: Path,
    route_json_path: Path,
    output_dir: Optional[Path] = None
) -> GeneratedProject:
    """
    Convenience function to generate VUnit project
    
    Args:
        submission_dir: Path to submission directory
        route_json_path: Path to route.json from Step 2
        output_dir: Output directory (optional)
    
    Returns:
        GeneratedProject with paths to generated files
    """
    from ..config import BuildConfigManager
    
    # Load configuration
    config_manager = BuildConfigManager(submission_dir)
    build_config = config_manager.load(route_json_path)
    route_info = config_manager.get_route_info()
    
    if not route_info:
        raise ValueError(f"Could not load route.json from {route_json_path}")
    
    # Generate project
    generator = VUnitProjectGenerator(submission_dir)
    return generator.generate(route_info, build_config, output_dir)
