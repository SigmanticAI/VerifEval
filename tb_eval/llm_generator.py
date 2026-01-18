"""
LLM-based testbench generator.

Supports multiple LLM providers (Anthropic Claude, OpenAI GPT).
"""

import os
import re
from typing import Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .config import DesignConfig, BenchmarkConfig, GENERATED_DIR
from .prompt_generator import (
    generate_cocotb_prompt, 
    generate_syntax_fix_prompt,
    save_prompt
)


class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class GenerationResult:
    """Result of testbench generation."""
    success: bool
    code: str
    iterations: int
    error_message: Optional[str] = None
    provider: Optional[str] = None


class LLMClient:
    """Client for interacting with LLMs."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.ANTHROPIC,
                 temperature: float = 0.7,
                 max_tokens: int = 8000):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        
    def _get_anthropic_client(self):
        """Get Anthropic client."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        import anthropic
        return anthropic.Anthropic()
    
    def _get_openai_client(self):
        """Get OpenAI client."""
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        import openai
        return openai.OpenAI()
    
    def generate(self, prompt: str) -> str:
        """Generate response from LLM."""
        
        if self.provider == LLMProvider.ANTHROPIC:
            client = self._get_anthropic_client()
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        elif self.provider == LLMProvider.OPENAI:
            client = self._get_openai_client()
            
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
        
        else:
            raise ValueError(f"Unknown provider: {self.provider}")


def extract_python_code(response: str) -> str:
    """Extract Python code from LLM response, handling markdown formatting."""
    
    # Try to extract from markdown code blocks
    patterns = [
        r'```python\n(.*?)```',
        r'```\n(.*?)```',
        r'```(.*?)```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            # Return the longest match (likely the main code)
            return max(matches, key=len).strip()
    
    # If no code blocks found, assume the whole response is code
    # Remove any leading/trailing markdown artifacts
    code = response.strip()
    if code.startswith('```'):
        code = code.split('\n', 1)[1] if '\n' in code else code[3:]
    if code.endswith('```'):
        code = code.rsplit('```', 1)[0]
    
    return code.strip()


def validate_python_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """Validate Python syntax without executing."""
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


class TestbenchGenerator:
    """Generate cocotb testbenches using LLMs."""
    
    def __init__(self, config: BenchmarkConfig = None,
                 provider: str = "anthropic"):
        self.config = config or BenchmarkConfig()
        self.provider = LLMProvider(provider)
        self.client = LLMClient(
            provider=self.provider,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
    
    def generate_testbench(self, design: DesignConfig, 
                          run_id: int = 1) -> GenerationResult:
        """
        Generate a testbench for the given design.
        
        Implements iterative refinement as per the paper:
        - Generate initial testbench
        - If syntax errors, iterate up to max_iterations times
        """
        
        # Generate initial prompt
        prompt = generate_cocotb_prompt(design)
        save_prompt(design.name, prompt, f"initial_run{run_id}")
        
        print(f"  Generating testbench for {design.name} (run {run_id})...")
        
        # Generate initial code
        try:
            response = self.client.generate(prompt)
            code = extract_python_code(response)
        except Exception as e:
            return GenerationResult(
                success=False,
                code="",
                iterations=0,
                error_message=f"LLM generation failed: {str(e)}",
                provider=self.provider.value
            )
        
        # Validate and iterate if needed
        iteration = 1
        while iteration <= self.config.max_iterations:
            is_valid, error = validate_python_syntax(code)
            
            if is_valid:
                # Save successful generation
                output_dir = GENERATED_DIR / design.name / f"run_{run_id}"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                tb_file = output_dir / f"test_{design.name}.py"
                tb_file.write_text(code)
                
                print(f"    ✓ Generated successfully after {iteration} iteration(s)")
                
                return GenerationResult(
                    success=True,
                    code=code,
                    iterations=iteration,
                    provider=self.provider.value
                )
            
            if iteration >= self.config.max_iterations:
                break
                
            # Generate fix prompt
            print(f"    Iteration {iteration}: Syntax error, requesting fix...")
            fix_prompt = generate_syntax_fix_prompt(code, error, iteration)
            save_prompt(design.name, fix_prompt, f"fix_run{run_id}_iter{iteration}")
            
            try:
                response = self.client.generate(fix_prompt)
                code = extract_python_code(response)
            except Exception as e:
                return GenerationResult(
                    success=False,
                    code=code,
                    iterations=iteration,
                    error_message=f"LLM fix generation failed: {str(e)}",
                    provider=self.provider.value
                )
            
            iteration += 1
        
        # Failed after max iterations
        return GenerationResult(
            success=False,
            code=code,
            iterations=iteration,
            error_message=f"Failed to fix syntax errors after {self.config.max_iterations} iterations: {error}",
            provider=self.provider.value
        )
    
    def generate_multiple_runs(self, design: DesignConfig,
                               num_runs: int = 5) -> list:
        """
        Generate multiple testbench runs for statistical analysis.
        
        As per the paper, each design is tested with multiple LLM runs
        to get build success rates and coverage statistics.
        """
        
        results = []
        
        for run_id in range(1, num_runs + 1):
            result = self.generate_testbench(design, run_id)
            results.append(result)
        
        return results

