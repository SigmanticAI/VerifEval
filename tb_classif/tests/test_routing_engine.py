"""
Complete test suite for routing engine
"""

class TestRoutingEngine:
    
    def test_create_routing_cocotb(
        self, routing_engine, sample_detection_cocotb, 
        sample_quality_pass, tmp_path
    ):
        """Test routing decision for CocoTB"""
        dut_files = [tmp_path / "rtl" / "adder.sv"]
        tb_files = [tmp_path / "tb" / "test_adder.py"]
        
        routing = routing_engine.create_routing_decision(
            detection_results=[sample_detection_cocotb],
            dut_files=dut_files,
            tb_files=tb_files,
            quality_report=sample_quality_pass
        )
        
        assert routing.tb_type == TBType.COCOTB.value
        assert routing.track == Track.A.value
        assert routing.chosen_simulator == Simulator.VERILATOR.value
        assert routing.confidence >= 0.9
        assert routing.quality_gate_passed == True
        assert len(routing.errors) == 0
    
    def test_create_routing_uvm_sv(self, routing_engine, tmp_path):
        """Test routing for UVM-SV (should flag commercial sim requirement)"""
        detection = DetectionResult(
            tb_type=TBType.UVM_SV,
            confidence=0.95,
            files_detected=["tb/test.sv"],
            detection_method="pattern_matching",
            language=Language.SYSTEMVERILOG,
            metadata={"requires_commercial_sim": True}
        )
        
        dut_files = [tmp_path / "rtl" / "fifo.sv"]
        tb_files = [tmp_path / "tb" / "test.sv"]
        
        routing = routing_engine.create_routing_decision(
            detection_results=[detection],
            dut_files=dut_files,
            tb_files=tb_files
        )
        
        assert routing.tb_type == TBType.UVM_SV.value
        assert routing.track == Track.C.value
        assert routing.chosen_simulator == Simulator.COMMERCIAL_REQUIRED.value
        assert len(routing.errors) > 0
        assert any("commercial" in e.lower() for e in routing.errors)
        assert len(routing.recommendations) > 0
        assert any("pyuvm" in r.lower() for r in routing.recommendations)
    
    def test_routing_with_quality_failures(self, routing_engine, tmp_path):
        """Test routing when quality gate fails"""
        detection = DetectionResult(
            tb_type=TBType.SYSTEMVERILOG,
            confidence=0.80,
            files_detected=["tb/tb.sv"],
            detection_method="pattern_matching",
            language=Language.SYSTEMVERILOG
        )
        
        quality_fail = QualityReport(
            status="fail",
            linter="verible",
            timestamp="2024-01-01T00:00:00Z",
            total_files=1,
            files_checked=1,
            total_violations=5,
            critical_errors=5,
            warnings=0,
            style_issues=0,
            files=[]
        )
        
        routing = routing_engine.create_routing_decision(
            detection_results=[detection],
            dut_files=[tmp_path / "rtl" / "dut.sv"],
            tb_files=[tmp_path / "tb" / "tb.sv"],
            quality_report=quality_fail
        )
        
        assert routing.quality_gate_passed == False
        assert routing.confidence < 0.8  # Penalized by quality issues
        assert len(routing.errors) > 0
    
    def test_routing_unknown_tb_type(self, routing_engine, tmp_path):
        """Test routing with no detection results"""
        routing = routing_engine.create_routing_decision(
            detection_results=[],
            dut_files=[tmp_path / "rtl" / "dut.sv"],
            tb_files=[tmp_path / "tb" / "unknown.txt"]
        )
        
        assert routing.tb_type == TBType.UNKNOWN.value
        assert routing.confidence == 0.0
        assert len(routing.errors) > 0
        assert len(routing.recommendations) > 0
    
    def test_entrypoint_determination_cocotb(self, routing_engine, tmp_path):
        """Test entrypoint selection for CocoTB"""
        tb_files = [
            tmp_path / "tb" / "helper.py",
            tmp_path / "tb" / "test_main.py",
            tmp_path / "tb" / "utils.py"
        ]
        
        entrypoint = routing_engine._determine_entrypoint(
            TBType.COCOTB, tb_files, None
        )
        
        # Should select test_main.py (has "test" in name)
        assert "test_main.py" in entrypoint
    
    def test_entrypoint_determination_vunit(self, routing_engine, tmp_path):
        """Test entrypoint selection for VUnit"""
        tb_files = [
            tmp_path / "tb" / "helper.py",
            tmp_path / "tb" / "run.py",
            tmp_path / "tb" / "tb.vhd"
        ]
        
        entrypoint = routing_engine._determine_entrypoint(
            TBType.VUNIT, tb_files, None
        )
        
        # Should select run.py
        assert "run.py" in entrypoint


class TestUVMHandler:
    """Test UVM-specific handling"""
    
    def test_migration_guide_generation(self):
        """Test pyuvm migration guide generation"""
        from step2_classify_route.routing.engine import UVMHandler
        
        guide = UVMHandler.generate_pyuvm_migration_guide([])
        
        assert "migration_guide" in guide
        assert "steps" in guide["migration_guide"]
        assert "pyuvm" in str(guide).lower()
    
    def test_uvm_compatibility_check(self):
        """Test UVM compatibility checking"""
        from step2_classify_route.routing.engine import UVMHandler
        
        detection = DetectionResult(
            tb_type=TBType.UVM_SV,
            confidence=0.95,
            files_detected=["test.sv"],
            detection_method="pattern",
            language=Language.SYSTEMVERILOG
        )
        
        compat = UVMHandler.check_uvm_compatibility(detection)
        
        assert "uvm_compatibility" in compat
        assert compat["uvm_compatibility"]["commercial_sim_required"] == True
        assert len(compat["uvm_compatibility"]["alternatives"]) > 0
