#!/usr/bin/env python3
"""
Evaluation metrics for VerifAgent benchmark.
Compares generated verification against ground truth.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    """Results from evaluating a single design."""
    design_name: str
    total_score: float = 0.0
    max_score: float = 100.0
    
    # Dimension scores
    spec_extraction_score: float = 0.0
    verification_planning_score: float = 0.0
    code_generation_score: float = 0.0
    verification_completeness_score: float = 0.0
    
    # Detailed metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Bug detection bonus
    bugs_detected: int = 0
    total_bugs: int = 0
    bonus_score: float = 0.0
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'design_name': self.design_name,
            'total_score': round(self.total_score, 2),
            'max_score': self.max_score,
            'dimension_scores': {
                'specification_extraction': round(self.spec_extraction_score, 2),
                'verification_planning': round(self.verification_planning_score, 2),
                'code_generation': round(self.code_generation_score, 2),
                'verification_completeness': round(self.verification_completeness_score, 2),
            },
            'bug_detection': {
                'detected': self.bugs_detected,
                'total': self.total_bugs,
                'bonus_score': round(self.bonus_score, 2),
            },
            'metrics': self.metrics,
            'errors': self.errors,
            'warnings': self.warnings,
        }


class SpecificationExtractor:
    """Evaluates specification extraction quality."""
    
    @staticmethod
    def evaluate(generated_spec: Dict, reference_spec: Dict, config: Dict) -> Tuple[float, Dict]:
        """
        Evaluate specification extraction.
        
        Returns:
            (score, detailed_metrics)
        """
        criteria = config['specification_extraction']
        score = 0.0
        metrics = {}
        
        # Module detection
        gen_modules = {m['name'] for m in generated_spec.get('modules', [])}
        req_modules = set(criteria['module_detection']['required'])
        module_match = len(gen_modules & req_modules) / len(req_modules) if req_modules else 0
        module_score = module_match * criteria['module_detection']['points']
        score += module_score
        metrics['module_detection'] = {
            'score': round(module_score, 2),
            'max': criteria['module_detection']['points'],
            'found': list(gen_modules),
            'required': list(req_modules),
        }
        
        # Port identification
        gen_ports = set()
        for module in generated_spec.get('modules', []):
            gen_ports.update(p['name'] for p in module.get('ports', []))
        
        req_ports = set(criteria['port_identification']['required_ports'])
        opt_ports = set(criteria['port_identification'].get('optional_ports', []))
        
        required_match = len(gen_ports & req_ports) / len(req_ports) if req_ports else 0
        optional_match = len(gen_ports & opt_ports) / len(opt_ports) if opt_ports else 0
        port_score = (required_match * 0.8 + optional_match * 0.2) * criteria['port_identification']['points']
        score += port_score
        metrics['port_identification'] = {
            'score': round(port_score, 2),
            'max': criteria['port_identification']['points'],
            'required_match': round(required_match, 2),
            'optional_match': round(optional_match, 2),
        }
        
        # Parameter detection
        gen_params = set()
        for module in generated_spec.get('modules', []):
            gen_params.update(p['name'] for p in module.get('parameters', []))
        
        req_params = set(criteria['parameter_detection']['required'])
        param_match = len(gen_params & req_params) / len(req_params) if req_params else 0
        param_score = param_match * criteria['parameter_detection']['points']
        score += param_score
        metrics['parameter_detection'] = {
            'score': round(param_score, 2),
            'max': criteria['parameter_detection']['points'],
            'match_rate': round(param_match, 2),
        }
        
        # Requirements extraction
        gen_reqs = generated_spec.get('requirements', [])
        min_reqs = criteria['requirements_extraction']['minimum_requirements']
        critical_reqs = criteria['requirements_extraction']['critical_requirements']
        
        # Count requirements
        req_count_score = min(len(gen_reqs) / min_reqs, 1.0) * (criteria['requirements_extraction']['points'] * 0.5)
        
        # Check for critical requirements (fuzzy match)
        critical_found = 0
        for critical_req in critical_reqs:
            for gen_req in gen_reqs:
                if SpecificationExtractor._fuzzy_match(critical_req, gen_req.get('description', '')):
                    critical_found += 1
                    break
        
        critical_score = (critical_found / len(critical_reqs)) * (criteria['requirements_extraction']['points'] * 0.5)
        req_score = req_count_score + critical_score
        score += req_score
        metrics['requirements_extraction'] = {
            'score': round(req_score, 2),
            'max': criteria['requirements_extraction']['points'],
            'total_requirements': len(gen_reqs),
            'minimum_required': min_reqs,
            'critical_found': critical_found,
            'critical_total': len(critical_reqs),
        }
        
        return score, metrics
    
    @staticmethod
    def _fuzzy_match(needle: str, haystack: str, threshold: float = 0.5) -> bool:
        """Simple fuzzy matching for requirement descriptions."""
        needle = needle.lower()
        haystack = haystack.lower()
        words = needle.split()
        matches = sum(1 for word in words if word in haystack)
        return (matches / len(words)) >= threshold if words else False


class VerificationPlanner:
    """Evaluates verification plan quality."""
    
    @staticmethod
    def evaluate(generated_plan: Dict, reference: Dict, config: Dict) -> Tuple[float, Dict]:
        """Evaluate verification planning."""
        criteria = config['verification_planning']
        score = 0.0
        metrics = {}
        
        # Test coverage
        test_categories = generated_plan.get('test_categories', [])
        total_tests = sum(len(cat.get('tests', [])) for cat in test_categories)
        min_tests = criteria['test_coverage']['minimum_tests']
        
        test_count_score = min(total_tests / min_tests, 1.0) * (criteria['test_coverage']['points'] * 0.6)
        
        # Check for required test categories
        gen_categories = {cat['name'].lower() for cat in test_categories}
        req_categories = {cat.lower() for cat in criteria['test_coverage']['required_test_categories']}
        category_match = len(gen_categories & req_categories) / len(req_categories) if req_categories else 0
        category_score = category_match * (criteria['test_coverage']['points'] * 0.4)
        
        test_score = test_count_score + category_score
        score += test_score
        metrics['test_coverage'] = {
            'score': round(test_score, 2),
            'max': criteria['test_coverage']['points'],
            'total_tests': total_tests,
            'category_match': round(category_match, 2),
        }
        
        # Assertion planning
        assertions = generated_plan.get('assertions', [])
        min_assertions = criteria['assertion_planning']['minimum_assertions']
        critical_assertions = criteria['assertion_planning']['critical_assertions']
        
        assertion_count_score = min(len(assertions) / min_assertions, 1.0) * (criteria['assertion_planning']['points'] * 0.5)
        
        # Check for critical assertions
        critical_found = 0
        for critical_name in critical_assertions:
            for assertion in assertions:
                if VerificationPlanner._fuzzy_match(critical_name, assertion.get('name', '')):
                    critical_found += 1
                    break
        
        critical_assertion_score = (critical_found / len(critical_assertions)) * (criteria['assertion_planning']['points'] * 0.5)
        assertion_score = assertion_count_score + critical_assertion_score
        score += assertion_score
        metrics['assertion_planning'] = {
            'score': round(assertion_score, 2),
            'max': criteria['assertion_planning']['points'],
            'total_assertions': len(assertions),
            'critical_found': critical_found,
        }
        
        # Coverage strategy
        covergroups = generated_plan.get('covergroups', [])
        req_covergroups = criteria['coverage_strategy']['required_covergroups']
        
        cg_found = 0
        for req_cg in req_covergroups:
            for cg in covergroups:
                if VerificationPlanner._fuzzy_match(req_cg, cg.get('name', '')):
                    cg_found += 1
                    break
        
        coverage_score = (cg_found / len(req_covergroups)) * criteria['coverage_strategy']['points']
        score += coverage_score
        metrics['coverage_strategy'] = {
            'score': round(coverage_score, 2),
            'max': criteria['coverage_strategy']['points'],
            'covergroups_found': cg_found,
        }
        
        return score, metrics
    
    @staticmethod
    def _fuzzy_match(needle: str, haystack: str) -> bool:
        """Fuzzy match for test/assertion names."""
        needle = needle.lower().replace('_', ' ').replace('-', ' ')
        haystack = haystack.lower().replace('_', ' ').replace('-', ' ')
        return needle in haystack or haystack in needle


class CodeQualityChecker:
    """Evaluates generated code quality."""
    
    @staticmethod
    def evaluate(output_dir: Path, config: Dict) -> Tuple[float, Dict]:
        """Evaluate code generation quality."""
        criteria = config['code_generation']
        score = 0.0
        metrics = {}
        
        # Compilability (basic syntax check)
        sv_files = list(output_dir.rglob('*.sv'))
        compilable_count = 0
        syntax_errors = []
        
        for sv_file in sv_files:
            try:
                content = sv_file.read_text()
                # Basic syntax checks
                if CodeQualityChecker._basic_syntax_check(content):
                    compilable_count += 1
                else:
                    syntax_errors.append(str(sv_file))
            except Exception as e:
                syntax_errors.append(f"{sv_file}: {e}")
        
        compile_rate = compilable_count / len(sv_files) if sv_files else 0
        compile_score = compile_rate * criteria['compilability']['points']
        score += compile_score
        metrics['compilability'] = {
            'score': round(compile_score, 2),
            'max': criteria['compilability']['points'],
            'files_total': len(sv_files),
            'files_compilable': compilable_count,
            'syntax_errors': syntax_errors,
        }
        
        # UVM compliance
        uvm_components = criteria['uvm_compliance']['required_components']
        components_found = CodeQualityChecker._check_uvm_components(output_dir, uvm_components)
        uvm_score = (len(components_found) / len(uvm_components)) * criteria['uvm_compliance']['points']
        score += uvm_score
        metrics['uvm_compliance'] = {
            'score': round(uvm_score, 2),
            'max': criteria['uvm_compliance']['points'],
            'components_found': components_found,
        }
        
        # Code quality (simplified)
        quality_score = criteria['code_quality']['points'] * 0.8  # Default good score
        metrics['code_quality'] = {
            'score': round(quality_score, 2),
            'max': criteria['code_quality']['points'],
        }
        score += quality_score
        
        # Interface correctness (basic check)
        interface_score = criteria['interface_correctness']['points'] * 0.8
        metrics['interface_correctness'] = {
            'score': round(interface_score, 2),
            'max': criteria['interface_correctness']['points'],
        }
        score += interface_score
        
        return score, metrics
    
    @staticmethod
    def _basic_syntax_check(content: str) -> bool:
        """Basic SystemVerilog syntax validation."""
        # Check for balanced begin/end
        begin_count = len(re.findall(r'\bbegin\b', content))
        end_count = len(re.findall(r'\bend\b', content))
        if begin_count != end_count:
            return False
        
        # Check for balanced parentheses/brackets
        if content.count('(') != content.count(')'):
            return False
        if content.count('[') != content.count(']'):
            return False
        if content.count('{') != content.count('}'):
            return False
        
        return True
    
    @staticmethod
    def _check_uvm_components(output_dir: Path, required: List[str]) -> List[str]:
        """Check for UVM component patterns in generated files."""
        found = []
        all_content = ""
        
        for sv_file in output_dir.rglob('*.sv'):
            try:
                all_content += sv_file.read_text()
            except:
                pass
        
        patterns = {
            'interface': r'interface\s+\w+_if',
            'agent': r'class\s+\w+_agent\s+extends\s+uvm_agent',
            'sequence': r'class\s+\w+_sequence\s+extends\s+uvm_sequence',
            'test': r'class\s+\w+_test\s+extends\s+uvm_test',
        }
        
        for component in required:
            if component in patterns:
                if re.search(patterns[component], all_content):
                    found.append(component)
        
        return found


class CompletenessEvaluator:
    """Evaluates verification completeness."""
    
    @staticmethod
    def evaluate(generated_plan: Dict, reference: Dict, config: Dict) -> Tuple[float, Dict]:
        """Evaluate verification completeness."""
        criteria = config['verification_completeness']
        score = 0.0
        metrics = {}
        
        # Requirement coverage
        gen_reqs = set()
        for cat in generated_plan.get('test_categories', []):
            for test in cat.get('tests', []):
                # Extract requirement references from test descriptions
                desc = test.get('description', '').upper()
                gen_reqs.update(re.findall(r'REQ-\d+', desc))
        
        ref_reqs = {req['id'] for req in reference.get('functional_requirements', [])}
        req_coverage = len(gen_reqs & ref_reqs) / len(ref_reqs) if ref_reqs else 0
        req_score = min(req_coverage / criteria['requirement_coverage']['target'], 1.0) * criteria['requirement_coverage']['points']
        score += req_score
        metrics['requirement_coverage'] = {
            'score': round(req_score, 2),
            'max': criteria['requirement_coverage']['points'],
            'coverage': round(req_coverage, 2),
        }
        
        # Assertion coverage
        gen_assertions = {a['name'] for a in generated_plan.get('assertions', [])}
        ref_assertions = {a['name'] for a in reference.get('required_assertions', [])}
        
        assertion_matches = 0
        for ref_name in ref_assertions:
            for gen_name in gen_assertions:
                if CompletenessEvaluator._fuzzy_match(ref_name, gen_name):
                    assertion_matches += 1
                    break
        
        assertion_coverage = assertion_matches / len(ref_assertions) if ref_assertions else 0
        assertion_score = min(assertion_coverage / criteria['assertion_coverage']['target'], 1.0) * criteria['assertion_coverage']['points']
        score += assertion_score
        metrics['assertion_coverage'] = {
            'score': round(assertion_score, 2),
            'max': criteria['assertion_coverage']['points'],
            'coverage': round(assertion_coverage, 2),
        }
        
        # Functional coverage
        gen_cgs = generated_plan.get('covergroups', [])
        cg_score = min(len(gen_cgs) / 4, 1.0) * criteria['functional_coverage']['points']  # Expect at least 4
        score += cg_score
        metrics['functional_coverage'] = {
            'score': round(cg_score, 2),
            'max': criteria['functional_coverage']['points'],
            'covergroups': len(gen_cgs),
        }
        
        # Corner case coverage
        ref_corners = {cc['id'] for cc in reference.get('corner_cases', [])}
        gen_corners = set()
        
        # Extract corner case mentions from tests
        for cat in generated_plan.get('test_categories', []):
            for test in cat.get('tests', []):
                desc = test.get('description', '').upper()
                gen_corners.update(re.findall(r'CC-\d+', desc))
        
        corner_coverage = len(gen_corners & ref_corners) / len(ref_corners) if ref_corners else 0
        corner_score = min(corner_coverage / criteria['corner_case_coverage']['target'], 1.0) * criteria['corner_case_coverage']['points']
        score += corner_score
        metrics['corner_case_coverage'] = {
            'score': round(corner_score, 2),
            'max': criteria['corner_case_coverage']['points'],
            'coverage': round(corner_coverage, 2),
        }
        
        return score, metrics
    
    @staticmethod
    def _fuzzy_match(needle: str, haystack: str) -> bool:
        """Fuzzy match for assertion names."""
        needle = needle.lower().replace('_', ' ')
        haystack = haystack.lower().replace('_', ' ')
        return needle in haystack or haystack in needle

