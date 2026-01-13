Here's a complete Makefile for the sync_fifo verification environment:

```makefile
# Makefile for sync_fifo verification environment
# ==============================================

# Tool and simulator settings
SIMULATOR = vcs
WAVES = vpd
COVERAGE = cm

# Directory structure
TB_DIR = tb
AGENTS_DIR = $(TB_DIR)/agents
ENV_DIR = $(TB_DIR)/env
TESTS_DIR = $(TB_DIR)/tests
ASSERT_DIR = assertions
COV_DIR = coverage
WORK_DIR = work
LOG_DIR = logs
REPORT_DIR = reports

# Design and testbench files
DUT_FILES = rtl/sync_fifo.sv
TB_FILES = $(AGENTS_DIR)/sync_fifo_if.sv \
           $(AGENTS_DIR)/sync_fifo_agent.sv \
           $(ENV_DIR)/env.sv \
           $(TESTS_DIR)/tests.sv \
           $(ASSERT_DIR)/sync_fifo_assertions.sv \
           $(COV_DIR)/sync_fifo_coverage.sv \
           $(TB_DIR)/tb_top.sv

ALL_FILES = $(DUT_FILES) $(TB_FILES)

# Compilation flags
VCS_COMP_FLAGS = -sverilog \
                 -timescale=1ns/1ps \
                 -debug_access+all \
                 -kdb \
                 -lca \
                 -ntb_opts uvm-1.2 \
                 +incdir+$(AGENTS_DIR) \
                 +incdir+$(ENV_DIR) \
                 +incdir+$(TESTS_DIR) \
                 +incdir+$(ASSERT_DIR) \
                 +incdir+$(COV_DIR) \
                 -work $(WORK_DIR)

# Coverage flags
COV_FLAGS = -cm line+cond+fsm+tgl+branch+assert \
            -cm_dir $(WORK_DIR)/coverage.vdb \
            -cm_name sync_fifo_cov

# Simulation flags
SIM_FLAGS = -ucli \
            -do run.tcl \
            +UVM_TESTNAME \
            +UVM_VERBOSITY=UVM_MEDIUM

# Test list
TESTS = sync_fifo_basic_test \
        sync_fifo_full_test \
        sync_fifo_empty_test \
        sync_fifo_overflow_test \
        sync_fifo_underflow_test \
        sync_fifo_random_test \
        sync_fifo_stress_test

# Default target
.PHONY: all
all: compile

# Create directories
$(WORK_DIR) $(LOG_DIR) $(REPORT_DIR):
	@mkdir -p $@

# Compilation target
.PHONY: compile
compile: $(WORK_DIR)
	@echo "=== Compiling sync_fifo design and testbench ==="
	$(SIMULATOR) $(VCS_COMP_FLAGS) $(COV_FLAGS) $(ALL_FILES) -o $(WORK_DIR)/simv
	@echo "=== Compilation completed ==="

# Clean compilation
.PHONY: clean_compile
clean_compile:
	@echo "=== Cleaning and recompiling ==="
	$(MAKE) clean
	$(MAKE) compile

# Run single test
.PHONY: run_test
run_test: compile $(LOG_DIR)
	@if [ -z "$(TEST)" ]; then \
		echo "Error: TEST variable not specified. Usage: make run_test TEST=<test_name>"; \
		exit 1; \
	fi
	@echo "=== Running test: $(TEST) ==="
	cd $(WORK_DIR) && ./simv $(SIM_FLAGS)=$(TEST) \
		-l $(LOG_DIR)/$(TEST).log \
		+UVM_CONFIG_DB_TRACE

# Run all tests individually
.PHONY: run_tests
run_tests: compile $(LOG_DIR)
	@echo "=== Running all tests individually ==="
	@for test in $(TESTS); do \
		echo "Running $$test..."; \
		cd $(WORK_DIR) && ./simv $(SIM_FLAGS)=$$test \
			-l $(LOG_DIR)/$$test.log \
			+UVM_CONFIG_DB_TRACE || echo "$$test FAILED"; \
	done
	@echo "=== All individual tests completed ==="

# Coverage collection
.PHONY: coverage
coverage: compile $(LOG_DIR) $(REPORT_DIR)
	@echo "=== Running tests with coverage collection ==="
	@for test in $(TESTS); do \
		echo "Running $$test with coverage..."; \
		cd $(WORK_DIR) && ./simv $(SIM_FLAGS)=$$test \
			$(COV_FLAGS) \
			-l $(LOG_DIR)/$$test_cov.log \
			+UVM_CONFIG_DB_TRACE; \
	done
	@echo "=== Generating coverage reports ==="
	urg -dir $(WORK_DIR)/coverage.vdb \
		-report $(REPORT_DIR) \
		-format both

# Merge coverage from multiple runs
.PHONY: merge_coverage
merge_coverage: $(REPORT_DIR)
	@echo "=== Merging coverage databases ==="
	urg -dir $(WORK_DIR)/coverage.vdb \
		-report $(REPORT_DIR)/merged \
		-format both

# Regression testing
.PHONY: regression
regression: compile $(LOG_DIR) $(REPORT_DIR)
	@echo "=== Starting regression run ==="
	@echo "Tests to run: $(TESTS)"
	@passed=0; failed=0; \
	for test in $(TESTS); do \
		echo "=== Running regression test: $$test ==="; \
		cd $(WORK_DIR) && ./simv $(SIM_FLAGS)=$$test \
			$(COV_FLAGS) \
			-l $(LOG_DIR)/$$test_regr.log \
			+UVM_CONFIG_DB_TRACE; \
		if [ $$? -eq 0 ]; then \
			echo "$$test: PASSED"; \
			passed=$$((passed + 1)); \
		else \
			echo "$$test: FAILED"; \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	echo "=== Regression Summary ==="; \
	echo "Total tests: $$((passed + failed))"; \
	echo "Passed: $$passed"; \
	echo "Failed: $$failed"; \
	if [ $$failed -eq 0 ]; then \
		echo "=== REGRESSION PASSED ==="; \
	else \
		echo "=== REGRESSION FAILED ==="; \
		exit 1; \
	fi
	@echo "=== Generating regression coverage report ==="
	urg -dir $(WORK_DIR)/coverage.vdb \
		-report $(REPORT_DIR)/regression \
		-format both

# Nightly regression (extended test suite)
.PHONY: nightly
nightly: regression
	@echo "=== Running extended nightly tests ==="
	@$(MAKE) run_test TEST=sync_fifo_long_random_test
	@$(MAKE) run_test TEST=sync_fifo_corner_case_test
	@echo "=== Nightly regression completed ==="

# Debug mode compilation
.PHONY: debug
debug: $(WORK_DIR)
	@echo "=== Compiling in debug mode ==="
	$(SIMULATOR) $(VCS_COMP_FLAGS) $(COV_FLAGS) \
		-debug_access+all \
		-debug_region+cell+encrypt \
		$(ALL_FILES) -o $(WORK_DIR)/simv_debug

# Interactive debug session
.PHONY: debug_run
debug_run: debug $(LOG_DIR)
	@if [ -z "$(TEST)" ]; then \
		echo "Error: TEST variable not specified. Usage: make debug_run TEST=<test_name>"; \
		exit 1; \
	fi
	@echo "=== Running test in debug mode: $(TEST) ==="
	cd $(WORK_DIR) && ./simv_debug $(SIM_FLAGS)=$(TEST) \
		-gui \
		-l $(LOG_DIR)/$(TEST)_debug.log

# Lint checking
.PHONY: lint
lint:
	@echo "=== Running lint checks ==="
	vcs -sverilog -lint=all $(ALL_FILES)

# Generate test list
.PHONY: list_tests
list_tests:
	@echo "Available tests:"
	@for test in $(TESTS); do echo "  $$test"; done

# Check logs for errors
.PHONY: check_logs
check_logs:
	@echo "=== Checking logs for errors ==="
	@if [ -d $(LOG_DIR) ]; then \
		grep -l "UVM_ERROR\|UVM_FATAL\|Error\|Fatal" $(LOG_DIR)/*.log 2>/dev/null || echo "No errors found in logs"; \
	else \
		echo "No log directory found"; \
	fi

# Generate summary report
.PHONY: summary
summary: $(REPORT_DIR)
	@echo "=== Generating test summary ==="
	@echo "Test Summary Report" > $(REPORT_DIR)/summary.txt
	@echo "===================" >> $(REPORT_DIR)/summary.txt
	@echo "Generated on: $$(date)" >> $(REPORT_DIR)/summary.txt
	@echo "" >> $(REPORT_DIR)/summary.txt
	@if [ -d $(LOG_DIR) ]; then \
		echo "Test Results:" >> $(REPORT_DIR)/summary.txt; \
		for log in $(LOG_DIR)/*.log; do \
			if [ -f "$$log" ]; then \
				test_name=$$(basename $$log .log); \
				if grep -q "UVM_ERROR\|UVM_FATAL" "$$log"; then \
					echo "  $$test_name: FAILED" >> $(REPORT_DIR)/summary.txt; \
				else \
					echo "  $$test_name: PASSED" >> $(REPORT_DIR)/summary.txt; \
				fi; \
			fi; \
		done; \
	fi
	@cat $(REPORT_DIR)/summary.txt

# Clean targets
.PHONY: clean_logs
clean_logs:
	@echo "=== Cleaning log files ==="
	rm -rf $(LOG_DIR)

.PHONY: clean_reports
clean_reports:
	@echo "=== Cleaning report files ==="
	rm -rf $(REPORT_DIR)

.PHONY: clean_work
clean_work:
	@echo "=== Cleaning work directory ==="
	rm -rf $(WORK_DIR)

.PHONY: clean
clean: clean_logs clean_reports clean_work
	@echo "=== Cleaning all generated files ==="
	rm -rf simv* csrc *.log *.vpd *.fsdb ucli.key vc_hdrs.h
	rm -rf DVEfiles inter.vpd .vlogansetup.env .vcs.timestamp

# Help target
.PHONY: help
help:
	@echo "Sync FIFO Verification Makefile"
	@echo "================================"
	@echo ""
	@echo "Compilation targets:"
	@echo "  compile        - Compile design and testbench"
	@echo "  clean_compile  - Clean and recompile"
	@echo "  debug          - Compile in debug mode"
	@echo "  lint           - Run lint checks"
	@echo ""
	@echo "Simulation targets:"
	@echo "  run_test TEST=<name>  - Run specific test"
	@echo "  run_tests             - Run all tests individually"
	@echo "  debug_run TEST=<name> - Run test in debug mode"
	@echo ""
	@echo "Coverage targets:"
	@echo "  coverage       - Run tests with coverage collection"
	@echo "  merge_coverage - Merge coverage databases"
	@echo ""
	@echo "Regression targets:"
	@echo "  regression     - Run full regression suite"
	@echo "  nightly        - Run extended nightly regression"
	@echo ""
	@echo "Utility targets:"
	@echo "  list_tests     - Show available tests"
	@echo "  check_logs     - Check logs for errors"
	@echo "  summary        - Generate test summary report"
	@echo ""
	@echo "Clean targets:"
	@echo "  clean          - Clean all generated files"
	@echo "  clean_logs     - Clean log files only"
	@echo "  clean_reports  - Clean report files only"
	@echo "  clean_work     - Clean work directory only"
	@echo ""
	@echo "Available tests: $(TESTS)"

# Make sure intermediate files are not deleted
.PRECIOUS: $(WORK_DIR)/simv $(LOG_DIR)/%.log
```

This Makefile provides:

1. **Compilation targets**: Basic compilation, debug mode, and lint checking
2. **Test execution**: Single test runs, all tests, and debug mode
3. **Coverage collection**: Comprehensive coverage with report generation
4. **Regression testing**: Full regression with pass/fail tracking
5. **Utility functions**: Log checking, test listing, and summary generation
6. **Clean targets**: Various levels of cleanup
7. **Help system**: Comprehensive help documentation

Key features:
- Modular directory structure support
- Coverage database management
- Error checking and reporting
- Debug mode support
- Extensible test list
- Comprehensive logging
- Summary report generation

To use this Makefile:
```bash
# Compile the design
make compile

# Run a specific test
make run_test TEST=sync_fifo_basic_test

# Run full regression
make regression

# Generate coverage report
make coverage

# Get help
make help
```