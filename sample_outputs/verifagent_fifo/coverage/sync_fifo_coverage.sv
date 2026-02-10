// Auto-added UVM imports
import uvm_pkg::*;
`include "uvm_macros.svh"

Here's the complete SystemVerilog functional coverage code for the sync_fifo design:

```systemverilog
// Functional Coverage for sync_fifo Design
// This coverage model captures all critical functional scenarios

class sync_fifo_coverage extends uvm_subscriber #(sync_fifo_transaction);
    `uvm_component_utils(sync_fifo_coverage)
    
    // Coverage transaction
    sync_fifo_transaction cov_txn;
    
    // Parameters for coverage (should match DUT parameters)
    parameter DATA_WIDTH = 32;
    parameter DEPTH = 16;
    parameter ADDR_WIDTH = $clog2(DEPTH);
    
    // Threshold values for coverage
    localparam ALMOST_FULL_THRESHOLD = (3 * DEPTH) / 4;
    localparam ALMOST_EMPTY_THRESHOLD = DEPTH / 4;
    
    // Coverage Groups
    
    // 1. Basic FIFO Operations Coverage
    covergroup cg_fifo_operations @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "fifo_operations";
        
        cp_wr_en: coverpoint cov_txn.wr_en {
            bins write_enabled = {1};
            bins write_disabled = {0};
        }
        
        cp_rd_en: coverpoint cov_txn.rd_en {
            bins read_enabled = {1};
            bins read_disabled = {0};
        }
        
        cp_full: coverpoint cov_txn.full {
            bins fifo_full = {1};
            bins fifo_not_full = {0};
        }
        
        cp_empty: coverpoint cov_txn.empty {
            bins fifo_empty = {1};
            bins fifo_not_empty = {0};
        }
        
        // Cross coverage for operation combinations
        cross_wr_en_full: cross cp_wr_en, cp_full {
            bins write_when_full = binsof(cp_wr_en.write_enabled) && binsof(cp_full.fifo_full);
            bins write_when_not_full = binsof(cp_wr_en.write_enabled) && binsof(cp_full.fifo_not_full);
            bins no_write_when_full = binsof(cp_wr_en.write_disabled) && binsof(cp_full.fifo_full);
            bins no_write_when_not_full = binsof(cp_wr_en.write_disabled) && binsof(cp_full.fifo_not_full);
        }
        
        cross_rd_en_empty: cross cp_rd_en, cp_empty {
            bins read_when_empty = binsof(cp_rd_en.read_enabled) && binsof(cp_empty.fifo_empty);
            bins read_when_not_empty = binsof(cp_rd_en.read_enabled) && binsof(cp_empty.fifo_not_empty);
            bins no_read_when_empty = binsof(cp_rd_en.read_disabled) && binsof(cp_empty.fifo_empty);
            bins no_read_when_not_empty = binsof(cp_rd_en.read_disabled) && binsof(cp_empty.fifo_not_empty);
        }
        
        cross_wr_rd_en: cross cp_wr_en, cp_rd_en {
            bins simultaneous_wr_rd = binsof(cp_wr_en.write_enabled) && binsof(cp_rd_en.read_enabled);
            bins only_write = binsof(cp_wr_en.write_enabled) && binsof(cp_rd_en.read_disabled);
            bins only_read = binsof(cp_wr_en.write_disabled) && binsof(cp_rd_en.read_enabled);
            bins no_operation = binsof(cp_wr_en.write_disabled) && binsof(cp_rd_en.read_disabled);
        }
    endgroup
    
    // 2. Status Flags Coverage
    covergroup cg_status_flags @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "status_flags";
        
        cp_full_flag: coverpoint cov_txn.full {
            bins full_set = {1};
            bins full_clear = {0};
        }
        
        cp_empty_flag: coverpoint cov_txn.empty {
            bins empty_set = {1};
            bins empty_clear = {0};
        }
        
        cp_almost_full: coverpoint cov_txn.almost_full {
            bins almost_full_set = {1};
            bins almost_full_clear = {0};
        }
        
        cp_almost_empty: coverpoint cov_txn.almost_empty {
            bins almost_empty_set = {1};
            bins almost_empty_clear = {0};
        }
        
        cp_error: coverpoint cov_txn.error {
            bins error_set = {1};
            bins error_clear = {0};
        }
        
        // Cross coverage for flag combinations
        cross_almost_flags: cross cp_almost_full, cp_almost_empty {
            bins both_almost_flags = binsof(cp_almost_full.almost_full_set) && binsof(cp_almost_empty.almost_empty_set);
            bins only_almost_full = binsof(cp_almost_full.almost_full_set) && binsof(cp_almost_empty.almost_empty_clear);
            bins only_almost_empty = binsof(cp_almost_full.almost_full_clear) && binsof(cp_almost_empty.almost_empty_set);
            bins neither_almost = binsof(cp_almost_full.almost_full_clear) && binsof(cp_almost_empty.almost_empty_clear);
        }
        
        cross_full_error: cross cp_full_flag, cp_error {
            bins full_with_error = binsof(cp_full_flag.full_set) && binsof(cp_error.error_set);
            bins full_no_error = binsof(cp_full_flag.full_set) && binsof(cp_error.error_clear);
            bins not_full_with_error = binsof(cp_full_flag.full_clear) && binsof(cp_error.error_set);
            bins not_full_no_error = binsof(cp_full_flag.full_clear) && binsof(cp_error.error_clear);
        }
        
        cross_empty_error: cross cp_empty_flag, cp_error {
            bins empty_with_error = binsof(cp_empty_flag.empty_set) && binsof(cp_error.error_set);
            bins empty_no_error = binsof(cp_empty_flag.empty_set) && binsof(cp_error.error_clear);
            bins not_empty_with_error = binsof(cp_empty_flag.empty_clear) && binsof(cp_error.error_set);
            bins not_empty_no_error = binsof(cp_empty_flag.empty_clear) && binsof(cp_error.error_clear);
        }
        
        // Illegal combinations
        cross_full_empty: cross cp_full_flag, cp_empty_flag {
            illegal_bins both_full_empty = binsof(cp_full_flag.full_set) && binsof(cp_empty_flag.empty_set);
        }
    endgroup
    
    // 3. Count Values Coverage
    covergroup cg_count_values @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "count_values";
        
        cp_count: coverpoint cov_txn.count {
            bins empty_count = {0};
            bins low_count = {[1:DEPTH/4]};
            bins mid_count = {[DEPTH/4+1:3*DEPTH/4-1]};
            bins high_count = {[3*DEPTH/4:DEPTH-1]};
            bins full_count = {DEPTH};
            bins boundary_almost_empty = {DEPTH/4};
            bins boundary_almost_full = {3*DEPTH/4};
        }
        
        cp_count_transitions: coverpoint cov_txn.count {
            bins count_inc[] = ([0:DEPTH-1] => [1:DEPTH]);
            bins count_dec[] = ([1:DEPTH] => [0:DEPTH-1]);
            bins count_stable[] = ([0:DEPTH] => [0:DEPTH]);
        }
        
        // Cross coverage with operations
        cross_count_operations: cross cp_count, cov_txn.wr_en, cov_txn.rd_en {
            bins write_at_empty = binsof(cp_count.empty_count) && binsof(cov_txn.wr_en) intersect {1} && binsof(cov_txn.rd_en) intersect {0};
            bins read_at_full = binsof(cp_count.full_count) && binsof(cov_txn.wr_en) intersect {0} && binsof(cov_txn.rd_en) intersect {1};
            bins simul_at_mid = binsof(cp_count.mid_count) && binsof(cov_txn.wr_en) intersect {1} && binsof(cov_txn.rd_en) intersect {1};
        }
    endgroup
    
    // 4. Threshold Boundaries Coverage
    covergroup cg_threshold_boundaries @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "threshold_boundaries";
        
        cp_almost_full_boundary: coverpoint cov_txn.count {
            bins below_threshold = {[0:ALMOST_FULL_THRESHOLD-1]};
            bins at_threshold = {ALMOST_FULL_THRESHOLD};
            bins above_threshold = {[ALMOST_FULL_THRESHOLD+1:DEPTH]};
        }
        
        cp_almost_empty_boundary: coverpoint cov_txn.count {
            bins below_threshold = {[0:ALMOST_EMPTY_THRESHOLD-1]};
            bins at_threshold = {ALMOST_EMPTY_THRESHOLD};
            bins above_threshold = {[ALMOST_EMPTY_THRESHOLD+1:DEPTH]};
        }
        
        // Cross with operations at boundaries
        cross_boundary_operations: cross cp_almost_full_boundary, cp_almost_empty_boundary, cov_txn.wr_en, cov_txn.rd_en;
    endgroup
    
    // 5. Error Conditions Coverage
    covergroup cg_error_conditions @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "error_conditions";
        
        cp_overflow_condition: coverpoint {cov_txn.full, cov_txn.wr_en, cov_txn.rd_en} {
            bins overflow_attempt = {3'b110}; // full=1, wr_en=1, rd_en=0
            bins overflow_with_read = {3'b111}; // full=1, wr_en=1, rd_en=1
            bins no_overflow = default;
        }
        
        cp_underflow_condition: coverpoint {cov_txn.empty, cov_txn.rd_en, cov_txn.wr_en} {
            bins underflow_attempt = {3'b110}; // empty=1, rd_en=1, wr_en=0
            bins underflow_with_write = {3'b111}; // empty=1, rd_en=1, wr_en=1
            bins no_underflow = default;
        }
        
        cp_error_recovery: coverpoint {cov_txn.error, cov_txn.rst_n} {
            bins error_active = {2'b11};
            bins error_reset = {2'b10, 2'b00};
            bins no_error = {2'b01};
        }
        
        // Cross error types with FIFO state
        cross_error_fifo_state: cross cp_overflow_condition, cp_underflow_condition, cov_txn.count {
            ignore_bins impossible = binsof(cp_overflow_condition.overflow_attempt) && binsof(cov_txn.count) intersect {[0:DEPTH-1]};
            ignore_bins impossible2 = binsof(cp_underflow_condition.underflow_attempt) && binsof(cov_txn.count) intersect {[1:DEPTH]};
        }
    endgroup
    
    // 6. Simultaneous Operations Coverage
    covergroup cg_simultaneous_ops @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "simultaneous_operations";
        
        cp_simul_rw_when_full: coverpoint {cov_txn.full, cov_txn.wr_en, cov_txn.rd_en} {
            bins simul_rw_full = {3'b111};
            bins write_only_full = {3'b110};
            bins read_only_full = {3'b101};
            bins no_op_full = {3'b100};
            bins not_full = {3'b0??};
        }
        
        cp_simul_rw_when_empty: coverpoint {cov_txn.empty, cov_txn.wr_en, cov_txn.rd_en} {
            bins simul_rw_empty = {3'b111};
            bins write_only_empty = {3'b110};
            bins read_only_empty = {3'b101};
            bins no_op_empty = {3'b100};
            bins not_empty = {3'b0??};
        }
        
        cp_simul_rw_normal: coverpoint {cov_txn.full, cov_txn.empty, cov_txn.wr_en, cov_txn.rd_en} {
            bins simul_normal = {4'b0011};
            bins write_normal = {4'b0010};
            bins read_normal = {4'b0001};
            bins no_op_normal = {4'b0000};
            bins invalid_state = {4'b11??}; // Both full and empty - should not happen
        }
        
        // Cross simultaneous operations with FIFO state
        cross_simul_ops_fifo_state: cross cp_simul_rw_normal, cov_txn.count;
    endgroup
    
    // 7. Data Patterns Coverage
    covergroup cg_data_patterns @(posedge cov_txn.clk iff cov_txn.wr_en);
        option.per_instance = 1;
        option.name = "data_patterns";
        
        cp_data_all_zeros: coverpoint cov_txn.wr_data {
            bins all_zeros = {0};
            bins not_all_zeros = {[1:$]};
        }
        
        cp_data_all_ones: coverpoint cov_txn.wr_data {
            bins all_ones = {{DATA_WIDTH{1'b1}}};
            bins not_all_ones = default;
        }
        
        cp_data_alternating: coverpoint cov_txn.wr_data {
            bins alternating_01 = {{DATA_WIDTH/2{2'b01}}};
            bins alternating_10 = {{DATA_WIDTH/2{2'b10}}};
            bins other_patterns = default;
        }
        
        cp_data_random: coverpoint cov_txn.wr_data {
            bins low_range = {[0:255]};
            bins mid_range = {[256:65535]} iff (DATA_WIDTH >= 16);
            bins high_range = {[65536:$]} iff (DATA_WIDTH >= 32);
        }
        
        // Cross data patterns with FIFO state
        cross_data_pattern_fifo_state: cross cp_data_all_zeros, cov_txn.full, cov_txn.almost_full;
    endgroup
    
    // 8. Reset Scenarios Coverage
    covergroup cg_reset_scenarios @(negedge cov_txn.rst_n or posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "reset_scenarios";
        
        cp_reset_during_write: coverpoint {cov_txn.rst_n, cov_txn.wr_en} {
            bins reset_during_write = {2'b01};
            bins reset_no_write = {2'b00};
            bins no_reset_write = {2'b11};
            bins no_reset_no_write = {2'b10};
        }
        
        cp_reset_during_read: coverpoint {cov_txn.rst_n, cov_txn.rd_en} {
            bins reset_during_read = {2'b01};
            bins reset_no_read = {2'b00};
            bins no_reset_read = {2'b11};
            bins no_reset_no_read = {2'b10};
        }
        
        cp_reset_when_full: coverpoint {cov_txn.rst_n, cov_txn.full} {
            bins reset_when_full = {2'b01};
            bins reset_when_not_full = {2'b00};
            bins no_reset_full = {2'b11};
            bins no_reset_not_full = {2'b10};
        }
        
        cp_reset_when_empty: coverpoint {cov_txn.rst_n, cov_txn.empty} {
            bins reset_when_empty = {2'b01};
            bins reset_when_not_empty = {2'b00};
            bins no_reset_empty = {2'b11};
            bins no_reset_not_empty = {2'b10};
        }
        
        // Cross reset timing with FIFO state
        cross_reset_timing_fifo_state: cross cp_reset_during_write, cp_reset_during_read, cov_txn.count;
    endgroup
    
    // 9. FSM States Coverage (Conceptual - based on FIFO state)
    covergroup cg_fsm_states @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "fsm_states";
        
        cp_current_state: coverpoint {cov_txn.full, cov_txn.empty, cov_txn.almost_full, cov_txn.almost_empty} {
            bins state_empty = {4'b0101};           // empty=1, almost_empty=1
            bins state_almost_empty = {4'b0001};    // almost_empty=1 only
            bins state_normal = {4'b0000};          // no flags
            bins state_almost_full = {4'b0010};     // almost_full=1 only
            bins state_full = {4'b1010};            // full=1, almost_full=1
            bins state_error = default;             // any other combination
        }
        
        cp_state_transitions: coverpoint {cov_txn.full, cov_txn.empty, cov_txn.almost_full, cov_txn.almost_empty} {
            bins empty_to_almost_empty[] = (4'b0101 => 4'b0001);
            bins almost_empty_to_normal[] = (4'b0001 => 4'b0000);
            bins normal_to_almost_full[] = (4'b0000 => 4'b0010);
            bins almost_full_to_full[] = (4'b0010 => 4'b1010);
            bins full_to_almost_full[] = (4'b1010 => 4'b0010);
            bins almost_full_to_normal[] = (4'b0010 => 4'b0000);
            bins normal_to_almost_empty[] = (4'b0000 => 4'b0001);
            bins almost_empty_to_empty[] = (4'b0001 => 4'b0101);
        }
        
        // Cross state with operations
        cross_state_operation: cross cp_current_state, cov_txn.wr_en, cov_txn.rd_en;
        
        // Cross state transitions with count
        cross_state_transition_count: cross cp_state_transitions, cov_txn.count;
    endgroup
    
    // 10. Pointer Coverage (Internal signals - would need access to DUT internals)
    covergroup cg_pointer_coverage @(posedge cov_txn.clk);
        option.per_instance = 1;
        option.name = "pointer_coverage";
        
        // Note: These would require access to internal DUT signals
        // Shown here for completeness of coverage model
        
        cp_wr_ptr: coverpoint cov_txn.wr_ptr {
            bins ptr_values[] = {[0:DEPTH-1]};
            bins ptr_wraparound[] = ([DEPTH-1] => [0]);
        }
        
        cp_rd_ptr: coverpoint cov_txn.rd_ptr {
            bins ptr_values[] = {[0:DEPTH-1]};
            bins ptr_wraparound[] = ([DEPTH-1] => [0]);
        }
        
        // Cross pointers for relative positioning
        cross_ptr_relationship: cross cp_wr_ptr, cp_rd_ptr {
            bins ptrs_equal = binsof(cp_wr_ptr) intersect binsof(cp_rd_ptr);
            bins wr_ahead = binsof(cp_wr_ptr) intersect {[1:DEPTH-1]} && binsof(cp_rd_ptr) intersect {[0:DEPTH-2]};
            bins rd_ahead = binsof(cp_rd_ptr) intersect {[1:DEPTH-1]} && binsof(cp_wr_ptr) intersect {[0:DEPTH-2]};
        }
    endgroup
    
    // Constructor
    function new(string name = "sync_fifo_coverage", uvm_component parent = null);
        super.new(name, parent);
        
        // Instantiate coverage groups
        cg_fifo_operations = new();
        cg_status_flags = new();
        cg_count_values = new();
        cg_threshold_boundaries = new();
        cg_error_conditions = new();
        cg_simultaneous_ops = new();
        cg_data_patterns = new();
        cg_reset_scenarios = new();
        cg_fsm_states = new();
        cg_pointer_coverage = new();
    endfunction
    
    // Write method - called when transaction is received
    function void write(sync_fifo_transaction t);
        cov_txn = t;
        
        // Sample all coverage groups
        cg_fifo_operations.sample();
        cg_status_flags.sample();
        cg_count_values.sample();
        cg_threshold_boundaries.sample();
        cg_error_conditions.sample();
        cg_simultaneous_ops.sample();
        cg_data_patterns.sample();
        cg_reset_scenarios.sample();
        cg_fsm_states.sample();
        cg_pointer_coverage.sample();
    endfunction
    
    // Coverage reporting
    function void report_phase(uvm_phase phase);
        real coverage_percent;
        
        `uvm_info(get_type_name(), "=== FIFO Coverage Report ===", UVM_LOW)
        
        coverage_percent = cg_fifo_operations.get_coverage();
        `uvm_info(get_type_name(), $sformatf("FIFO Operations Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_status_flags.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Status Flags Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_count_values.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Count Values Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_threshold_boundaries.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Threshold Boundaries Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_error_conditions.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Error Conditions Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_simultaneous_ops.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Simultaneous Operations Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_data_patterns.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Data Patterns Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_reset_scenarios.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Reset Scenarios Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_fsm_states.get_coverage();
        `uvm_info(get_type_name(), $sformatf("FSM States Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        coverage_percent = cg_pointer_coverage.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Pointer Coverage: %.2f%%", coverage_percent), UVM_LOW)
        
        `uvm_info(get_type_name(), "=== End Coverage Report ===", UVM_LOW)
    endfunction
    
endclass

// Transaction class for coverage (would be defined elsewhere in testbench)
class sync_fifo_transaction extends uvm_sequence_item;
    `uvm_object_utils(sync_fifo_transaction)
    
    // Input signals
    bit clk;
    bit rst_n;
    bit wr_en;
    bit [DATA_WIDTH-1:0] wr_data;
    bit rd_en;
    
    // Output signals
    bit [DATA_WIDTH-1:0] rd_data;
    bit full;
    bit empty;
    bit almost_full;
    bit almost_empty;
    bit error;
    
    // Internal signals (for enhanced coverage)
    bit [ADDR_WIDTH:0] count;
    bit [ADDR_WIDTH-1:0] wr_ptr;
    bit [ADDR_WIDTH-1:0] rd_ptr;
    
    function new(string name = "sync_fifo_transaction");
        super.new(name);
    endfunction
    
endclass

// Coverage wrapper for integration with testbench
module sync_fifo_coverage_wrapper;
    
    // Bind to DUT for signal access
    bind sync_fifo sync_fifo_coverage_monitor cov_monitor (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .wr_data(wr_data),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .full(full),
        .empty(empty),
        .almost_full(almost_full),
        .almost_empty(almost_empty),
        .error(error),
        .count(count_reg),
        .wr_ptr(wr_ptr),
        .rd_ptr(rd_ptr)
    );
    
endmodule

// Coverage monitor module for signal collection
module sync_fifo_coverage_monitor #(
    parameter DATA_WIDTH = 32,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH)
)(
    input clk,
    input rst_n,
    input wr_en,
    input [DATA_WIDTH-1:0] wr_data,
    input rd_en,
    input [DATA_WIDTH-1:0] rd_data,
    input full,
    input empty,
    input almost_full,
    input almost_empty,
    input error,
    input [ADDR_WIDTH:0] count,
    input [ADDR_WIDTH-1:0] wr_ptr,
    input [ADDR_WIDTH-1:0] rd_ptr
);
    
    // Coverage instance
    sync_fifo_coverage cov_inst;
    sync_fifo_transaction cov_txn;
    
    initial begin
        cov_inst = new("sync_fifo_coverage");
        cov_txn = new("sync_fifo_transaction");
    end
    
    // Continuous assignment to transaction
    always @(posedge clk or negedge rst_n) begin
        cov_txn.clk = clk;
        cov_txn.rst_n = rst_n;
        cov_txn.wr_en = wr_en;
        cov_txn.wr_data = wr_data;
        cov_txn.rd_en = rd_en;
        cov_txn.rd_data = rd_data;
        cov_txn.full = full;
        cov_txn.empty = empty;
        cov_txn.almost_full = almost_full;
        cov_txn.almost_empty = almost_empty;
        cov_txn.error = error;
        cov_txn.count = count;
        cov_txn.wr_ptr = wr_ptr;
        cov_txn.rd_ptr = rd_ptr;
        
        // Sample coverage
        cov_inst.write(cov_txn);
    end
    
endmodule
```

This comprehensive coverage model includes:

1. **Basic Operations Coverage**: Write/read enables with FIFO state
2. **Status Flags Coverage**: All flag combinations and transitions
3. **Count Values Coverage**: Full range of count values and transitions
4. **Threshold Boundaries**: Coverage around almost_full/almost_empty thresholds
5. **Error Conditions**: Overflow/underflow scenarios
6. **Simultaneous Operations**: Concurrent read/write coverage
7. **Data Patterns**: Various data patterns written to FIFO
8. **Reset Scenarios**: Reset timing with different FIFO states
9. **FSM States**: State machine coverage based on flag combinations
10. **Pointer Coverage**: Internal pointer behavior and wraparound

The coverage model provides comprehensive functional coverage to ensure all critical scenarios are tested and verified.