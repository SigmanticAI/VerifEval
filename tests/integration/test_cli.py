"""
Integration tests for CLI

Author: TB Eval Team
Version: 0.1.0
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch
import sys

from step4_execute.cli.main import main, create_parser


class TestCLI:
    """Test CLI functionality"""
    
    @pytest.mark.asyncio
    async def test_cli_dry_run(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test CLI dry run"""
        from step4_execute.executor import TestExecutor
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            self.runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Mock sys.argv
        test_args = [
            "tbeval-run",
            "--dry-run",
            "--manifest",
            str(sample_manifest_file),
            str(sample_submission_dir),
        ]
        
        with patch.object(sys, 'argv', test_args):
            exit_code = await main()
        
        # Dry run should exit with code 99
        assert exit_code == 99
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing"""
        parser = create_parser()
        
        # Test basic arguments
        args = parser.parse_args(["--dry-run", "/path/to/submission"])
        assert args.dry_run is True
        assert args.submission_dir == Path("/path/to/submission")
        
        # Test with multiple options
        args = parser.parse_args([
            "--verbose",
            "--timeout", "600",
            "--filter", "test_.*",
            "/path/to/submission"
        ])
        assert args.verbose is True
        assert args.timeout == 600
        assert args.filter == "test_.*"
    
    def test_cli_config_generation(self, temp_dir):
        """Test config file generation"""
        from step4_execute.config import create_default_config_file
        
        config_path = temp_dir / ".tbeval.yaml"
        create_default_config_file(config_path)
        
        assert config_path.exists()
        content = config_path.read_text()
        assert "execution:" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
