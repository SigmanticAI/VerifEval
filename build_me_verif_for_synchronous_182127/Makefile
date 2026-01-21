# Makefile for synchronous_fifo verification environment

# Tool settings
SIMULATOR = vcs
SIMV = simv
COVERAGE_DIR = coverage_report
LOG_DIR = logs
WORK_DIR = work

# Compiler flags
VCS_FLAGS = -full64 \
            -sverilog \
            -timescale=1ns/1ps \
            -debug_access+all \
            -kdb \
            -lca \
            -ntb_opts uvm-1.2 \
            +vcs+lic+wait \
            -l $(LOG_DIR)/compile.log

# Coverage flags
COV_FLAGS = -cm line+cond+fsm+tgl+branch+assert \
            -cm_dir $(COVERAGE_DIR)/$(TEST).vdb \
            -cm_name $(TEST)

# Simulation flags
SIM_FLAGS = -l $(LOG_DIR)/$(TEST).log \
            +UVM_TESTNAME=$(TEST) \
            +UVM_VERBOSITY=$(VERBOSITY) \
            $(COV_FLAGS)

# Default values
TEST ?= sync_fifo_base_test
VERBOSITY ?= UVM_MEDIUM
SEED ?= random

# File lists
RTL_FILES = rtl/synchronous_fifo.sv

TB_FILES = tb/agents/sync_fifo_if.sv \
           tb/agents/sync_fifo_agent.sv \
           tb/env/env.sv \
           tb/tests/tests.sv \
           assertions/synchronous_fifo_assertions.sv \
           coverage/synchronous_fifo_coverage.sv \
           ral/synchronous_fifo_ral.sv \
           tb/tb_top.sv

ALL_FILES = $(RTL_FILES) $(TB_FILES)

# Test list for regression
TESTS = sync_fifo_base_test \
        sync_fifo_full_test \
        sync_fifo_empty_test \
        sync_fifo_overflow_test \
        sync_fifo_underflow_test \
        sync_fifo_reset_test \
        sync_fifo_random_test \
        sync_fifo_back2back_test \
        sync_fifo_stress_test

# Targets
.PHONY: all clean compile run regression coverage help setup

all: setup compile

help:
	@echo "Makefile targets for synchronous_fifo verification"
	@echo "=================================================="
	@echo "setup      - Create necessary directories"
	@echo "compile    - Compile the design and testbench"
	@echo "run        - Run a single test (TEST=test_name)"
	@echo "regression - Run all tests"
	@echo "coverage   - Generate coverage report"
	@echo "clean      - Clean all generated files"
	@echo ""
	@echo "Variables:"
	@echo "  TEST=        (default: sync_fifo_base_test)"
	@echo "  VERBOSITY=       (default: UVM_MEDIUM)"
	@echo "  SEED=            (default: random)"
	@echo ""
	@echo "Example usage:"
	@echo "  make compile"
	@echo "  make run TEST=sync_fifo_random_test SEED=12345"
	@echo "  make regression"
	@echo "  make coverage"

setup:
	@echo "Creating directories..."
	@mkdir -p $(LOG_DIR)
	@mkdir -p $(COVERAGE_DIR)
	@mkdir -p $(WORK_DIR)

compile: setup
	@echo "Compiling design and testbench..."
	$(SIMULATOR) $(VCS_FLAGS) \
		$(ALL_FILES) \
		-o $(SIMV) \
		-top tb_top
	@echo "Compilation complete!"

run: compile
	@echo "Running test: $(TEST) with seed: $(SEED)"
	./$(SIMV) $(SIM_FLAGS) \
		+ntb_random_seed=$(SEED)
	@echo "Test $(TEST) completed!"

regression: compile
	@echo "Starting regression run..."
	@for test in $(TESTS); do \
		echo "Running $$test..."; \
		./$(SIMV) -l $(LOG_DIR)/$$test.log \
			+UVM_TESTNAME=$$test \
			+UVM_VERBOSITY=$(VERBOSITY) \
			-cm line+cond+fsm+tgl+branch+assert \
			-cm_dir $(COVERAGE_DIR)/$$test.vdb \
			-cm_name $$test \
			+ntb_random_seed=random || exit 1; \
	done
	@echo "Regression complete!"
	@$(MAKE) coverage

coverage:
	@echo "Generating coverage report..."
	urg -full64 \
		-dir $(COVERAGE_DIR)/*.vdb \
		-format both \
		-report $(COVERAGE_DIR)/urgReport
	@echo "Coverage report generated in $(COVERAGE_DIR)/urgReport"
	@echo ""
	@echo "Coverage Summary:"
	@grep -A 10 "COVERAGE SUMMARY" $(COVERAGE_DIR)/urgReport/hierarchy.txt || true

merge_coverage:
	@echo "Merging coverage databases..."
	urg -full64 \
		-dir $(COVERAGE_DIR)/*.vdb \
		-dbname $(COVERAGE_DIR)/merged_coverage \
		-format both \
		-report $(COVERAGE_DIR)/merged_report

clean:
	@echo "Cleaning generated files..."
	rm -rf $(SIMV) $(SIMV).daidir
	rm -rf csrc
	rm -rf $(LOG_DIR)
	rm -rf $(COVERAGE_DIR)
	rm -rf $(WORK_DIR)
	rm -rf ucli.key
	rm -rf vc_hdrs.h
	rm -rf DVEfiles
	rm -rf inter.vpd
	rm -rf *.log
	rm -rf .vlogansetup.*
	rm -rf urgReport
	rm -rf *.vdb
	@echo "Clean complete!"

run_gui: compile
	@echo "Running test with GUI: $(TEST)"
	./$(SIMV) -gui $(SIM_FLAGS) \
		+ntb_random_seed=$(SEED)

debug: VCS_FLAGS += -debug_all +memcbk
debug: compile
	@echo "Running test in debug mode: $(TEST)"
	./$(SIMV) $(SIM_FLAGS) \
		+ntb_random_seed=$(SEED) \
		-ucli -i debug.tcl

waves: compile
	@echo "Running test with waveform dump: $(TEST)"
	./$(SIMV) $(SIM_FLAGS) \
		+ntb_random_seed=$(SEED) \
		+vpdfile+waves.vpd

check_logs:
	@echo "Checking logs for errors..."
	@grep -i "error" $(LOG_DIR)/*.log || echo "No errors found"
	@grep -i "fatal" $(LOG_DIR)/*.log || echo "No fatal errors found"
	@grep -i "UVM_ERROR" $(LOG_DIR)/*.log || echo "No UVM errors found"
	@grep -i "UVM_FATAL" $(LOG_DIR)/*.log || echo "No UVM fatal errors found"

status:
	@echo "Verification Status"
	@echo "==================="
	@echo "Tests run:"
	@ls -1 $(LOG_DIR)/*.log 2>/dev/null | wc -l || echo "0"
	@echo "Coverage databases:"
	@ls -1d $(COVERAGE_DIR)/*.vdb 2>/dev/null | wc -l || echo "0"
	@echo ""
	@$(MAKE) check_logs