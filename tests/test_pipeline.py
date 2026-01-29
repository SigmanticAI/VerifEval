"""
Tests for the end-to-end evaluation pipeline (Questa version).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from pipeline.evaluator import (
    VerifEvalPipeline, PipelineConfig, EvaluationResult,
    StageResult, EvaluationStage
)


class TestPipelineConfig:
    """Tests for PipelineConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = PipelineConfig()
        
        assert config.run_quality_gate == True
        assert config.simulator == "questa"
        assert config.num_runs == 1
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = PipelineConfig(
            run_quality_gate=False,
            num_runs=3,
            verbose=True,
            license_file="1717@license.server.com"
        )
        
        assert config.run_quality_gate == False
        assert config.num_runs == 3
        assert config.verbose == True
        assert config.license_file == "1717@license.server.com"


class TestEvaluationResult:
    """Tests for EvaluationResult."""
    
    def test_empty_result(self):
        """Test empty evaluation result."""
        result = EvaluationResult(
            success=False,
            project_name="test_project",
            timestamp="2024-01-01T00:00:00"
        )
        
        assert result.success == False
        assert result.project_name == "test_project"
        assert len(result.stages) == 0
    
    def test_result_with_stages(self):
        """Test result with stage results."""
        result = EvaluationResult(
            success=True,
            project_name="test_project",
            timestamp="2024-01-01T00:00:00"
        )
        
        result.stages['quality_gate'] = StageResult(
            stage=EvaluationStage.QUALITY_GATE,
            success=True,
            duration_ms=100.0
        )
        
        assert len(result.stages) == 1
        assert result.stages['quality_gate'].success == True
    
    def test_to_dict(self):
        """Test serialization."""
        result = EvaluationResult(
            success=True,
            project_name="test",
            timestamp="2024-01-01T00:00:00",
            total_duration_ms=5000.0
        )
        
        data = result.to_dict()
        
        assert data['success'] == True
        assert data['project_name'] == "test"
        assert data['total_duration_ms'] == 5000.0


class TestStageResult:
    """Tests for StageResult."""
    
    def test_stage_result_creation(self):
        """Test creating a stage result."""
        result = StageResult(
            stage=EvaluationStage.BUILD,
            success=True,
            duration_ms=500.0
        )
        
        assert result.stage == EvaluationStage.BUILD
        assert result.success == True
        assert result.duration_ms == 500.0
    
    def test_stage_result_with_data(self):
        """Test stage result with data."""
        result = StageResult(
            stage=EvaluationStage.EXECUTE,
            success=True,
            data={
                'tests_passed': 10,
                'tests_failed': 2,
                'coverage': 85.5
            }
        )
        
        assert result.data['tests_passed'] == 10
        assert result.data['coverage'] == 85.5


class TestEvaluationStage:
    """Tests for EvaluationStage enum."""
    
    def test_all_stages_defined(self):
        """Test that all expected stages are defined."""
        expected_stages = [
            'QUALITY_GATE', 'CLASSIFY_ROUTE', 'TRANSLATION',
            'BUILD', 'EXECUTE', 'COVERAGE', 'SCORING'
        ]
        
        for stage_name in expected_stages:
            assert hasattr(EvaluationStage, stage_name)


class TestVerifEvalPipeline:
    """Tests for VerifEvalPipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline with default config."""
        return VerifEvalPipeline(PipelineConfig(verbose=False))
    
    @pytest.fixture
    def sample_uvm_project(self, tmp_path):
        """Create a sample UVM project."""
        tb_dir = tmp_path / "tb"
        tb_dir.mkdir()
        
        (tb_dir / "tb_top.sv").write_text('''
`timescale 1ns/1ps
module tb_top;
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    
    logic clk;
    logic rst_n;
    
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    initial begin
        rst_n = 0;
        #100;
        rst_n = 1;
    end
    
    initial begin
        run_test();
    end
endmodule
''')
        
        (tb_dir / "test.sv").write_text('''
class simple_test extends uvm_test;
    `uvm_component_utils(simple_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
endclass
''')
        
        # Create verification plan
        import json
        with open(tmp_path / "verification_plan.json", 'w') as f:
            json.dump({
                "tests": [
                    {"name": "base_test"},
                    {"name": "random_test"}
                ]
            }, f)
        
        return tmp_path
    
    def test_pipeline_init(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline is not None
        assert pipeline.config is not None
    
    def test_pipeline_with_custom_config(self):
        """Test pipeline with custom config."""
        config = PipelineConfig(
            run_quality_gate=False,
            num_runs=5
        )
        pipeline = VerifEvalPipeline(config)
        
        assert pipeline.config.run_quality_gate == False
        assert pipeline.config.num_runs == 5


class TestPipelineStages:
    """Tests for individual pipeline stages."""
    
    @pytest.fixture
    def pipeline(self):
        return VerifEvalPipeline(PipelineConfig(verbose=False))
    
    def test_quality_gate_no_files(self, pipeline, tmp_path):
        """Test quality gate with no SV files."""
        result = pipeline._run_quality_gate(tmp_path)
        
        # Should succeed but skip
        assert result.success == True
        assert result.data.get('skipped') == True
    
    def test_classification_empty_project(self, pipeline, tmp_path):
        """Test classification with empty project."""
        result = pipeline._run_classification(tmp_path)
        
        # Should fail since no files found
        assert result.stage == EvaluationStage.CLASSIFY_ROUTE
        assert result.success == False
    
    def test_classification_with_files(self, pipeline, tmp_path):
        """Test classification with SV files."""
        # Create a simple DUT file
        (tmp_path / "dut.sv").write_text('''
module dut(
    input clk,
    input rst_n,
    output logic [7:0] data
);
endmodule
''')
        
        result = pipeline._run_classification(tmp_path)
        
        assert result.stage == EvaluationStage.CLASSIFY_ROUTE
        assert result.success == True
        assert 'routing' in result.data
    
    def test_scoring_empty_stages(self, pipeline):
        """Test scoring with empty stages."""
        result = pipeline._compute_scores({})
        
        assert result.stage == EvaluationStage.SCORING
        assert 'overall_score' in result.data


class TestPipelineIntegration:
    """Integration tests for the pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        return VerifEvalPipeline(PipelineConfig(
            run_quality_gate=False,
            verbose=False
        ))
    
    def test_evaluate_nonexistent_path(self, pipeline, tmp_path):
        """Test evaluation of non-existent path."""
        fake_path = tmp_path / "nonexistent"
        
        result = pipeline.evaluate(fake_path)
        
        # Should handle gracefully
        assert isinstance(result, EvaluationResult)
        assert result.success == False
        assert any("does not exist" in e for e in result.errors)
    
    def test_evaluate_empty_project(self, pipeline, tmp_path):
        """Test evaluation of empty project."""
        result = pipeline.evaluate(tmp_path)
        
        assert isinstance(result, EvaluationResult)
        assert result.project_name == tmp_path.name


class TestScoring:
    """Tests for scoring logic."""
    
    @pytest.fixture
    def pipeline(self):
        return VerifEvalPipeline(PipelineConfig())
    
    def test_compute_scores_all_success(self, pipeline):
        """Test scoring when all stages succeed."""
        stages = {
            'quality_gate': StageResult(
                stage=EvaluationStage.QUALITY_GATE,
                success=True,
                data={'critical_errors': 0, 'warnings': 0}
            ),
            'execute': StageResult(
                stage=EvaluationStage.EXECUTE,
                success=True,
                data={
                    'build_success_rate': 100.0,
                    'sim_success_rate': 100.0,
                    'avg_coverage': 80.0
                }
            )
        }
        
        result = pipeline._compute_scores(stages)
        
        assert result.data['overall_score'] > 0
        assert result.data['build_success'] == 100.0
    
    def test_compute_scores_lint_errors(self, pipeline):
        """Test scoring with lint errors."""
        stages = {
            'quality_gate': StageResult(
                stage=EvaluationStage.QUALITY_GATE,
                success=False,
                data={'critical_errors': 5, 'warnings': 10}
            )
        }
        
        result = pipeline._compute_scores(stages)
        
        # Lint score should be reduced
        assert result.data['lint_score'] < 100.0


class TestResultFinalization:
    """Tests for result finalization."""
    
    @pytest.fixture
    def pipeline(self):
        return VerifEvalPipeline(PipelineConfig())
    
    def test_finalize_aggregates_errors(self, pipeline):
        """Test that finalization aggregates errors."""
        import time
        
        result = EvaluationResult(
            success=True,
            project_name="test",
            timestamp="2024-01-01"
        )
        
        result.stages['test'] = StageResult(
            stage=EvaluationStage.BUILD,
            success=False,
            errors=["Error 1", "Error 2"]
        )
        
        finalized = pipeline._finalize_result(result, time.time())
        
        assert "Error 1" in finalized.errors
        assert "Error 2" in finalized.errors
