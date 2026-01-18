# Cocotb Makefile for FIFO verification

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# DUT
VERILOG_SOURCES = $(PWD)/fifo.v
TOPLEVEL = fifo
MODULE = test_fifo

# Verilator args
EXTRA_ARGS += --coverage --coverage-line --coverage-toggle
EXTRA_ARGS += -Wno-fatal
EXTRA_ARGS += --trace

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim

