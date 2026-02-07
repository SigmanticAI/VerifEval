```markdown
# Architecture Documentation

**Audience**: Team members, contributors, maintainers

**Purpose**: Understand system design, data flow, and implementation decisions

## Table of Contents

- [System Overview](#system-overview)
- [Data Flow](#data-flow)
- [Component Architecture](#component-architecture)
- [Design Decisions](#design-decisions)
- [Extension Points](#extension-points)
- [Performance Considerations](#performance-considerations)

---

## System Overview

Step 5 Coverage Analysis is the bridge between test execution (Step 4) and scoring (Step 7). It processes raw coverage data from multiple formats, calculates comprehensive metrics, and generates structured reports.

### Key Responsibilities
1. **Coverage Ingestion**: Parse multiple coverage formats
2. **Metric Calculation**: Compute line, branch, toggle, FSM coverage
3. **Per-test Analysis**: Track unique contributions per test
4. **Report Generation**: Create structured JSON for downstream consumption
5. **Quality Assessment**: Validate against thresholds

### Design Principles
- **Modularity**: Clear separation between parsing, calculation, and reporting
- **Extensibility**: Easy to add new coverage formats
- **Robustness**: Graceful degradation (external tool → Python fallback)
- **Performance**: Lazy evaluation, streaming where possible
- **Testing**: Comprehensive unit and integration tests

---

## Data Flow
┌─────────────────────────────────────────────────────────────────┐
│ INPUTS                                                           │
├─────────────────────────────────────────────────────────────────┤
│ test_report.json (Step 4)                                       │
│   ├─→ Test results with coverage_file paths                     │
│   └─→ Test durations for efficiency analysis                    │
│                                                                  │
│ build_manifest.json (Step 3)                                    │
│   ├─→ Source file list                                          │
│   └─→ Build configuration                                       │
│                                                                  │
│ Coverage Files (multiple formats)                               │
│   ├─→ Verilator: coverage_*.dat                                 │
│   ├─→ LCOV: *.info, *.lcov                                      │
│   └─→ Covered: .cdd                                            │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: COVERAGE ANALYSIS                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. FORMAT DETECTION (parsers/format_detector.py)                │
│    ├─→ Try parsers in priority order                            │
│    └─→ Return first matching parser                             │
│                                                                  │
│ 2. COVERAGE PARSING (parsers/.py)                              │
│    ├─→ Try external tool (verilator_coverage, lcov)             │
│    └─→ Fallback to Python parsing                               │
│                                                                  │
│ 3. METRIC CALCULATION (metrics/calculator.py)                   │
│    ├─→ Calculate line/branch/toggle/FSM coverage                │
│    ├─→ Identify uncovered hotspots                              │
│    └─→ Compute weighted score                                   │
│                                                                  │
│ 4. PER-TEST MERGING (metrics/merger.py)                         │
│    ├─→ Track unique vs overlapping coverage                     │
│    ├─→ Calculate test efficiency/redundancy                     │
│    ├─→ Determine optimal test order                             │
│    └─→ Build hierarchical structure                             │
│                                                                  │
│ 5. REPORT GENERATION (analyzer.py)                              │
│    ├─→ Assemble CoverageReport                                  │
│    ├─→ Validate thresholds                                      │
│    └─→ Generate mutation targets                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUTS                                                          │
├─────────────────────────────────────────────────────────────────┤
│ coverage_report.json (Step 7 input)                             │
│   ├─→ structural_coverage (mandatory metrics)                   │
│   ├─→ hierarchical (per-test breakdown)                         │
│   ├─→ mutation_data (Step 6 targets)                            │
│   └─→ validation results                                        │
│                                                                  │
│ coverage_summary.txt (human-readable)                           │
│   └─→ Formatted tables and statistics                           │
│                                                                  │
│ enriched_test_report.json (optional)                            │
│   └─→ test_report.json + coverage summary                       │
└─────────────────────────────────────────────────────────────────┘
Copy
---

## Component Architecture

### 1. Models (models.py)

**Purpose**: Define all data structures

**Key Classes**:
```python
# Core Coverage Data
├── LineCoverageData         # Single line
├── BranchData               # Single branch
├── ToggleData               # Signal toggles
├── FileCoverage             # File-level aggregation
└── ModuleCoverage           # Module-level aggregation

# Metrics
├── LineCoverageMetrics      # Aggregated line stats
├── BranchCoverageMetrics    # Aggregated branch stats
├── ToggleCoverageMetrics    # Aggregated toggle stats
├── FSMCoverageMetrics       # FSM coverage (Phase 2)
└── StructuralCoverageMetrics # Complete metrics (Step 7 input)

# Analysis
├── PerTestCoverage          # Individual test contribution
├── HierarchicalCoverage     # Merged + per-test + differential
├── MutationTarget           # Mutation testing target
└── MutationTestingData      # Step 6 export

# Output
└── CoverageReport           # Main output structure
Design: Immutable data classes with computed properties

2. Configuration (config.py)
Purpose: Manage configuration from multiple sources
Priority: CLI args > Environment vars > .tbeval.yaml > Defaults
Key Classes:
pythonCopy├── CoverageThresholds       # Line/branch/toggle/FSM thresholds
├── CoverageWeights          # Scoring weights
├── ParserConfig             # Parser settings
├── MergingConfig            # Merge strategy
├── ReportingConfig          # Output settings
└── CoverageAnalysisConfig   # Main config
Configuration Flow:
Copy.tbeval.yaml → CoverageAnalysisConfig.from_yaml()
                      ↓
         Apply CLI overrides (--line-threshold, etc.)
                      ↓
         Apply environment variables (TBEVAL_COV_*)
                      ↓
              Validate and finalize

3. Parsers (parsers/)
Purpose: Convert coverage files to ModuleCoverage
Architecture:
CopyBaseParser (abstract)
    ↓
    ├── VerilatorParser (priority #1)
    ├── LCOVParser (priority #2)
    └── CoveredParser (priority #3)

FormatDetector
    ├─→ Tries parsers in priority order
    └─→ Returns first match
Q12 Strategy (External Tool + Python Fallback):
pythonCopydef parse_file(self, file_path):
    # 1. Try external tool
    if self.config.use_external_tools and self.has_tool():
        result = self._parse_with_tool(file_path)
        if result.success:
            return result
    
    # 2. Fallback to Python
    if self.config.fallback_to_python:
        return self._parse_with_python(file_path)
    
    # 3. Fail
    return ParseResult(success=False, error="No parser available")
Parser Interface:
pythonCopyclass BaseParser:
    def can_parse(file_path) -> bool
    def parse_file(file_path) -> ParseResult
    def merge_coverage(files) -> MergeResult
    def get_format() -> CoverageFormat

4. Metrics (metrics/)
Calculator (metrics/calculator.py)
Purpose: Calculate coverage percentages and scores
Key Methods:
pythonCopyCoverageCalculator:
    ├── calculate_metrics(module_coverage) → StructuralCoverageMetrics
    ├── calculate_line_coverage() → LineCoverageMetrics
    ├── calculate_branch_coverage() → BranchCoverageMetrics
    ├── calculate_toggle_coverage() → ToggleCoverageMetrics
    ├── identify_hotspots() → List[UncoveredRegion]
    └── validate_metrics() → (passed, violations)
Weighted Score Formula:
Copyoverall_score = (
    line_pct * 0.35 +
    branch_pct * 0.35 +
    toggle_pct * 0.20 +
    fsm_pct * 0.10
) / 100.0  # Normalize to 0.0-1.0
Merger (metrics/merger.py)
Purpose: Merge per-test coverage with advanced tracking (Q13)
Merge Algorithm:
pythonCopydef merge_with_tracking(test_coverages, test_durations):
    # 1. Build line coverage map (which tests cover which lines)
    line_map = {}  # (file, line) → set of test names
    
    # 2. For each test, identify unique vs overlapping lines
    for test_name, coverage in test_coverages.items():
        unique_lines = lines covered ONLY by this test
        overlapping_lines = lines covered by multiple tests
        
        # Calculate metrics
        unique_pct = len(unique_lines) / total_lines
        efficiency = unique_pct / test_duration
        redundancy = len(overlapping) / (unique + overlapping)
    
    # 3. Calculate differential coverage (cumulative)
    # 4. Calculate optimal order (greedy algorithm)
    # 5. Identify essential/redundant tests
Greedy Optimal Order:
pythonCopycovered = set()
order = []
while remaining_tests:
    # Pick test that adds most new coverage
    best_test = max(remaining_tests, 
                    key=lambda t: len(test_lines[t] - covered))
    order.append(best_test)
    covered.update(test_lines[best_test])
    remaining_tests.remove(best_test)

5. Analyzer (analyzer.py)
Purpose: Main orchestrator - coordinates entire pipeline
Execution Flow:
pythonCopyclass CoverageAnalyzer:
    def analyze() -> AnalysisResult:
        # 1. Load inputs
        self._load_test_report()
        self._load_build_manifest()
        
        # 2. Find coverage files
        self._find_coverage_files()
        
        # 3. Parse coverage
        for file in self.coverage_files:
            format = self.detector.detect(file)
            coverage = format.parser.parse_file(file)
            self.parsed_coverages[test_name] = coverage
        
        # 4. Calculate and merge
        self.hierarchical = self.merger.merge_with_tracking(
            self.parsed_coverages,
            self.test_durations
        )
        
        # 5. Generate report
        report = CoverageReport(
            structural_coverage=self.hierarchical.merged,
            hierarchical=self.hierarchical,
            mutation_data=self._generate_mutation_data()
        )
        
        # 6. Validate thresholds
        passed, violations = self.calculator.validate_metrics(report)
        report.thresholds_met = passed
        
        return AnalysisResult(success=True, report=report)
Factory Methods:
pythonCopy# From config file
analyzer = CoverageAnalyzer.from_config_file(".tbeval.yaml")

# From test report
analyzer = CoverageAnalyzer.from_test_report("test_report.json")

# Direct instantiation
config = CoverageAnalysisConfig(...)
analyzer = CoverageAnalyzer(config)

6. CLI (main.py)
Purpose: Command-line interface
Command Structure:
Copypython -m step5_coverage [command] [options]

Commands:
    (default)       Run coverage analysis
    --list-parsers  Show available parsers
    --check-config  Validate configuration
    --dry-run       Validate inputs only

Options:
    Input:  --test-report, --build-manifest, --config
    Output: --output, --summary, --html
    Thresholds: --line-threshold, --branch-threshold
    Display: --verbose, --quiet, --debug, --no-color
Color Output:
pythonCopyColors.GREEN → Success messages
Colors.YELLOW → Warnings
Colors.RED → Errors
Colors.BLUE → Info
Colors.CYAN → Headers
