"""
Complete test suite for routing engine
"""
import pytest
from pathlib import Path
import tempfile

from step2_classify_route.routing.engine import RoutingEngine, UVMHandler
from step2_classify_route.routing.confidence import ConfidenceScorer
from step2_classify_route.models import (
    DetectionResult, RoutingDecision, QualityReport,
    TBType, Track, Simulator, Language
)


@pytest.fixture
def routing_engine(tmp_path):
    """Create routing engine instance"""
    return RoutingEngine(tmp_path)


@pytest.fixture
def sample_detection_cocotb():
    """Sample CocoTB detection result"""
    return DetectionResult(
        tb_type=TBType.COCOTB,
        confidence=0.95,
        files_detected=["tb/test_adder.py"],
        detection_method="pattern_matching",
        language=Language.PYTHON,
        metadata={"has_test_decorator": True}
    )


@pytest.fixture
def sample_detection_vunit():
    """Sample VUnit detection result"""
    return DetectionResult(
        tb_type=TBType.VUNIT,
        confidence=0.92,
        files_detected=["tb/run.py", "tb/tb_counter.vhd"],
        detection_method="vunit_python_runner",
        language=Language.VHDL,
        metadata={"is_runner_script": True}
    )


@pytest.fixture
def sample_detection_uvm_sv():
    """Sample UVM-SV detection result"""
    return DetectionResult(
        tb_type=TBType.UVM_SV,
        confidence=0.95,
        files_detected=["tb/my_test.sv"],
        detection_method="pattern_matching",
        language=Language.SYSTEMVERILOG,
        metadata={"requires_commercial_sim": True}
    )


@pytest.fixture
def sample_quality_pass():
    """Sample passing quality report"""
    return QualityReport(
        status="pass",
        linter="verible",
        timestamp="2024-01-01T00:00:00Z",
        total_files=3,
        files_checked=3,
        total_violations=0,
        critical_errors=0,
        warnings=0,
        style_issues=0,
        files=[]
    )


@pytest.fixture
def sample_quality_fail():
    """Sample failing quality report"""
    return QualityReport(
        status="fail",
        linter="verible",
        timestamp="2024-01-01T00:00:00Z",
        total_files=3,
        files_checked=3,
        total_violations=5,
        critical_errors=3,
        warnings=2,
        style_issues=0,
        files=[]
    )


class TestRoutingEngine:
    """Test routing engine functionality"""
    
    def test_create_routing_cocotb(
        self, routing_engine, sample_detection_cocotb, 
        sample_quality_pass, tmp_path
    ):
        """Test routing decision for CocoTB testbench"""
        # Create dummy files
        (tmp_path / "rtl").mkdir()
        (tmp_path / "tb").mkdir()
        dut_file = tmp_path / "rtl" / "adder.sv"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "test_adder.py"
        tb_file.touch()
        
        routing = routing_engine.create_routing_decision(
            detection_results=[sample_detection_cocotb],
            dut_files=[dut_file],
            tb_files=[tb_file],
            quality_report=sample_quality_pass
        )
        
        assert routing.tb_type == TBType.COCOTB.value
        assert routing.track == Track.A.value
        assert routing.chosen_simulator == Simulator.VERILATOR.value
        assert routing.confidence >= 0.9
        assert routing.quality_gate_passed is True
        assert len(routing.errors) == 0
    
    def test_create_routing_vunit(
        self, routing_engine, sample_detection_vunit,
        sample_quality_pass, tmp_path
    ):
        """Test routing decision for VUnit testbench"""
        (tmp_path / "src").mkdir()
        (tmp_path / "tb").mkdir()
        dut_file = tmp_path / "src" / "counter.vhd"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "run.py"
        tb_file.touch()
        
        routing = routing_engine.create_routing_decision(
            detection_results=[sample_detection_vunit],
            dut_files=[dut_file],
            tb_files=[tb_file],
            quality_report=sample_quality_pass
        )
        
        assert routing.tb_type == TBType.VUNIT.value
        assert routing.track == Track.B.value
        assert routing.chosen_simulator == Simulator.GHDL.value
        assert routing.quality_gate_passed is True
    
    def test_create_routing_uvm_sv_error(
        self, routing_engine, sample_detection_uvm_sv, tmp_path
    ):
        """Test routing for UVM-SV generates proper error"""
        (tmp_path / "rtl").mkdir()
        (tmp_path / "tb").mkdir()
        dut_file = tmp_path / "rtl" / "fifo.sv"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "my_test.sv"
        tb_file.touch()
        
        routing = routing_engine.create_routing_decision(
            detection_results=[sample_detection_uvm_sv],
            dut_files=[dut_file],
            tb_files=[tb_file]
        )
        
        assert routing.tb_type == TBType.UVM_SV.value
        assert routing.track == Track.C.value
        assert routing.chosen_simulator == Simulator.COMMERCIAL_REQUIRED.value
        
        # Should have errors about commercial simulator
        assert len(routing.errors) > 0
        assert any("commercial" in e.lower() for e in routing.errors)
        
        # Should have recommendations for pyuvm
        assert len(routing.recommendations) > 0
        assert any("pyuvm" in r.lower() for r in routing.recommendations)
    
    def test_create_routing_quality_gate_fail(
        self, routing_engine, sample_detection_cocotb,
        sample_quality_fail, tmp_path
    ):
        """Test routing when quality gate fails"""
        (tmp_path / "rtl").mkdir()
        dut_file = tmp_path / "rtl" / "dut.sv"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "test.py"
        
        routing = routing_engine.create_routing_decision(
            detection_results=[sample_detection_cocotb],
            dut_files=[dut_file],
            tb_files=[tb_file],
            quality_report=sample_quality_fail
        )
        
        assert routing.quality_gate_passed is False
        assert routing.confidence < sample_detection_cocotb.confidence
        assert len(routing.errors) > 0
    
    def test_create_routing_no_detections(self, routing_engine, tmp_path):
        """Test routing with no detection results"""
        (tmp_path / "rtl").mkdir()
        dut_file = tmp_path / "rtl" / "dut.sv"
        dut_file.touch()
        tb_file = tmp_path / "unknown.txt"
        
        routing = routing_engine.create_routing_decision(
            detection_results=[],
            dut_files=[dut_file],
            tb_files=[tb_file]
        )
        
        assert routing.tb_type == TBType.UNKNOWN.value
        assert routing.confidence == 0.0
        assert len(routing.errors) > 0
        assert not routing.is_valid()
    
    def test_track_assignment(self, routing_engine):
        """Test track assignment for different TB types"""
        test_cases = [
            (TBType.COCOTB, Track.A),
            (TBType.PYUVM, Track.A),
            (TBType.VUNIT, Track.B),
            (TBType.SYSTEMVERILOG, Track.B),
            (TBType.VHDL, Track.B),
            (TBType.UVM_SV, Track.C),
        ]
        
        for tb_type, expected_track in test_cases:
            track = routing_engine._assign_track(tb_type)
            assert track == expected_track, f"Failed for {tb_type}"
    
    def test_entrypoint_cocotb(self, routing_engine, tmp_path):
        """Test entrypoint determination for CocoTB"""
        tb_files = [
            tmp_path / "tb" / "conftest.py",
            tmp_path / "tb" / "test_main.py",
            tmp_path / "tb" / "helpers.py"
        ]
        
        for f in tb_files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()
        
        entrypoint = routing_engine._determine_entrypoint(
            TBType.COCOTB, tb_files, None
        )
        
        assert "test_main.py" in entrypoint
    
    def test_entrypoint_vunit(self, routing_engine, tmp_path):
        """Test entrypoint determination for VUnit"""
        tb_files = [
            tmp_path / "tb" / "run.py",
            tmp_path / "tb" / "tb_counter.vhd",
            tmp_path / "tb" / "helpers.py"
        ]
        
        for f in tb_files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()
        
        entrypoint = routing_engine._determine_entrypoint(
            TBType.VUNIT, tb_files, None
        )
        
        assert "run.py" in entrypoint
    
    def test_entrypoint_with_top_module(self, routing_engine, tmp_path):
        """Test entrypoint when top_module is specified"""
        tb_files = [tmp_path / "tb" / "tb_top.sv"]
        
        entrypoint = routing_engine._determine_entrypoint(
            TBType.SYSTEMVERILOG, tb_files, "tb_top"
        )
        
        assert entrypoint == "tb_top"
    
    def test_recommendations_for_low_confidence(
        self, routing_engine, tmp_path
    ):
        """Test that low confidence generates recommendations"""
        detection = DetectionResult(
            tb_type=TBType.SYSTEMVERILOG,
            confidence=0.5,  # Low confidence
            files_detected=["tb/tb.sv"],
            detection_method="heuristic",
            language=Language.SYSTEMVERILOG
        )
        
        (tmp_path / "rtl").mkdir()
        (tmp_path / "tb").mkdir()
        dut_file = tmp_path / "rtl" / "dut.sv"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "tb.sv"
        tb_file.touch()
        
        routing = routing_engine.create_routing_decision(
            detection_results=[detection],
            dut_files=[dut_file],
            tb_files=[tb_file]
        )
        
        # Should have recommendation to add manifest
        assert any("manifest" in r.lower() for r in routing.recommendations)
    
    def test_multiple_detections_select_highest_confidence(
        self, routing_engine, tmp_path
    ):
        """Test that highest confidence detection is selected"""
        detection_low = DetectionResult(
            tb_type=TBType.SYSTEMVERILOG,
            confidence=0.6,
            files_detected=["tb/tb.sv"],
            detection_method="heuristic",
            language=Language.SYSTEMVERILOG
        )
        
        detection_high = DetectionResult(
            tb_type=TBType.COCOTB,
            confidence=0.95,
            files_detected=["tb/test.py"],
            detection_method="pattern_matching",
            language=Language.PYTHON
        )
        
        (tmp_path / "rtl").mkdir()
        dut_file = tmp_path / "rtl" / "dut.sv"
        dut_file.touch()
        tb_file = tmp_path / "tb" / "test.py"
        
        routing = routing_engine.create_routing_decision(
            detection_results=[detection_low, detection_high],
            dut_files=[dut_file],
            tb_files=[tb_file]
        )
        
        # Should select CocoTB (higher confidence)
        assert routing.tb_type == TBType.COCOTB.value


class TestConfidenceScorer:
    """Test confidence scoring logic"""
    
    def test_calculate_detection_confidence_basic(self):
        """Test basic confidence calculation"""
        detection = DetectionResult(
            tb_type=TBType.COCOTB,
            confidence=0.95,
            files_detected=["test.py"],
            detection_method="pattern",
            language=Language.PYTHON
        )
        
        quality = QualityReport(
            status="pass",
            linter="verible",
            timestamp="",
            total_files=1,
            files_checked=1,
            total_violations=0,
            critical_errors=0,
            warnings=0,
            style_issues=0,
            files=[]
        )
        
        confidence = ConfidenceScorer.calculate_detection_confidence(
            [detection], quality
        )
        
        assert confidence >= 0.9
    
    def test_confidence_penalized_by_quality_errors(self):
        """Test that critical errors reduce confidence"""
        detection = DetectionResult(
            tb_type=TBType.COCOTB,
            confidence=0.95,
            files_detected=["test.py"],
            detection_method="pattern",
            language=Language.PYTHON
        )
        
        quality_fail = QualityReport(
            status="fail",
            linter="verible",
            timestamp="",
            total_files=1,
            files_checked=1,
            total_violations=5,
            critical_errors=5,
            warnings=0,
            style_issues=0,
            files=[]
        )
        
        confidence = ConfidenceScorer.calculate_detection_confidence(
            [detection], quality_fail
        )
        
        # Should be significantly lower due to errors
        assert confidence < 0.7
    
    def test_select_best_detection(self):
        """Test selecting best detection from multiple"""
        detections = [
            DetectionResult(
                tb_type=TBType.SYSTEMVERILOG,
                confidence=0.5,
                files_detected=[],
                detection_method="",
                language=Language.SYSTEMVERILOG
            ),
            DetectionResult(
                tb_type=TBType.COCOTB,
                confidence=0.95,
                files_detected=[],
                detection_method="",
                language=Language.PYTHON
            ),
            DetectionResult(
                tb_type=TBType.VUNIT,
                confidence=0.7,
                files_detected=[],
                detection_method="",
                language=Language.VHDL
            ),
        ]
        
        best = ConfidenceScorer.select_best_detection(detections)
        
        assert best.tb_type == TBType.COCOTB
        assert best.confidence == 0.95
    
    def test_select_best_detection_empty_list(self):
        """Test error handling for empty detection list"""
        with pytest.raises(ValueError):
            ConfidenceScorer.select_best_detection([])


class TestUVMHandler:
    """Test UVM-specific handling"""
    
    def test_migration_guide_structure(self):
        """Test pyuvm migration guide generation"""
        guide = UVMHandler.generate_pyuvm_migration_guide([])
        
        assert "migration_guide" in guide
        assert "steps" in guide["migration_guide"]
        assert "resources" in guide["migration_guide"]
        assert len(guide["migration_guide"]["steps"]) > 0
        assert "pyuvm" in str(guide).lower()
    
    def test_uvm_compatibility_check_structure(self):
        """Test UVM compatibility check output structure"""
        detection = DetectionResult(
            tb_type=TBType.UVM_SV,
            confidence=0.95,
            files_detected=["test.sv"],
            detection_method="pattern",
            language=Language.SYSTEMVERILOG
        )
        
        compat = UVMHandler.check_uvm_compatibility(detection)
        
        assert "uvm_compatibility" in compat
        assert compat["uvm_compatibility"]["commercial_sim_required"] is True
        assert "alternatives" in compat["uvm_compatibility"]
        assert len(compat["uvm_compatibility"]["alternatives"]) > 0
    
    def test_migration_guide_has_example(self):
        """Test that migration guide includes code example"""
        guide = UVMHandler.generate_pyuvm_migration_guide([])
        
        assert "example_conversion" in guide["migration_guide"]
        assert "systemverilog" in guide["migration_guide"]["example_conversion"]
        assert "pyuvm" in guide["migration_guide"]["example_conversion"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
