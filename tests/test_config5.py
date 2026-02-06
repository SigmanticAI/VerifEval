"""
Test coverage configuration functionality
"""

from pathlib import Path
import tempfile
import json


def test_thresholds():
    """Test CoverageThresholds"""
    from step5_coverage.config import CoverageThresholds
    
    thresholds = CoverageThresholds(
        line=85.0,
        branch=95.0,
        toggle=75.0,
        fsm=80.0,
        overall=85.0
    )
    
    # Test compliance check
    compliant, violations = thresholds.check_compliance(
        line_pct=90.0,
        branch_pct=96.0,
        toggle_pct=80.0,
        fsm_pct=85.0,
        overall_score=0.90
    )
    
    assert compliant
    assert len(violations) == 0
    
    # Test non-compliance
    compliant, violations = thresholds.check_compliance(
        line_pct=80.0,  # Below threshold
        branch_pct=96.0,
        toggle_pct=70.0,  # Below threshold
        fsm_pct=85.0,
        overall_score=0.82
    )
    
    assert not compliant
    assert len(violations) == 2
    assert any("Line coverage" in v for v in violations)
    assert any("Toggle coverage" in v for v in violations)


def test_weights():
    """Test CoverageWeights"""
    from step5_coverage.config import CoverageWeights
    
    weights = CoverageWeights(
        line=0.35,
        branch=0.35,
        toggle=0.20,
        fsm=0.10
    )
    
    # Weights should sum to 1.0
    total = weights.line + weights.branch + weights.toggle + weights.fsm
    assert abs(total - 1.0) < 0.001
    
    # Test invalid weights
    try:
        bad_weights = CoverageWeights(
            line=0.5,
            branch=0.5,
            toggle=0.5,
            fsm=0.5  # Sum = 2.0, should fail
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "sum to 1.0" in str(e)


def test_parser_config():
    """Test ParserConfig"""
    from step5_coverage.config import ParserConfig
    
    config = ParserConfig(
        priority=["verilator", "lcov", "covered"],
        use_external_tools=True,
        fallback_to_python=True
    )
    
    assert config.priority == ["verilator", "lcov", "covered"]
    assert config.use_external_tools
    assert config.fallback_to_python


def test_merging_config():
    """Test MergingConfig"""
    from step5_coverage.config import MergingConfig
    
    config = MergingConfig(
        strategy="tool_preferred",
        per_test_analysis=True,
        track_unique_contributions=True
    )
    
    assert config.strategy == "tool_preferred"
    assert config.per_test_analysis
    assert config.track_unique_contributions
    
    # Test invalid strategy
    try:
        bad_config = MergingConfig(strategy="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid merge strategy" in str(e)


def test_reporting_config():
    """Test ReportingConfig"""
    from step5_coverage.config import ReportingConfig
    
    config = ReportingConfig(
        output_dir=Path(".tbeval/coverage"),
        json_detail_level="full",
        export_mutation_targets=True
    )
    
    assert config.output_dir == Path(".tbeval/coverage")
    assert config.json_detail_level == "full"
    assert config.export_mutation_targets


def test_main_config():
    """Test CoverageAnalysisConfig"""
    from step5_coverage.config import CoverageAnalysisConfig
    
    # Create temporary test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create dummy test_report.json
        test_report = tmpdir / "test_report.json"
        test_report.write_text(json.dumps({"status": "completed"}))
        
        # Create dummy build_manifest.json
        build_manifest = tmpdir / "build_manifest.json"
        build_manifest.write_text(json.dumps({"build_status": "success"}))
        
        # Create config
        config = CoverageAnalysisConfig(
            test_report_path=test_report,
            build_manifest_path=build_manifest,
            submission_dir=tmpdir
        )
        
        assert config.test_report_path == test_report
        assert config.build_manifest_path == build_manifest
        assert not config.fail_on_threshold  # Default: don't fail


def test_config_from_yaml():
    """Test loading config from YAML"""
    from step5_coverage.config import CoverageAnalysisConfig
    import yaml
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files
        test_report = tmpdir / "test_report.json"
        test_report.write_text(json.dumps({"status": "completed"}))
        
        build_manifest = tmpdir / "build_manifest.json"
        build_manifest.write_text(json.dumps({"build_status": "success"}))
        
        # Create YAML config
        yaml_config = {
            "coverage": {
                "analysis": {
                    "thresholds": {
                        "line": 85.0,
                        "branch": 95.0,
                    },
                    "weights": {
                        "line": 0.4,
                        "branch": 0.4,
                        "toggle": 0.15,
                        "fsm": 0.05,
                    },
                    "parsers": ["verilator", "lcov"],
                }
            }
        }
        
        yaml_path = tmpdir / ".tbeval.yaml"
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_config, f)
        
        # Load config
        config = CoverageAnalysisConfig.from_yaml(
            yaml_path,
            test_report,
            build_manifest
        )
        
        assert config.thresholds.line == 85.0
        assert config.thresholds.branch == 95.0
        assert config.weights.line == 0.4
        assert config.parsers.priority == ["verilator", "lcov"]


def test_config_serialization():
    """Test config to_dict and to_yaml"""
    from step5_coverage.config import CoverageAnalysisConfig
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files
        test_report = tmpdir / "test_report.json"
        test_report.write_text(json.dumps({"status": "completed"}))
        
        build_manifest = tmpdir / "build_manifest.json"
        build_manifest.write_text(json.dumps({"build_status": "success"}))
        
        # Create config
        config = CoverageAnalysisConfig(
            test_report_path=test_report,
            build_manifest_path=build_manifest,
            submission_dir=tmpdir
        )
        
        # Test to_dict
        data = config.to_dict()
        assert "thresholds" in data
        assert "weights" in data
        assert "parsers" in data
        
        # Test to_yaml
        yaml_out = tmpdir / "config_out.yaml"
        config.to_yaml(yaml_out)
        assert yaml_out.exists()


def test_create_default_config():
    """Test creating default config file"""
    from step5_coverage.config import create_default_config_file
    import yaml
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / ".tbeval.yaml"
        
        create_default_config_file(output_path)
        
        assert output_path.exists()
        
        # Verify content
        with open(output_path) as f:
            data = yaml.safe_load(f)
        
        assert "coverage" in data
        assert "analysis" in data["coverage"]
        assert data["coverage"]["analysis"]["thresholds"]["line"] == 80.0


if __name__ == "__main__":
    print("Testing coverage configuration...")
    
    test_thresholds()
    print("✓ Thresholds")
    
    test_weights()
    print("✓ Weights")
    
    test_parser_config()
    print("✓ Parser config")
    
    test_merging_config()
    print("✓ Merging config")
    
    test_reporting_config()
    print("✓ Reporting config")
    
    test_main_config()
    print("✓ Main config")
    
    test_config_from_yaml()
    print("✓ Config from YAML")
    
    test_config_serialization()
    print("✓ Config serialization")
    
    test_create_default_config()
    print("✓ Default config creation")
    
    print("\n✅ All config tests passed!")
