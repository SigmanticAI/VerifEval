"""
Main orchestrator for Step 2: Classification and Routing
"""
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .models import (
    RoutingDecision, QualityReport, DetectionResult,
    TBType, Track, Language, ProjectConfig
)
from .config import ConfigManager
from .discovery.file_finder import FileFinder
from .discovery.manifest_parser import ManifestParser
from .detectors.cocotb_detector import CocoTBDetector
from .detectors.pyuvm_detector import PyUVMDetector
from .detectors.uvm_sv_detector import UVMSVDetector
from .detectors.vunit_detector import VUnitDetector
from .detectors.hdl_detector import HDLDetector
from .quality_gate.verible_linter import VeribleLinter
from .quality_gate.ghdl_checker import GHDLChecker
from .routing.engine import RoutingEngine
from .utils.validators import ProjectValidator


class ClassifierRouter:
    """
    Main orchestrator for testbench classification and routing
    
    Coordinates:
    - File discovery
    - Manifest parsing
    - TB type detection
    - Quality gate execution
    - Routing decision generation
    """
    
    def __init__(
        self,
        submission_dir: Path,
        config: Optional[ProjectConfig] = None
    ):
        self.submission_dir = Path(submission_dir)
        self.config = config or ConfigManager.load_config(search_dir=self.submission_dir)
        
        # Initialize components
        self.file_finder = FileFinder(self.submission_dir, self.config)
        self.manifest_parser = ManifestParser(self.submission_dir)
        self.routing_engine = RoutingEngine(self.submission_dir)
        self.validator = ProjectValidator(self.submission_dir)
        
        # Initialize detectors (order matters - more specific first)
        self.detectors = [
            PyUVMDetector(),      # Most specific Python TB
            CocoTBDetector(),     # Python TB
            UVMSVDetector(),      # UVM-SV (needs special handling)
            VUnitDetector(),      # VUnit framework
            HDLDetector(),        # Generic HDL (fallback)
        ]
        
        # Results storage
        self.detection_results: List[DetectionResult] = []
        self.quality_report: Optional[QualityReport] = None
        self.dut_files: List[Path] = []
        self.tb_files: List[Path] = []
    
    def classify_and_route(
        self,
        run_quality_gate: bool = True
    ) -> RoutingDecision:
        """
        Main classification and routing pipeline
        
        Steps:
        1. Load manifest (if exists)
        2. Discover files
        3. Validate project structure
        4. Detect testbench type
        5. Run quality gate (optional)
        6. Generate routing decision
        
        Args:
            run_quality_gate: Whether to run static analysis
        
        Returns:
            RoutingDecision with all routing information
        """
        # Step 1: Load manifest
        manifest_data = self.manifest_parser.load_manifest()
        manifest_validation = self.manifest_parser.validate_manifest()
        
        # Step 2: Discover files (manifest overrides auto-discovery)
        self._discover_files(manifest_data)
        
        # Step 3: Validate project structure
        validation_results = self.validator.validate_project(
            self.dut_files, self.tb_files
        )
        
        if not validation_results['valid']:
            # Return early with error routing
            return self._create_error_routing(
                errors=validation_results['errors'],
                warnings=validation_results['warnings']
            )
        
        # Step 4: Detect testbench type
        explicit_tb_type = self.manifest_parser.get_tb_type()
        
        if explicit_tb_type:
            # Use manifest-specified type
            self.detection_results = [self._create_manifest_detection(explicit_tb_type)]
        else:
            # Auto-detect
            self.detection_results = self._run_detection()
        
        # Step 5: Run quality gate
        if run_quality_gate and self.config.quality_gate_mode != "disabled":
            self.quality_report = self._run_quality_gate()
        
        # Step 6: Generate routing decision
        routing = self.routing_engine.create_routing_decision(
            detection_results=self.detection_results,
            dut_files=self.dut_files,
            tb_files=self.tb_files,
            quality_report=self.quality_report,
            top_module=self.manifest_parser.get_top_module(),
            preferred_simulator=self.manifest_parser.get_preferred_simulator()
        )
        
        # Add any manifest validation warnings
        if manifest_validation['warnings']:
            routing.warnings.extend(manifest_validation['warnings'])
        
        return routing
    
    def _discover_files(self, manifest_data: dict) -> None:
        """Discover DUT and TB files"""
        # Try manifest first
        manifest_dut = self.manifest_parser.get_dut_files()
        manifest_tb = self.manifest_parser.get_tb_files()
        
        if manifest_dut:
            self.dut_files = [self.submission_dir / f for f in manifest_dut]
        else:
            self.dut_files = self.file_finder.find_dut_files()
        
        if manifest_tb:
            self.tb_files = [self.submission_dir / f for f in manifest_tb]
        else:
            self.tb_files = self.file_finder.find_testbench_files()
    
    def _run_detection(self) -> List[DetectionResult]:
        """Run all detectors on testbench files"""
        results = []
        
        for tb_file in self.tb_files:
            for detector in self.detectors:
                result = detector.detect(tb_file)
                if result:
                    results.append(result)
                    break  # Use first matching detector
        
        return results
    
    def _create_manifest_detection(self, tb_type: str) -> DetectionResult:
        """Create detection result from manifest specification"""
        try:
            detected_type = TBType(tb_type)
        except ValueError:
            detected_type = TBType.UNKNOWN
        
        # Determine language from TB type
        language_map = {
            TBType.COCOTB: Language.PYTHON,
            TBType.PYUVM: Language.PYTHON,
            TBType.VUNIT: Language.VHDL,  # Default, could be SV
            TBType.SYSTEMVERILOG: Language.SYSTEMVERILOG,
            TBType.VHDL: Language.VHDL,
            TBType.UVM_SV: Language.SYSTEMVERILOG,
        }
        
        return DetectionResult(
            tb_type=detected_type,
            confidence=1.0,  # Manifest is authoritative
            files_detected=[str(f) for f in self.tb_files],
            detection_method="manifest",
            language=language_map.get(detected_type, Language.SYSTEMVERILOG),
            metadata={"source": "submission.yaml"}
        )
    
    def _run_quality_gate(self) -> QualityReport:
        """Run quality gate based on detected language"""
        # Combine all files for quality check
        all_hdl_files = [
            f for f in (self.dut_files + self.tb_files)
            if f.suffix in ['.sv', '.v', '.vhd', '.vhdl', '.svh']
        ]
        
        if not all_hdl_files:
            return QualityReport(
                status="skipped",
                linter="none",
                timestamp=datetime.now().isoformat(),
                total_files=0,
                files_checked=0,
                total_violations=0,
                critical_errors=0,
                warnings=0,
                style_issues=0,
                files=[]
            )
        
        # Determine which linter to use based on file types
        sv_files = [f for f in all_hdl_files if f.suffix in ['.sv', '.v', '.svh']]
        vhdl_files = [f for f in all_hdl_files if f.suffix in ['.vhd', '.vhdl']]
        
        reports = []
        
        # Run Verible on SystemVerilog files
        if sv_files:
            verible = VeribleLinter(
                sv_files,
                self.submission_dir,
                rules_config=Path(self.config.verible_rules_file) if self.config.verible_rules_file else None,
                waiver_file=Path(self.config.verible_waiver_file) if self.config.verible_waiver_file else None
            )
            reports.append(verible.run_checks())
        
        # Run GHDL on VHDL files
        if vhdl_files:
            ghdl = GHDLChecker(vhdl_files, self.submission_dir)
            reports.append(ghdl.run_checks())
        
        # Merge reports if multiple
        if len(reports) == 1:
            return reports[0]
        elif len(reports) > 1:
            return self._merge_quality_reports(reports)
        else:
            return self._create_empty_quality_report()
    
    def _merge_quality_reports(self, reports: List[QualityReport]) -> QualityReport:
        """Merge multiple quality reports into one"""
        merged = QualityReport(
            status="pass",
            linter="multiple",
            timestamp=datetime.now().isoformat(),
            total_files=sum(r.total_files for r in reports),
            files_checked=sum(r.files_checked for r in reports),
            total_violations=sum(r.total_violations for r in reports),
            critical_errors=sum(r.critical_errors for r in reports),
            warnings=sum(r.warnings for r in reports),
            style_issues=sum(r.style_issues for r in reports),
            files=[]
        )
        
        # Combine file reports
        for report in reports:
            merged.files.extend(report.files)
        
        # Update status
        if merged.critical_errors > 0:
            merged.status = "fail"
        elif merged.warnings > 0:
            merged.status = "warning"
        
        return merged
    
    def _create_empty_quality_report(self) -> QualityReport:
        """Create empty quality report"""
        return QualityReport(
            status="skipped",
            linter="none",
            timestamp=datetime.now().isoformat(),
            total_files=0,
            files_checked=0,
            total_violations=0,
            critical_errors=0,
            warnings=0,
            style_issues=0,
            files=[]
        )
    
    def _create_error_routing(
        self,
        errors: List[str],
        warnings: List[str]
    ) -> RoutingDecision:
        """Create routing decision for validation errors"""
        return RoutingDecision(
            tb_type=TBType.UNKNOWN.value,
            track=Track.B.value,
            entrypoint="",
            chosen_simulator="none",
            language=Language.SYSTEMVERILOG.value,
            confidence=0.0,
            detection_method="failed",
            dut_files=[str(f) for f in self.dut_files],
            tb_files=[str(f) for f in self.tb_files],
            quality_gate_passed=False,
            recommendations=["Fix validation errors before proceeding"],
            warnings=warnings,
            errors=errors
        )
    
    def save_routing(
        self,
        routing: RoutingDecision,
        output_path: Optional[Path] = None
    ) -> Path:
        """Save routing decision to JSON file"""
        if output_path is None:
            output_path = self.submission_dir / "route.json"
        
        with open(output_path, 'w') as f:
            json.dump(routing.to_dict(), f, indent=2)
        
        return output_path
    
    def save_quality_report(
        self,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Save quality report to JSON file"""
        if not self.quality_report:
            return None
        
        if output_path is None:
            output_path = self.submission_dir / "quality_report.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.quality_report.to_dict(), f, indent=2)
        
        return output_path
