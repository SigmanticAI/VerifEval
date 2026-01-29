"""
Configuration management for Step 2
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from .models import ProjectConfig


class ConfigManager:
    """Manages configuration loading and defaults"""
    
    DEFAULT_CONFIG_NAMES = [
        ".tbeval.yaml",
        ".tbeval.yml", 
        ".tbeval.json",
        "tbeval_config.yaml",
        "tbeval_config.yml"
    ]
    
    @staticmethod
    def find_config_file(search_dir: Path) -> Optional[Path]:
        """Find configuration file in directory"""
        for name in ConfigManager.DEFAULT_CONFIG_NAMES:
            config_path = search_dir / name
            if config_path.exists():
                return config_path
        return None
    
    @staticmethod
    def load_config(config_path: Optional[Path] = None, 
                   search_dir: Optional[Path] = None) -> ProjectConfig:
        """
        Load configuration from file or use defaults
        
        Priority:
        1. Explicit config_path
        2. Config file in search_dir
        3. Config file in current directory
        4. Default configuration
        """
        # Try explicit path first
        if config_path and config_path.exists():
            return ConfigManager._load_from_file(config_path)
        
        # Try search directory
        if search_dir:
            found_config = ConfigManager.find_config_file(search_dir)
            if found_config:
                return ConfigManager._load_from_file(found_config)
        
        # Try current directory
        found_config = ConfigManager.find_config_file(Path.cwd())
        if found_config:
            return ConfigManager._load_from_file(found_config)
        
        # Return defaults
        return ProjectConfig()
    
    @staticmethod
    def _load_from_file(config_path: Path) -> ProjectConfig:
        """Load configuration from file"""
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path.suffix}")
        
        return ProjectConfig.from_dict(data)
    
    @staticmethod
    def create_default_config(output_path: Path) -> None:
        """Create a default configuration file"""
        default_config = {
            "project_name": "my_project",
            "quality_gate_mode": "advisory",
            "fail_on_critical_errors": True,
            "fail_on_syntax_errors": True,
            "fail_on_lint_warnings": False,
            "fail_on_style_issues": False,
            "verible_rules_file": None,
            "verible_waiver_file": None,
            "questa_path": None,  # Auto-detect from PATH or specify explicit path
            "questa_license_server": None,  # e.g., "1234@license-server.company.com"
            "questa_args": [],  # Additional arguments to vsim
            "preferred_simulator": "questa",  # updated from verilator
            "enable_uvm_detection": True,
            "dut_directories": ["rtl", "src", "design"],
            "tb_directories": ["tb", "testbench", "test"]
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        print(f"Created default configuration: {output_path}")
