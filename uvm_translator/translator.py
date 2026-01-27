"""
UVM to Python/cocotb Translator.

Uses LLM (Claude/OpenAI) to translate UVM SystemVerilog testbenches
to Python cocotb/pyuvm testbenches that can run on open-source simulators.
"""

import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from .parser import UVMParser, ParseResult, UVMComponent, UVMComponentType
from .analyzer import UVMAnalyzer, UVMTestbenchStructure


class TranslationMode(Enum):
    """Translation target mode."""
    COCOTB = "cocotb"      # Pure cocotb (simpler, more portable)
    PYUVM = "pyuvm"        # pyuvm (UVM methodology in Python)


@dataclass
class TranslatedFile:
    """A single translated Python file."""
    filename: str
    content: str
    file_type: str  # test, driver, monitor, transaction, etc.
    source_files: List[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """Result of UVM to Python translation."""
    success: bool
    mode: TranslationMode
    files: List[TranslatedFile] = field(default_factory=list)
    output_dir: Optional[Path] = None
    
    # Metadata
    source_structure: Optional[UVMTestbenchStructure] = None
    translation_time_ms: float = 0.0
    llm_tokens_used: int = 0
    
    # Diagnostics
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'mode': self.mode.value,
            'files': [
                {'filename': f.filename, 'file_type': f.file_type, 'source_files': f.source_files}
                for f in self.files
            ],
            'output_dir': str(self.output_dir) if self.output_dir else None,
            'translation_time_ms': self.translation_time_ms,
            'llm_tokens_used': self.llm_tokens_used,
            'errors': self.errors,
            'warnings': self.warnings,
            'notes': self.notes
        }


class LLMClient:
    """
    Unified LLM client supporting Claude and OpenAI.
    """
    
    def __init__(self, provider: str = "anthropic", model: str = None):
        self.provider = provider.lower()
        self.model = model
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic()
                self.model = self.model or "claude-sonnet-4-20250514"
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        elif self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI()
                self.model = self.model or "gpt-4-turbo-preview"
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def generate(self, system_prompt: str, user_prompt: str, 
                 max_tokens: int = 8192) -> Tuple[str, int]:
        """
        Generate response from LLM.
        
        Returns:
            Tuple of (response_text, tokens_used)
        """
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            text = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return text, tokens
        
        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            text = response.choices[0].message.content
            tokens = response.usage.total_tokens
            return text, tokens
        
        return "", 0


class UVMTranslator:
    """
    Main translator for UVM-SV to Python/cocotb.
    
    Uses LLM to translate UVM testbenches while preserving
    verification intent and test scenarios.
    """
    
    # System prompt for translation
    SYSTEM_PROMPT = """You are an expert verification engineer specializing in translating 
UVM (Universal Verification Methodology) SystemVerilog testbenches to Python-based 
verification using cocotb and pyuvm frameworks.

Your task is to translate UVM testbench code to equivalent Python code that:
1. Preserves the verification intent and test scenarios
2. Maintains functional equivalence where possible
3. Uses cocotb primitives (Clock, triggers, coroutines) correctly
4. Follows Python best practices and is well-documented
5. Can run on open-source simulators (Verilator, Icarus)

Key translation mappings:
- UVM sequence_item → Python dataclass with fields
- UVM driver → cocotb coroutine that drives DUT signals
- UVM monitor → cocotb coroutine that samples DUT signals
- UVM sequence → async function that generates transactions
- UVM scoreboard → Python class with comparison logic
- Constraints → Python random with bounds checking
- Virtual interface → dut handle passed to coroutines

Output format:
- Return complete, runnable Python code
- Include all necessary imports
- Add clear comments explaining the translation
- Use type hints where appropriate"""

    def __init__(self, 
                 mode: TranslationMode = TranslationMode.COCOTB,
                 llm_provider: str = "anthropic",
                 llm_model: str = None):
        """
        Initialize translator.
        
        Args:
            mode: Translation target (cocotb or pyuvm)
            llm_provider: LLM provider (anthropic or openai)
            llm_model: Specific model to use (optional)
        """
        self.mode = mode
        self.parser = UVMParser()
        self.analyzer = UVMAnalyzer()
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        self.total_tokens = 0
    
    def translate_project(self, 
                         project_dir: Path,
                         output_dir: Optional[Path] = None) -> TranslationResult:
        """
        Translate a complete UVM project to Python/cocotb.
        
        Args:
            project_dir: Directory containing UVM testbench files
            output_dir: Output directory for translated files
            
        Returns:
            TranslationResult with translated files
        """
        start_time = time.time()
        result = TranslationResult(success=False, mode=self.mode)
        
        # Set output directory
        if output_dir is None:
            output_dir = project_dir / "translated_cocotb"
        result.output_dir = output_dir
        
        try:
            # Step 1: Parse UVM files
            parse_result = self.parser.parse_project(project_dir)
            
            if parse_result.errors:
                result.errors.extend(parse_result.errors)
            
            if not parse_result.components and not parse_result.interfaces:
                result.errors.append("No UVM components found in project")
                return result
            
            # Step 2: Analyze structure
            structure = self.analyzer.analyze(parse_result)
            structure.project_name = project_dir.name
            result.source_structure = structure
            result.warnings.extend(structure.warnings)
            result.notes.extend(structure.translation_notes)
            
            # Step 3: Generate translated files
            translated_files = self._translate_structure(structure, parse_result)
            result.files.extend(translated_files)
            
            # Step 4: Generate support files
            support_files = self._generate_support_files(structure)
            result.files.extend(support_files)
            
            # Step 5: Write files to output directory
            self._write_files(result.files, output_dir)
            
            result.success = True
            result.llm_tokens_used = self.total_tokens
            
        except Exception as e:
            result.errors.append(f"Translation failed: {str(e)}")
        
        result.translation_time_ms = (time.time() - start_time) * 1000
        return result
    
    def translate_file(self, file_path: Path) -> TranslationResult:
        """
        Translate a single UVM file.
        
        Args:
            file_path: Path to .sv file
            
        Returns:
            TranslationResult with translated content
        """
        start_time = time.time()
        result = TranslationResult(success=False, mode=self.mode)
        
        try:
            # Parse file
            parse_result = self.parser.parse_file(file_path)
            
            # Analyze
            structure = self.analyzer.analyze(parse_result)
            structure.project_name = file_path.stem
            result.source_structure = structure
            
            # Translate
            translated_files = self._translate_structure(structure, parse_result)
            result.files.extend(translated_files)
            
            result.success = True
            result.llm_tokens_used = self.total_tokens
            
        except Exception as e:
            result.errors.append(f"Translation failed: {str(e)}")
        
        result.translation_time_ms = (time.time() - start_time) * 1000
        return result
    
    def _translate_structure(self, structure: UVMTestbenchStructure,
                            parse_result: ParseResult) -> List[TranslatedFile]:
        """Translate the analyzed structure to Python files."""
        files = []
        
        # Translate transactions first (they're referenced by other components)
        for trans in structure.transactions:
            trans_file = self._translate_transaction(trans, structure)
            if trans_file:
                files.append(trans_file)
        
        # Translate main test file
        test_file = self._translate_test(structure, parse_result)
        if test_file:
            files.append(test_file)
        
        # Translate sequences
        for seq in structure.sequences:
            seq_file = self._translate_sequence(seq, structure)
            if seq_file:
                files.append(seq_file)
        
        return files
    
    def _translate_transaction(self, trans, structure) -> Optional[TranslatedFile]:
        """Translate a UVM transaction/sequence_item to Python dataclass."""
        prompt = f"""Translate this UVM sequence_item to a Python dataclass:

UVM Transaction Name: {trans.name}
Fields: {json.dumps(trans.fields, indent=2)}
Constraints: {json.dumps(trans.constraints, indent=2)}

Requirements:
1. Create a Python dataclass with appropriate fields
2. Add a randomize() method that respects constraints
3. Include type hints
4. Add __str__ method for debugging

Return ONLY the Python code, no explanations."""

        try:
            response, tokens = self.llm.generate(self.SYSTEM_PROMPT, prompt)
            self.total_tokens += tokens
            
            # Extract code from response
            code = self._extract_code(response)
            
            return TranslatedFile(
                filename=f"{self._to_snake_case(trans.name)}.py",
                content=code,
                file_type="transaction"
            )
        except Exception as e:
            return None
    
    def _translate_test(self, structure: UVMTestbenchStructure,
                       parse_result: ParseResult) -> Optional[TranslatedFile]:
        """Translate the main UVM test to cocotb test file."""
        
        # Gather all source code for context
        source_code = ""
        for comp in parse_result.components:
            if comp.raw_source:
                source_code += f"\n// {comp.name}\n{comp.raw_source}\n"
        
        # Build interface info
        interface_info = ""
        if structure.interface_signals:
            signals = [f"  - {s.name}: {s.direction}, width={s.width}" 
                      for s in structure.interface_signals[:20]]  # Limit for prompt
            interface_info = "\n".join(signals)
        
        prompt = f"""Translate this UVM testbench to a cocotb Python testbench:

PROJECT INFO:
- DUT Name: {structure.dut_name}
- Clock Signal: {structure.clock_signal}
- Reset Signal: {structure.reset_signal} (active_low={structure.reset_active_low})
- Clock Period: {structure.clock_period_ns}ns

INTERFACE SIGNALS:
{interface_info}

TRANSACTIONS:
{json.dumps([t.name for t in structure.transactions])}

SEQUENCES:
{json.dumps([s.name for s in structure.sequences])}

AGENTS:
{json.dumps([a.name for a in structure.agents])}

SOURCE CODE:
{source_code[:8000]}  # Truncated for context window

Generate a complete cocotb testbench with:
1. Proper imports (cocotb, Clock, triggers)
2. Reset coroutine
3. Driver coroutine(s) for driving signals
4. Monitor coroutine(s) for sampling signals  
5. Multiple @cocotb.test() decorated test functions covering:
   - Reset behavior
   - Basic operations
   - Edge cases
   - Random stimulus
6. Reference model/scoreboard logic where applicable

Return ONLY the Python code."""

        try:
            response, tokens = self.llm.generate(self.SYSTEM_PROMPT, prompt, max_tokens=16384)
            self.total_tokens += tokens
            
            code = self._extract_code(response)
            
            return TranslatedFile(
                filename="test_dut.py",
                content=code,
                file_type="test",
                source_files=[str(f) for f in structure.source_files]
            )
        except Exception as e:
            # Return a basic template on failure
            return TranslatedFile(
                filename="test_dut.py",
                content=self._get_basic_test_template(structure),
                file_type="test"
            )
    
    def _translate_sequence(self, seq, structure) -> Optional[TranslatedFile]:
        """Translate a UVM sequence to Python async function."""
        prompt = f"""Translate this UVM sequence to a Python async function for cocotb:

Sequence Name: {seq.name}
Transaction Type: {seq.transaction_type}
Body Logic: {seq.body_logic[:2000] if seq.body_logic else 'N/A'}

Requirements:
1. Create an async function that generates transactions
2. Use Python random for randomization
3. Yield transactions or drive signals directly
4. Include proper async/await syntax for cocotb

Return ONLY the Python code."""

        try:
            response, tokens = self.llm.generate(self.SYSTEM_PROMPT, prompt)
            self.total_tokens += tokens
            
            code = self._extract_code(response)
            
            return TranslatedFile(
                filename=f"{self._to_snake_case(seq.name)}.py",
                content=code,
                file_type="sequence"
            )
        except Exception:
            return None
    
    def _generate_support_files(self, structure: UVMTestbenchStructure) -> List[TranslatedFile]:
        """Generate support files (Makefile, conftest.py, etc.)."""
        files = []
        
        # Makefile for cocotb
        makefile = self._generate_makefile(structure)
        files.append(TranslatedFile(
            filename="Makefile",
            content=makefile,
            file_type="build"
        ))
        
        # conftest.py for pytest integration
        conftest = self._generate_conftest(structure)
        files.append(TranslatedFile(
            filename="conftest.py",
            content=conftest,
            file_type="config"
        ))
        
        return files
    
    def _generate_makefile(self, structure: UVMTestbenchStructure) -> str:
        """Generate Makefile for cocotb simulation."""
        dut_name = structure.dut_name or "dut"
        
        return f'''# Makefile for cocotb simulation
# Auto-generated by UVM Translator

# Simulator selection (verilator or icarus)
SIM ?= verilator

# DUT toplevel
TOPLEVEL = {dut_name}
TOPLEVEL_LANG = verilog

# Verilog sources - add your DUT files here
VERILOG_SOURCES = $(shell find ../rtl -name "*.v" -o -name "*.sv" 2>/dev/null)

# cocotb test module
MODULE = test_dut

# Verilator-specific settings
ifeq ($(SIM),verilator)
    EXTRA_ARGS += --trace --trace-fst
    EXTRA_ARGS += --coverage
    EXTRA_ARGS += -Wno-fatal
endif

# Icarus-specific settings
ifeq ($(SIM),icarus)
    COMPILE_ARGS += -g2012
endif

# Include cocotb makefile
include $(shell cocotb-config --makefiles)/Makefile.sim

# Coverage report target
coverage:
\tverilator_coverage --annotate logs/annotated coverage.dat

# Clean target
clean::
\trm -rf __pycache__ results.xml *.vcd *.fst coverage.dat
\trm -rf obj_dir sim_build logs

.PHONY: coverage clean
'''
    
    def _generate_conftest(self, structure: UVMTestbenchStructure) -> str:
        """Generate pytest conftest.py."""
        return '''"""
Pytest configuration for cocotb tests.
Auto-generated by UVM Translator.
"""

import pytest


def pytest_configure(config):
    """Configure pytest for cocotb."""
    config.addinivalue_line(
        "markers", "cocotb: mark test as cocotb test"
    )


@pytest.fixture
def dut_params():
    """Default DUT parameters."""
    return {
        "DATA_WIDTH": 8,
        "DEPTH": 16,
    }
'''
    
    def _get_basic_test_template(self, structure: UVMTestbenchStructure) -> str:
        """Get a basic cocotb test template when LLM translation fails."""
        clock = structure.clock_signal or "clk"
        reset = structure.reset_signal or "rst_n"
        active_low = structure.reset_active_low
        
        return f'''"""
cocotb testbench for {structure.dut_name or 'DUT'}
Auto-generated by UVM Translator.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer
import random


async def reset_dut(dut):
    """Apply reset to DUT."""
    dut.{reset}.value = {'0' if active_low else '1'}
    await ClockCycles(dut.{clock}, 5)
    dut.{reset}.value = {'1' if active_low else '0'}
    await RisingEdge(dut.{clock})


@cocotb.test()
async def test_reset(dut):
    """Test reset behavior."""
    cocotb.start_soon(Clock(dut.{clock}, 10, units='ns').start())
    await reset_dut(dut)
    
    # Add reset assertions here
    cocotb.log.info("Reset test completed")


@cocotb.test()
async def test_basic_operation(dut):
    """Test basic DUT operation."""
    cocotb.start_soon(Clock(dut.{clock}, 10, units='ns').start())
    await reset_dut(dut)
    
    # Add basic operation tests here
    for _ in range(10):
        await RisingEdge(dut.{clock})
    
    cocotb.log.info("Basic operation test completed")


@cocotb.test()
async def test_random_stimulus(dut):
    """Test with random stimulus."""
    cocotb.start_soon(Clock(dut.{clock}, 10, units='ns').start())
    await reset_dut(dut)
    
    # Reference model for checking
    expected_results = []
    
    for i in range(50):
        # Generate random stimulus
        # TODO: Customize for your DUT signals
        await RisingEdge(dut.{clock})
    
    cocotb.log.info("Random stimulus test completed")
'''
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Look for code blocks
        import re
        
        # Try to find ```python ... ``` blocks
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return '\n\n'.join(matches)
        
        # If no code blocks, return the response as-is
        # (assuming it's already code)
        return response.strip()
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _write_files(self, files: List[TranslatedFile], output_dir: Path) -> None:
        """Write translated files to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file in files:
            file_path = output_dir / file.filename
            with open(file_path, 'w') as f:
                f.write(file.content)

