"""
Manifest file parsing
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import yaml


class ManifestParser:
    """Parses project manifest files"""
    
    MANIFEST_NAMES = [
        "submission.yaml",
        "submission.yml",
        "submission.json",
        "manifest.yaml",
        "manifest.yml",
        "manifest.json",
        "tb_config.yaml",
        "tb_config.yml"
    ]
    
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.manifest_path: Optional[Path] = None
        self.manifest_data: Dict[str, Any] = {}
    
    def find_manifest(self) -> Optional[Path]:
        """Find manifest file in directory"""
        for name in self.MANIFEST_NAMES:
            manifest_path = self.root_dir / name
            if manifest_path.exists():
                return manifest_path
        return None
    
    def load_manifest(self, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load and parse manifest file"""
        if manifest_path:
            self.manifest_path = manifest_path
        else:
            self.manifest_path = self.find_manifest()
        
        if not self.manifest_path:
            return {}
        
        try:
            with open(self.manifest_path, 'r') as f:
                if self.manifest_path.suffix in ['.yaml', '.yml']:
                    self.manifest_data = yaml.safe_load(f) or {}
                elif self.manifest_path.suffix == '.json':
                    self.manifest_data = json.load(f)
                else:
                    print(f"Warning: Unsupported manifest format: {self.manifest_path.suffix}")
                    return {}
        except Exception as e:
            print(f"Error loading manifest {self.manifest_path}: {e}")
            return {}
        
        return self.manifest_data
    
    def get_dut_files(self) -> List[str]:
        """Extract DUT file list from manifest"""
        if not self.manifest_data:
            return []
        return self.manifest_data.get('dut', {}).get('files', [])
    
    def get_tb_files(self) -> List[str]:
        """Extract testbench file list from manifest"""
        if not self.manifest_data:
            return []
        return self.manifest_data.get('testbench', {}).get('files', [])
    
    def get_tb_type(self) -> Optional[str]:
        """Get explicitly specified testbench type"""
        if not self.manifest_data:
            return None
        tb_type = self.manifest_data.get('testbench', {}).get('type')
        if tb_type == 'auto':
            return None
        return tb_type
    
    def get_top_module(self) -> Optional[str]:
        """Get top module name"""
        if not self.manifest_data:
            return None
        return self.manifest_data.get('dut', {}).get('top_module')
    
    def get_preferred_simulator(self) -> Optional[str]:
        """Get preferred simulator"""
        if not self.manifest_data:
            return None
        return self.manifest_data.get('simulator')
    
    def get_language(self) -> Optional[str]:
        """Get HDL language"""
        if not self.manifest_data:
            return None
        return self.manifest_data.get('dut', {}).get('language')
    
    def validate_manifest(self) -> Dict[str, Any]:
        """Validate manifest structure and return errors/warnings"""
        issues = {
            'errors': [],
            'warnings': [],
            'valid': True
        }
        
        if not self.manifest_data:
            issues['warnings'].append("No manifest file found")
            return issues
        
        # Check required fields
        if 'dut' not in self.manifest_data:
            issues['warnings'].append("No 'dut' section in manifest")
        
        if 'testbench' not in self.manifest_data:
            issues['warnings'].append("No 'testbench' section in manifest")
        
        # Check DUT files specified
        dut_files = self.get_dut_files()
        if not dut_files:
            issues['warnings'].append("No DUT files specified in manifest")
        
        # Check TB files specified
        tb_files = self.get_tb_files()
        if not tb_files:
            issues['warnings'].append("No testbench files specified in manifest")
        
        return issues
