"""
UVM Translation Runner.

Main entry point for UVM-SV to Python/cocotb translation.
Provides CLI interface and programmatic API.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .parser import UVMParser
from .analyzer import UVMAnalyzer, UVMTestbenchStructure
from .translator import UVMTranslator, TranslationResult, TranslationMode
from .validator import TranslationValidator, ValidationResult
from .templates import generate_complete_testbench, TemplateConfig


class UVMTranslationRunner:
    """
    Main runner for UVM to Python translation workflow.
    
    Handles the complete pipeline:
    1. Parse UVM-SV files
    2. Analyze testbench structure
    3. Translate to Python/cocotb (via LLM or templates)
    4. Validate generated code
    5. Write output files
    """
    
    def __init__(self, 
                 mode: TranslationMode = TranslationMode.COCOTB,
                 use_llm: bool = True,
                 llm_provider: str = "anthropic",
                 verbose: bool = False):
        """
        Initialize the translation runner.
        
        Args:
            mode: Translation target (cocotb or pyuvm)
            use_llm: Whether to use LLM for translation (False = template-only)
            llm_provider: LLM provider to use (anthropic or openai)
            verbose: Enable verbose output
        """
        self.mode = mode
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.verbose = verbose
        
        self.parser = UVMParser()
        self.analyzer = UVMAnalyzer()
        self.validator = TranslationValidator()
        
        if use_llm:
            self.translator = UVMTranslator(
                mode=mode,
                llm_provider=llm_provider
            )
        else:
            self.translator = None
    
    def translate(self, 
                 input_path: Path,
                 output_dir: Optional[Path] = None,
                 validate: bool = True,
                 auto_fix: bool = True) -> Dict[str, Any]:
        """
        Run the complete translation pipeline.
        
        Args:
            input_path: Path to UVM project directory or single file
            output_dir: Output directory (default: input_path/translated_cocotb)
            validate: Whether to validate generated code
            auto_fix: Whether to attempt auto-fixing issues
            
        Returns:
            Dictionary with translation results
        """
        results = {
            'success': False,
            'input_path': str(input_path),
            'output_dir': None,
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode.value,
            'use_llm': self.use_llm,
            'parse_result': None,
            'analysis': None,
            'translation': None,
            'validation': None,
            'files_generated': [],
            'errors': [],
            'warnings': [],
        }
        
        input_path = Path(input_path)
        
        # Determine if input is file or directory
        if input_path.is_file():
            project_dir = input_path.parent
            is_single_file = True
        else:
            project_dir = input_path
            is_single_file = False
        
        # Set output directory
        if output_dir is None:
            output_dir = project_dir / "translated_cocotb"
        output_dir = Path(output_dir)
        results['output_dir'] = str(output_dir)
        
        try:
            # Step 1: Parse
            if self.verbose:
                print(f"[1/4] Parsing UVM files in {input_path}...")
            
            if is_single_file:
                parse_result = self.parser.parse_file(input_path)
            else:
                parse_result = self.parser.parse_project(project_dir)
            
            results['parse_result'] = {
                'num_components': len(parse_result.components),
                'num_interfaces': len(parse_result.interfaces),
                'num_modules': len(parse_result.modules),
                'imports': parse_result.imports[:10],  # Limit for brevity
                'errors': parse_result.errors,
            }
            
            if parse_result.errors:
                results['warnings'].extend(parse_result.errors)
            
            if not parse_result.components and not parse_result.interfaces:
                results['errors'].append("No UVM components found")
                return results
            
            # Step 2: Analyze
            if self.verbose:
                print("[2/4] Analyzing testbench structure...")
            
            structure = self.analyzer.analyze(parse_result)
            structure.project_name = project_dir.name
            
            results['analysis'] = structure.to_dict()
            results['warnings'].extend(structure.warnings)
            
            # Step 3: Translate
            if self.verbose:
                print("[3/4] Translating to Python/cocotb...")
            
            if self.use_llm and self.translator:
                # Use LLM-based translation
                translation_result = self.translator.translate_project(
                    project_dir, output_dir
                )
            else:
                # Use template-based translation
                translation_result = self._translate_with_templates(
                    structure, output_dir
                )
            
            results['translation'] = translation_result.to_dict()
            results['files_generated'] = [f.filename for f in translation_result.files]
            results['errors'].extend(translation_result.errors)
            results['warnings'].extend(translation_result.warnings)
            
            if not translation_result.success:
                return results
            
            # Step 4: Validate
            if validate:
                if self.verbose:
                    print("[4/4] Validating generated code...")
                
                validation_result = self.validator.validate_project(output_dir)
                
                # Auto-fix if enabled
                if auto_fix and not validation_result.valid:
                    self._auto_fix_files(output_dir)
                    # Re-validate
                    validation_result = self.validator.validate_project(output_dir)
                
                results['validation'] = validation_result.to_dict()
                
                for issue in validation_result.issues:
                    if issue.severity.value == 'error':
                        results['errors'].append(issue.message)
                    elif issue.severity.value == 'warning':
                        results['warnings'].append(issue.message)
            
            results['success'] = len(results['errors']) == 0
            
            if self.verbose:
                self._print_summary(results)
            
        except Exception as e:
            results['errors'].append(f"Translation failed: {str(e)}")
            import traceback
            if self.verbose:
                traceback.print_exc()
        
        return results
    
    def _translate_with_templates(self, structure: UVMTestbenchStructure,
                                  output_dir: Path) -> TranslationResult:
        """Translate using templates only (no LLM)."""
        result = TranslationResult(success=True, mode=self.mode)
        result.output_dir = output_dir
        result.source_structure = structure
        
        try:
            # Generate complete testbench using templates
            testbench_code = generate_complete_testbench(structure)
            
            from .translator import TranslatedFile
            
            # Main test file
            result.files.append(TranslatedFile(
                filename="test_dut.py",
                content=testbench_code,
                file_type="test"
            ))
            
            # Generate Makefile
            makefile = self._generate_makefile(structure)
            result.files.append(TranslatedFile(
                filename="Makefile",
                content=makefile,
                file_type="build"
            ))
            
            # Write files
            output_dir.mkdir(parents=True, exist_ok=True)
            for file in result.files:
                file_path = output_dir / file.filename
                with open(file_path, 'w') as f:
                    f.write(file.content)
            
            result.notes.append("Generated using templates (no LLM)")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Template generation failed: {str(e)}")
        
        return result
    
    def _generate_makefile(self, structure: UVMTestbenchStructure) -> str:
        """Generate Makefile for the translated testbench."""
        dut_name = structure.dut_name or "dut"
        
        return f'''# Makefile for cocotb simulation
# Auto-generated by UVM Translator

SIM ?= verilator
TOPLEVEL = {dut_name}
TOPLEVEL_LANG = verilog

# Add your DUT Verilog files here
VERILOG_SOURCES = $(shell find ../rtl -name "*.v" -o -name "*.sv" 2>/dev/null)

MODULE = test_dut

ifeq ($(SIM),verilator)
    EXTRA_ARGS += --trace --coverage -Wno-fatal
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
\trm -rf __pycache__ results.xml *.vcd *.fst sim_build

.PHONY: clean
'''
    
    def _auto_fix_files(self, output_dir: Path) -> None:
        """Attempt to auto-fix issues in generated files."""
        for py_file in output_dir.glob('*.py'):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                fixed = self.validator.auto_fix(content)
                
                if fixed != content:
                    with open(py_file, 'w') as f:
                        f.write(fixed)
                    
                    if self.verbose:
                        print(f"  Auto-fixed: {py_file.name}")
            except Exception:
                pass
    
    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print translation summary."""
        print("\n" + "=" * 60)
        print("UVM TRANSLATION SUMMARY")
        print("=" * 60)
        
        print(f"\nInput: {results['input_path']}")
        print(f"Output: {results['output_dir']}")
        print(f"Mode: {results['mode']}")
        print(f"LLM: {'Yes' if results['use_llm'] else 'No (templates only)'}")
        
        if results['parse_result']:
            pr = results['parse_result']
            print(f"\nParsed:")
            print(f"  - Components: {pr['num_components']}")
            print(f"  - Interfaces: {pr['num_interfaces']}")
            print(f"  - Modules: {pr['num_modules']}")
        
        if results['files_generated']:
            print(f"\nGenerated files:")
            for f in results['files_generated']:
                print(f"  - {f}")
        
        if results['errors']:
            print(f"\nErrors ({len(results['errors'])}):")
            for e in results['errors'][:5]:
                print(f"  ✗ {e}")
        
        if results['warnings']:
            print(f"\nWarnings ({len(results['warnings'])}):")
            for w in results['warnings'][:5]:
                print(f"  ⚠ {w}")
        
        status = "✓ SUCCESS" if results['success'] else "✗ FAILED"
        print(f"\nStatus: {status}")
        print("=" * 60)


def main():
    """CLI entry point for UVM translation."""
    parser = argparse.ArgumentParser(
        description="UVM-SV to Python/cocotb Translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate UVM project using LLM
  python -m uvm_translator.runner --input path/to/uvm_tb
  
  # Translate using templates only (no LLM required)
  python -m uvm_translator.runner --input path/to/uvm_tb --no-llm
  
  # Specify output directory
  python -m uvm_translator.runner --input path/to/uvm_tb --output path/to/output
  
  # Use OpenAI instead of Claude
  python -m uvm_translator.runner --input path/to/uvm_tb --provider openai
        """
    )
    
    parser.add_argument('--input', '-i', type=Path, required=True,
                       help='Input UVM project directory or file')
    parser.add_argument('--output', '-o', type=Path,
                       help='Output directory for translated files')
    parser.add_argument('--mode', choices=['cocotb', 'pyuvm'], default='cocotb',
                       help='Translation target (default: cocotb)')
    parser.add_argument('--no-llm', action='store_true',
                       help='Use templates only, no LLM translation')
    parser.add_argument('--provider', choices=['anthropic', 'openai'], default='anthropic',
                       help='LLM provider (default: anthropic)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation of generated code')
    parser.add_argument('--no-fix', action='store_true',
                       help='Skip auto-fixing of issues')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"Error: Input path does not exist: {args.input}")
        sys.exit(1)
    
    # Create runner
    mode = TranslationMode.COCOTB if args.mode == 'cocotb' else TranslationMode.PYUVM
    
    runner = UVMTranslationRunner(
        mode=mode,
        use_llm=not args.no_llm,
        llm_provider=args.provider,
        verbose=args.verbose
    )
    
    # Run translation
    results = runner.translate(
        input_path=args.input,
        output_dir=args.output,
        validate=not args.no_validate,
        auto_fix=not args.no_fix
    )
    
    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    
    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()

