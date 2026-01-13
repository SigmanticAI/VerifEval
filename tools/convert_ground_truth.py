#!/usr/bin/env python3
"""
Convert various source formats to benchmark ground truth.

Usage:
    python convert_ground_truth.py --source opencores --input fifo_spec.txt --output requirements.json
    python convert_ground_truth.py --source testbench --input tb_file.sv --output requirements.json
    python convert_ground_truth.py --source paper --input paper.pdf --output requirements.json
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any


class GroundTruthConverter:
    """Convert various formats to benchmark ground truth JSON."""
    
    def __init__(self):
        self.requirements = []
        self.corner_cases = []
        self.assertions = []
        self.coverage = {}
    
    def from_opencores_doc(self, doc_text: str) -> Dict:
        """
        Extract ground truth from OpenCores documentation.
        
        Looks for patterns like:
        - "The FIFO shall..." → requirements
        - "must", "should" → requirement priorities
        - Test sections → corner cases
        """
        lines = doc_text.split('\n')
        
        req_id = 1
        for line in lines:
            line = line.strip()
            
            # Look for requirement statements
            if re.search(r'\b(shall|must|should)\b', line, re.IGNORECASE):
                priority = 'critical' if 'shall' in line.lower() or 'must' in line.lower() else 'high'
                
                self.requirements.append({
                    'id': f'REQ-{req_id:03d}',
                    'description': line,
                    'priority': priority,
                    'category': 'functional',
                    'test_required': True,
                    'assertion_required': 'shall' in line.lower()
                })
                req_id += 1
        
        return self._build_output()
    
    def from_testbench_code(self, sv_code: str) -> Dict:
        """
        Extract ground truth from existing SystemVerilog testbench.
        
        Extracts:
        - Test names → requirements
        - Assertions → required assertions
        - Coverage points → coverage requirements
        """
        # Extract test names
        tests = re.findall(r'task\s+(\w*test\w*)\s*\(', sv_code, re.IGNORECASE)
        for i, test_name in enumerate(tests, 1):
            # Convert test_name to requirement description
            desc = test_name.replace('_', ' ').replace('test', '').strip()
            self.requirements.append({
                'id': f'REQ-{i:03d}',
                'description': f'Verify {desc}',
                'priority': 'high',
                'category': 'functional',
                'test_required': True,
                'assertion_required': False
            })
        
        # Extract assertions
        assertions = re.findall(r'assert\s+property\s*\(\s*@?\s*\(?.*?\)?\s*(\w+)', sv_code)
        for assertion_name in set(assertions):
            self.assertions.append({
                'name': assertion_name,
                'description': f'Property: {assertion_name}',
                'property_type': 'safety'
            })
        
        # Extract covergroups
        covergroups = re.findall(r'covergroup\s+(\w+)', sv_code)
        if covergroups:
            self.coverage = {
                'code_coverage': 100,
                'functional_coverage': {
                    'covergroups': covergroups
                }
            }
        
        return self._build_output()
    
    def from_spec_document(self, spec_text: str) -> Dict:
        """
        Extract from specification document.
        
        Heuristics:
        - Numbered sections → requirements
        - "must", "shall" → critical requirements
        - "Corner case:", "Edge case:" → corner cases
        """
        lines = spec_text.split('\n')
        
        req_id = 1
        cc_id = 1
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Requirements
            if re.search(r'\b(shall|must|should|will)\b', line, re.IGNORECASE):
                priority = self._determine_priority(line)
                
                self.requirements.append({
                    'id': f'REQ-{req_id:03d}',
                    'description': line,
                    'priority': priority,
                    'category': self._determine_category(line),
                    'test_required': True,
                    'assertion_required': priority == 'critical'
                })
                req_id += 1
            
            # Corner cases
            if re.search(r'\b(corner case|edge case|boundary|limit)\b', line, re.IGNORECASE):
                self.corner_cases.append({
                    'id': f'CC-{cc_id:03d}',
                    'description': line,
                    'test_required': True
                })
                cc_id += 1
        
        return self._build_output()
    
    def from_verification_plan(self, plan_text: str) -> Dict:
        """
        Extract from existing verification plan document.
        
        Looks for:
        - Test plan sections
        - Assertion requirements
        - Coverage goals
        """
        lines = plan_text.split('\n')
        
        current_section = None
        req_id = 1
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if re.match(r'^#+\s*(test|assertion|coverage)', line, re.IGNORECASE):
                current_section = line.lower()
                continue
            
            # Extract based on section
            if 'test' in (current_section or ''):
                if line and not line.startswith('#'):
                    self.requirements.append({
                        'id': f'REQ-{req_id:03d}',
                        'description': line,
                        'priority': 'high',
                        'category': 'functional',
                        'test_required': True,
                        'assertion_required': False
                    })
                    req_id += 1
        
        return self._build_output()
    
    def _determine_priority(self, text: str) -> str:
        """Determine requirement priority from text."""
        text_lower = text.lower()
        if 'shall' in text_lower or 'must' in text_lower or 'critical' in text_lower:
            return 'critical'
        elif 'should' in text_lower or 'important' in text_lower:
            return 'high'
        else:
            return 'medium'
    
    def _determine_category(self, text: str) -> str:
        """Determine requirement category from text."""
        text_lower = text.lower()
        if 'timing' in text_lower or 'clock' in text_lower or 'delay' in text_lower:
            return 'timing'
        elif 'power' in text_lower:
            return 'power'
        else:
            return 'functional'
    
    def _build_output(self) -> Dict:
        """Build final ground truth JSON structure."""
        output = {}
        
        if self.requirements:
            output['functional_requirements'] = self.requirements
        
        if self.corner_cases:
            output['corner_cases'] = self.corner_cases
        
        if self.assertions:
            output['required_assertions'] = self.assertions
        
        if self.coverage:
            output['coverage_requirements'] = self.coverage
        
        return output
    
    def manual_entry_wizard(self) -> Dict:
        """Interactive wizard for manual ground truth creation."""
        print("=== Ground Truth Creation Wizard ===\n")
        
        # Get requirements
        print("Enter functional requirements (one per line, empty line to finish):")
        req_id = 1
        while True:
            desc = input(f"REQ-{req_id:03d}: ").strip()
            if not desc:
                break
            
            priority = input("  Priority (critical/high/medium) [high]: ").strip() or 'high'
            test_req = input("  Test required? (y/n) [y]: ").strip().lower() != 'n'
            assert_req = input("  Assertion required? (y/n) [n]: ").strip().lower() == 'y'
            
            self.requirements.append({
                'id': f'REQ-{req_id:03d}',
                'description': desc,
                'priority': priority,
                'category': 'functional',
                'test_required': test_req,
                'assertion_required': assert_req
            })
            req_id += 1
        
        # Get corner cases
        print("\nEnter corner cases (one per line, empty line to finish):")
        cc_id = 1
        while True:
            desc = input(f"CC-{cc_id:03d}: ").strip()
            if not desc:
                break
            
            self.corner_cases.append({
                'id': f'CC-{cc_id:03d}',
                'description': desc,
                'test_required': True
            })
            cc_id += 1
        
        # Get assertions
        print("\nEnter required assertions (one per line, empty line to finish):")
        while True:
            name = input("Assertion name: ").strip()
            if not name:
                break
            
            desc = input("  Description: ").strip()
            
            self.assertions.append({
                'name': name,
                'description': desc,
                'property_type': 'safety'
            })
        
        return self._build_output()


def main():
    parser = argparse.ArgumentParser(description='Convert source to ground truth JSON')
    parser.add_argument('--source', choices=['opencores', 'testbench', 'spec', 'plan', 'manual'],
                       required=True, help='Source type')
    parser.add_argument('--input', type=Path, help='Input file')
    parser.add_argument('--output', type=Path, required=True, help='Output JSON file')
    
    args = parser.parse_args()
    
    converter = GroundTruthConverter()
    
    if args.source == 'manual':
        result = converter.manual_entry_wizard()
    else:
        if not args.input or not args.input.exists():
            print(f"Error: Input file {args.input} not found")
            return 1
        
        with open(args.input) as f:
            content = f.read()
        
        if args.source == 'opencores':
            result = converter.from_opencores_doc(content)
        elif args.source == 'testbench':
            result = converter.from_testbench_code(content)
        elif args.source == 'spec':
            result = converter.from_spec_document(content)
        elif args.source == 'plan':
            result = converter.from_verification_plan(content)
    
    # Write output
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Ground truth written to {args.output}")
    print(f"   - {len(result.get('functional_requirements', []))} requirements")
    print(f"   - {len(result.get('corner_cases', []))} corner cases")
    print(f"   - {len(result.get('required_assertions', []))} assertions")


if __name__ == '__main__':
    main()

