"""
Mock build manifests for testing

Author: TB Eval Team
Version: 0.1.0
"""

from datetime import datetime


def get_cocotb_manifest(submission_dir: str = "/tmp/submission"):
    """Get CocoTB (Track A) manifest"""
    return {
        "schema_version": "1.0",
        "framework_version": "0.1.0",
        "build_status": "success",
        "timestamp": datetime.now().isoformat(),
        "duration_ms": 5000,
        "track_used": "A",
        "submission_dir": submission_dir,
        "simulator_config": {
            "simulator_type": "verilator",
            "available": True,
            "version": "5.006",
        },
        "tests_discovered": {
            "tests": [
                {
                    "name": "test_basic",
                    "full_name": "test_adder.test_basic",
                    "testbench": "test_adder",
                    "test_type": "cocotb",
                    "timeout_ms": 30000,
                },
                {
                    "name": "test_advanced",
                    "full_name": "test_adder.test_advanced",
                    "testbench": "test_adder",
                    "test_type": "cocotb",
                    "timeout_ms": 60000,
                },
            ],
            "total_count": 2,
        },
        "execution_command": ["make", "-C", ".tbeval/cocotb"],
        "execution_env": {"SIM": "verilator"},
        "execution_cwd": ".tbeval/cocotb",
    }


def get_vunit_manifest(submission_dir: str = "/tmp/submission"):
    """Get VUnit (Track B) manifest"""
    return {
        "schema_version": "1.0",
        "framework_version": "0.1.0",
        "build_status": "success",
        "timestamp": datetime.now().isoformat(),
        "duration_ms": 8000,
        "track_used": "B",
        "submission_dir": submission_dir,
        "vunit_project": {
            "run_py_path": ".tbeval/vunit_project/run.py",
            "generated": True,
            "output_path": ".tbeval/vunit_out",
        },
        "simulator_config": {
            "simulator_type": "ghdl",
            "available": True,
        },
        "tests_discovered": {
            "tests": [
                {
                    "name": "test_reset",
                    "full_name": "work.tb_counter.test_reset",
                    "testbench": "tb_counter",
                    "test_type": "vunit",
                    "timeout_ms": 30000,
                },
                {
                    "name": "test_count",
                    "full_name": "work.tb_counter.test_count",
                    "testbench": "tb_counter",
                    "test_type": "vunit",
                    "timeout_ms": 30000,
                },
            ],
            "total_count": 2,
        },
    }


def get_failing_manifest(submission_dir: str = "/tmp/submission"):
    """Get manifest with build failure"""
    manifest = get_cocotb_manifest(submission_dir)
    manifest["build_status"] = "failed"
    manifest["errors"] = ["Compilation failed"]
    return manifest
