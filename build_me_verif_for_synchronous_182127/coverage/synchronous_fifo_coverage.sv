// Synchronous FIFO Functional Coverage
// Comprehensive coverage for all aspects of FIFO operation

class synchronous_fifo_coverage;
  
  // Parameters - should match DUT
  parameter DATA_WIDTH = 8;
  parameter DEPTH = 16;
  parameter ADDR_WIDTH = $clog2(DEPTH);
  parameter COUNT_WIDTH = $clog2(DEPTH+1);
  
  // Sampled signals
  logic clk;
  logic rst_n;
  logic wr_en;
  logic rd_en;
  logic [DATA_WIDTH-1:0] wr_data;
  logic [DATA_WIDTH-1:0] rd_data;
  logic full;
  logic empty;
  logic almost_full;
  logic almost_empty;
  logic [COUNT_WIDTH-1:0] count;
  logic [ADDR_WIDTH-1:0] wr_ptr;
  logic [ADDR_WIDTH-1:0] rd_ptr;
  
  // Derived signals for coverage
  typedef enum {WRITE_ONLY, READ_ONLY, SIMUL_RW, NO_OP} operation_t;
  typedef enum {EMPTY, ALMOST_EMPTY, NORMAL, ALMOST_FULL, FULL} fifo_state_t;
  typedef enum {INCREMENT, DECREMENT, NO_CHANGE} count_delta_t;
  typedef enum {PTR_EQUAL, WR_AHEAD, RD_AHEAD} ptr_relation_t;
  
  operation_t current_operation;
  fifo_state_t current_state;
  fifo_state_t previous_state;
  count_delta_t count_change;
  ptr_relation_t ptr_relationship;
  
  logic wr_valid;
  logic rd_valid;
  logic [COUNT_WIDTH-1:0] prev_count;
  logic prev_full;
  logic prev_empty;
  logic prev_almost_full;
  logic prev_almost_empty;
  
  // Data pattern detection
  typedef enum {ALL_ZEROS, ALL_ONES, ALTERNATING_01, ALTERNATING_10, WALKING_ONES, WALKING_ZEROS, RANDOM} data_pattern_t;
  data_pattern_t wr_data_pattern;
  
  // Corner case detection
  logic write_when_full;
  logic read_when_empty;
  logic simul_rw_full;
  logic simul_rw_empty;
  logic wr_ptr_wrap;
  logic rd_ptr_wrap;
  logic back_to_back_wr;
  logic back_to_back_rd;
  
  // Boundary transitions
  logic count_0_to_1;
  logic count_1_to_0;
  logic count_1_to_2;
  logic count_2_to_1;
  logic count_depth_minus_2_to_depth_minus_1;
  logic count_depth_minus_1_to_depth_minus_2;
  logic count_depth_minus_1_to_depth;
  logic count_depth_to_depth_minus_1;
  
  // Flag transitions
  logic full_assert;
  logic full_deassert;
  logic empty_assert;
  logic empty_deassert;
  logic afull_assert;
  logic afull_deassert;
  logic aempty_assert;
  logic aempty_deassert;
  
  // Update derived signals
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      prev_count  prev_count)
      count_change = INCREMENT;
    else if (count  rd_ptr)
      ptr_relationship = WR_AHEAD;
    else
      ptr_relationship = RD_AHEAD;
  end
  
  // Valid operation signals
  always_comb begin
    wr_valid = (wr_en && !full) || (wr_en && rd_en && full);
    rd_valid = (rd_en && !empty) || (wr_en && rd_en && empty);
  end
  
  // Data pattern detection
  always_comb begin
    if (wr_data == '0)
      wr_data_pattern = ALL_ZEROS;
    else if (wr_data == '1)
      wr_data_pattern = ALL_ONES;
    else if (wr_data == {{DATA_WIDTH/2{2'b01}}})
      wr_data_pattern = ALTERNATING_01;
    else if (wr_data == {{DATA_WIDTH/2{2'b10}}})
      wr_data_pattern = ALTERNATING_10;
    else if ($countones(wr_data) == 1)
      wr_data_pattern = WALKING_ONES;
    else if ($countones(wr_data) == DATA_WIDTH-1)
      wr_data_pattern = WALKING_ZEROS;
    else
      wr_data_pattern = RANDOM;
  end
  
  // Corner case detection
  always_comb begin
    write_when_full = wr_en && full && !rd_en;
    read_when_empty = rd_en && empty && !wr_en;
    simul_rw_full = wr_en && rd_en && full;
    simul_rw_empty = wr_en && rd_en && empty;
    wr_ptr_wrap = wr_valid && (wr_ptr == DEPTH-1);
    rd_ptr_wrap = rd_valid && (rd_ptr == DEPTH-1);
    back_to_back_wr = wr_valid && prev_count  count;
  end
  
  // Boundary transitions
  always_comb begin
    count_0_to_1 = (prev_count == 0) && (count == 1);
    count_1_to_0 = (prev_count == 1) && (count == 0);
    count_1_to_2 = (prev_count == 1) && (count == 2);
    count_2_to_1 = (prev_count == 2) && (count == 1);
    count_depth_minus_2_to_depth_minus_1 = (prev_count == DEPTH-2) && (count == DEPTH-1);
    count_depth_minus_1_to_depth_minus_2 = (prev_count == DEPTH-1) && (count == DEPTH-2);
    count_depth_minus_1_to_depth = (prev_count == DEPTH-1) && (count == DEPTH);
    count_depth_to_depth_minus_1 = (prev_count == DEPTH) && (count == DEPTH-1);
  end
  
  // Flag transitions
  always_comb begin
    full_assert = !prev_full && full;
    full_deassert = prev_full && !full;
    empty_assert = !prev_empty && empty;
    empty_deassert = prev_empty && !empty;
    afull_assert = !prev_almost_full && almost_full;
    afull_deassert = prev_almost_full && !almost_full;
    aempty_assert = !prev_almost_empty && almost_empty;
    aempty_deassert = prev_almost_empty && !almost_empty;
  end
  
  // ========================================================================
  // COVERGROUP 1: Count Values Coverage
  // ========================================================================
  covergroup cg_count_values @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_count_values";
    
    cp_count: coverpoint count {
      bins count_values[] = {[0:DEPTH]};
      bins count_zero = {0};
      bins count_one = {1};
      bins count_depth_minus_one = {DEPTH-1};
      bins count_depth = {DEPTH};
      bins count_mid_range = {[2:DEPTH-2]};
    }
    
    cp_count_width: coverpoint count {
      bins lower_quarter = {[0:DEPTH/4]};
      bins lower_mid = {[DEPTH/4+1:DEPTH/2]};
      bins upper_mid = {[DEPTH/2+1:3*DEPTH/4]};
      bins upper_quarter = {[3*DEPTH/4+1:DEPTH]};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 2: Flag States Coverage
  // ========================================================================
  covergroup cg_flag_states @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_flag_states";
    
    cp_full: coverpoint full {
      bins full_low = {0};
      bins full_high = {1};
    }
    
    cp_empty: coverpoint empty {
      bins empty_low = {0};
      bins empty_high = {1};
    }
    
    cp_almost_full: coverpoint almost_full {
      bins afull_low = {0};
      bins afull_high = {1};
    }
    
    cp_almost_empty: coverpoint almost_empty {
      bins aempty_low = {0};
      bins aempty_high = {1};
    }
    
    cross_flags: cross cp_full, cp_empty, cp_almost_full, cp_almost_empty {
      illegal_bins full_and_empty = binsof(cp_full.full_high) && binsof(cp_empty.empty_high);
      illegal_bins full_and_aempty = binsof(cp_full.full_high) && binsof(cp_almost_empty.aempty_high);
      illegal_bins empty_and_afull = binsof(cp_empty.empty_high) && binsof(cp_almost_full.afull_high);
      illegal_bins afull_and_aempty = binsof(cp_almost_full.afull_high) && binsof(cp_almost_empty.aempty_high);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 3: Operations Coverage
  // ========================================================================
  covergroup cg_operations @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_operations";
    
    cp_operation: coverpoint current_operation {
      bins write_only = {WRITE_ONLY};
      bins read_only = {READ_ONLY};
      bins simul_rw = {SIMUL_RW};
      bins no_op = {NO_OP};
    }
    
    cp_fifo_state: coverpoint current_state {
      bins empty = {EMPTY};
      bins almost_empty = {ALMOST_EMPTY};
      bins normal = {NORMAL};
      bins almost_full = {ALMOST_FULL};
      bins full = {FULL};
    }
    
    cross_op_state: cross cp_operation, cp_fifo_state {
      bins write_when_full = binsof(cp_operation.write_only) && binsof(cp_fifo_state.full);
      bins read_when_empty = binsof(cp_operation.read_only) && binsof(cp_fifo_state.empty);
      bins simul_when_empty = binsof(cp_operation.simul_rw) && binsof(cp_fifo_state.empty);
      bins simul_when_full = binsof(cp_operation.simul_rw) && binsof(cp_fifo_state.full);
      bins simul_when_normal = binsof(cp_operation.simul_rw) && binsof(cp_fifo_state.normal);
      bins write_when_almost_full = binsof(cp_operation.write_only) && binsof(cp_fifo_state.almost_full);
      bins read_when_almost_empty = binsof(cp_operation.read_only) && binsof(cp_fifo_state.almost_empty);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 4: State Transitions Coverage
  // ========================================================================
  covergroup cg_state_transitions @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_state_transitions";
    
    cp_state_from: coverpoint previous_state {
      bins empty = {EMPTY};
      bins almost_empty = {ALMOST_EMPTY};
      bins normal = {NORMAL};
      bins almost_full = {ALMOST_FULL};
      bins full = {FULL};
    }
    
    cp_state_to: coverpoint current_state {
      bins empty = {EMPTY};
      bins almost_empty = {ALMOST_EMPTY};
      bins normal = {NORMAL};
      bins almost_full = {ALMOST_FULL};
      bins full = {FULL};
    }
    
    cross_transitions: cross cp_state_from, cp_state_to {
      bins empty_to_almost_empty = binsof(cp_state_from.empty) && binsof(cp_state_to.almost_empty);
      bins almost_empty_to_empty = binsof(cp_state_from.almost_empty) && binsof(cp_state_to.empty);
      bins almost_empty_to_normal = binsof(cp_state_from.almost_empty) && binsof(cp_state_to.normal);
      bins normal_to_almost_empty = binsof(cp_state_from.normal) && binsof(cp_state_to.almost_empty);
      bins normal_to_almost_full = binsof(cp_state_from.normal) && binsof(cp_state_to.almost_full);
      bins almost_full_to_normal = binsof(cp_state_from.almost_full) && binsof(cp_state_to.normal);
      bins almost_full_to_full = binsof(cp_state_from.almost_full) && binsof(cp_state_to.full);
      bins full_to_almost_full = binsof(cp_state_from.full) && binsof(cp_state_to.almost_full);
      bins empty_to_empty = binsof(cp_state_from.empty) && binsof(cp_state_to.empty);
      bins full_to_full = binsof(cp_state_from.full) && binsof(cp_state_to.full);
      bins normal_to_normal = binsof(cp_state_from.normal) && binsof(cp_state_to.normal);
      
      illegal_bins empty_to_full = binsof(cp_state_from.empty) && binsof(cp_state_to.full);
      illegal_bins full_to_empty = binsof(cp_state_from.full) && binsof(cp_state_to.empty);
      illegal_bins empty_to_almost_full = binsof(cp_state_from.empty) && binsof(cp_state_to.almost_full);
      illegal_bins full_to_almost_empty = binsof(cp_state_from.full) && binsof(cp_state_to.almost_empty);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 5: Boundary Conditions Coverage
  // ========================================================================
  covergroup cg_boundary_conditions @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_boundary_conditions";
    
    cp_boundaries: coverpoint {count_0_to_1, count_1_to_0, count_1_to_2, count_2_to_1,
                               count_depth_minus_2_to_depth_minus_1, count_depth_minus_1_to_depth_minus_2,
                               count_depth_minus_1_to_depth, count_depth_to_depth_minus_1} {
      bins count_0_to_1 = {8'b10000000};
      bins count_1_to_0 = {8'b01000000};
      bins count_1_to_2 = {8'b00100000};
      bins count_2_to_1 = {8'b00010000};
      bins count_depth_m2_to_depth_m1 = {8'b00001000};
      bins count_depth_m1_to_depth_m2 = {8'b00000100};
      bins count_depth_m1_to_depth = {8'b00000010};
      bins count_depth_to_depth_m1 = {8'b00000001};
    }
    
    cp_count_at_boundary: coverpoint count {
      bins at_zero = {0};
      bins at_one = {1};
      bins at_two = {2};
      bins at_depth_minus_two = {DEPTH-2};
      bins at_depth_minus_one = {DEPTH-1};
      bins at_depth = {DEPTH};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 6: Corner Cases Coverage
  // ========================================================================
  covergroup cg_corner_cases @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_corner_cases";
    
    cp_write_when_full: coverpoint write_when_full {
      bins occurred = {1};
    }
    
    cp_read_when_empty: coverpoint read_when_empty {
      bins occurred = {1};
    }
    
    cp_simul_rw_full: coverpoint simul_rw_full {
      bins occurred = {1};
    }
    
    cp_simul_rw_empty: coverpoint simul_rw_empty {
      bins occurred = {1};
    }
    
    cp_wr_ptr_wrap: coverpoint wr_ptr_wrap {
      bins occurred = {1};
    }
    
    cp_rd_ptr_wrap: coverpoint rd_ptr_wrap {
      bins occurred = {1};
    }
    
    cp_back_to_back_wr: coverpoint back_to_back_wr {
      bins occurred = {1};
    }
    
    cp_back_to_back_rd: coverpoint back_to_back_rd {
      bins occurred = {1};
    }
    
    cp_sustained_full: coverpoint full {
      bins sustained[] = (1[*10:100]);
    }
    
    cp_sustained_empty: coverpoint empty {
      bins sustained[] = (1[*10:100]);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 7: Data Patterns Coverage
  // ========================================================================
  covergroup cg_data_patterns @(posedge clk iff wr_valid);
    option.per_instance = 1;
    option.name = "cg_data_patterns";
    
    cp_data_pattern: coverpoint wr_data_pattern {
      bins all_zeros = {ALL_ZEROS};
      bins all_ones = {ALL_ONES};
      bins alternating_01 = {ALTERNATING_01};
      bins alternating_10 = {ALTERNATING_10};
      bins walking_ones = {WALKING_ONES};
      bins walking_zeros = {WALKING_ZEROS};
      bins random = {RANDOM};
    }
    
    cp_wr_data_bits: coverpoint wr_data {
      bins all_zeros = {0};
      bins all_ones = {'1};
      bins others = default;
    }
    
    cp_wr_data_toggle: coverpoint wr_data {
      bins low_bits[] = {[0:15]};
      bins mid_bits[] = {[16:239]};
      bins high_bits[] = {[240:255]};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 8: Pointer Values Coverage
  // ========================================================================
  covergroup cg_pointer_values @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_pointer_values";
    
    cp_wr_ptr: coverpoint wr_ptr {
      bins ptr_values[] = {[0:DEPTH-1]};
      bins ptr_zero = {0};
      bins ptr_max = {DEPTH-1};
      bins ptr_mid = {DEPTH/2};
    }
    
    cp_rd_ptr: coverpoint rd_ptr {
      bins ptr_values[] = {[0:DEPTH-1]};
      bins ptr_zero = {0};
      bins ptr_max = {DEPTH-1};
      bins ptr_mid = {DEPTH/2};
    }
    
    cp_ptr_relation: coverpoint ptr_relationship {
      bins ptr_equal = {PTR_EQUAL};
      bins wr_ahead = {WR_AHEAD};
      bins rd_ahead = {RD_AHEAD};
    }
    
    cross_ptrs: cross cp_wr_ptr, cp_rd_ptr {
      bins ptrs_equal = binsof(cp_wr_ptr) intersect binsof(cp_rd_ptr);
      bins wr_ahead_of_rd = binsof(cp_wr_ptr) && binsof(cp_rd_ptr) 
                            with (cp_wr_ptr > cp_rd_ptr);
      bins rd_ahead_of_wr = binsof(cp_wr_ptr) && binsof(cp_rd_ptr) 
                            with (cp_rd_ptr > cp_wr_ptr);
    }
    
    cross_ptr_state: cross cp_ptr_relation, cp_fifo_state {
      bins equal_when_empty = binsof(cp_ptr_relation.ptr_equal) && binsof(cp_fifo_state.empty);
      bins equal_when_full = binsof(cp_ptr_relation.ptr_equal) && binsof(cp_fifo_state.full);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 9: Count Changes Coverage
  // ========================================================================
  covergroup cg_count_changes @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_count_changes";
    
    cp_count_delta: coverpoint count_change {
      bins increment = {INCREMENT};
      bins decrement = {DECREMENT};
      bins no_change = {NO_CHANGE};
    }
    
    cp_count_before: coverpoint prev_count {
      bins zero = {0};
      bins one = {1};
      bins depth_minus_one = {DEPTH-1};
      bins depth = {DEPTH};
      bins others[] = {[2:DEPTH-2]};
    }
    
    cp_count_after: coverpoint count {
      bins zero = {0};
      bins one = {1};
      bins depth_minus_one = {DEPTH-1};
      bins depth = {DEPTH};
      bins others[] = {[2:DEPTH-2]};
    }
    
    cross_count_change: cross cp_count_delta, cp_count_before {
      bins inc_from_zero = binsof(cp_count_delta.increment) && binsof(cp_count_before.zero);
      bins inc_from_one = binsof(cp_count_delta.increment) && binsof(cp_count_before.one);
      bins inc_to_depth = binsof(cp_count_delta.increment) && binsof(cp_count_before.depth_minus_one);
      bins dec_from_depth = binsof(cp_count_delta.decrement) && binsof(cp_count_before.depth);
      bins dec_to_zero = binsof(cp_count_delta.decrement) && binsof(cp_count_before.one);
      bins no_change_at_zero = binsof(cp_count_delta.no_change) && binsof(cp_count_before.zero);
      bins no_change_at_depth = binsof(cp_count_delta.no_change) && binsof(cp_count_before.depth);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 10: Reset Scenarios Coverage
  // ========================================================================
  covergroup cg_reset_scenarios @(negedge rst_n);
    option.per_instance = 1;
    option.name = "cg_reset_scenarios";
    
    cp_reset_state: coverpoint current_state {
      bins reset_when_empty = {EMPTY};
      bins reset_when_almost_empty = {ALMOST_EMPTY};
      bins reset_when_normal = {NORMAL};
      bins reset_when_almost_full = {ALMOST_FULL};
      bins reset_when_full = {FULL};
    }
    
    cp_reset_operation: coverpoint current_operation {
      bins reset_during_write = {WRITE_ONLY};
      bins reset_during_read = {READ_ONLY};
      bins reset_during_simul_rw = {SIMUL_RW};
      bins reset_during_idle = {NO_OP};
    }
    
    cp_reset_count: coverpoint count {
      bins reset_at_zero = {0};
      bins reset_at_partial[] = {[1:DEPTH-1]};
      bins reset_at_full = {DEPTH};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 11: Simultaneous R/W Coverage
  // ========================================================================
  covergroup cg_simultaneous_rw @(posedge clk iff (wr_en && rd_en));
    option.per_instance = 1;
    option.name = "cg_simultaneous_rw";
    
    cp_simul_state: coverpoint current_state {
      bins simul_empty = {EMPTY};
      bins simul_almost_empty = {ALMOST_EMPTY};
      bins simul_normal = {NORMAL};
      bins simul_almost_full = {ALMOST_FULL};
      bins simul_full = {FULL};
    }
    
    cp_simul_count: coverpoint count {
      bins at_zero = {0};
      bins at_one = {1};
      bins at_mid[] = {[2:DEPTH-2]};
      bins at_depth_minus_one = {DEPTH-1};
      bins at_depth = {DEPTH};
    }
    
    cp_simul_result: coverpoint count_change {
      bins stayed_same = {NO_CHANGE};
      bins increased = {INCREMENT};
      bins decreased = {DECREMENT};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 12: Back-to-Back Operations Coverage
  // ========================================================================
  covergroup cg_back_to_back @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_back_to_back";
    
    cp_consecutive_writes: coverpoint wr_valid {
      bins single_write = (1);
      bins two_writes = (1[*2]);
      bins three_writes = (1[*3]);
      bins many_writes = (1[*4:$]);
    }
    
    cp_consecutive_reads: coverpoint rd_valid {
      bins single_read = (1);
      bins two_reads = (1[*2]);
      bins three_reads = (1[*3]);
      bins many_reads = (1[*4:$]);
    }
    
    cp_alternating: coverpoint {wr_valid, rd_valid} {
      bins wr_then_rd = (2'b10 => 2'b01);
      bins rd_then_wr = (2'b01 => 2'b10);
      bins wr_wr = (2'b10 => 2'b10);
      bins rd_rd = (2'b01 => 2'b01);
      bins simul = (2'b11);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 13: Flag Transitions Coverage
  // ========================================================================
  covergroup cg_flag_transitions @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_flag_transitions";
    
    cp_full_trans: coverpoint {prev_full, full} {
      bins full_assert = (2'b01);
      bins full_deassert = (2'b10);
      bins full_stable_low = (2'b00);
      bins full_stable_high = (2'b11);
    }
    
    cp_empty_trans: coverpoint {prev_empty, empty} {
      bins empty_assert = (2'b01);
      bins empty_deassert = (2'b10);
      bins empty_stable_low = (2'b00);
      bins empty_stable_high = (2'b11);
    }
    
    cp_afull_trans: coverpoint {prev_almost_full, almost_full} {
      bins afull_assert = (2'b01);
      bins afull_deassert = (2'b10);
      bins afull_stable_low = (2'b00);
      bins afull_stable_high = (2'b11);
    }
    
    cp_aempty_trans: coverpoint {prev_almost_empty, almost_empty} {
      bins aempty_assert = (2'b01);
      bins aempty_deassert = (2'b10);
      bins aempty_stable_low = (2'b00);
      bins aempty_stable_high = (2'b11);
    }
    
    cross_flag_trans: cross cp_full_trans, cp_empty_trans {
      illegal_bins both_assert = binsof(cp_full_trans.full_assert) && 
                                 binsof(cp_empty_trans.empty_assert);
      illegal_bins both_high = binsof(cp_full_trans.full_stable_high) && 
                               binsof(cp_empty_trans.empty_stable_high);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 14: Enable Signal Coverage
  // ========================================================================
  covergroup cg_enable_signals @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_enable_signals";
    
    cp_wr_en: coverpoint wr_en {
      bins low = {0};
      bins high = {1};
    }
    
    cp_rd_en: coverpoint rd_en {
      bins low = {0};
      bins high = {1};
    }
    
    cross_enables: cross cp_wr_en, cp_rd_en {
      bins both_low = binsof(cp_wr_en.low) && binsof(cp_rd_en.low);
      bins wr_only = binsof(cp_wr_en.high) && binsof(cp_rd_en.low);
      bins rd_only = binsof(cp_wr_en.low) && binsof(cp_rd_en.high);
      bins both_high = binsof(cp_wr_en.high) && binsof(cp_rd_en.high);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 15: Valid Signal Coverage
  // ========================================================================
  covergroup cg_valid_signals @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_valid_signals";
    
    cp_wr_valid: coverpoint wr_valid {
      bins not_valid = {0};
      bins valid = {1};
    }
    
    cp_rd_valid: coverpoint rd_valid {
      bins not_valid = {0};
      bins valid = {1};
    }
    
    cross_valid: cross cp_wr_valid, cp_rd_valid {
      bins both_invalid = binsof(cp_wr_valid.not_valid) && binsof(cp_rd_valid.not_valid);
      bins wr_valid_only = binsof(cp_wr_valid.valid) && binsof(cp_rd_valid.not_valid);
      bins rd_valid_only = binsof(cp_wr_valid.not_valid) && binsof(cp_rd_valid.valid);
      bins both_valid = binsof(cp_wr_valid.valid) && binsof(cp_rd_valid.valid);
    }
    
    cross_valid_state: cross cp_wr_valid, cp_rd_valid, cp_fifo_state {
      bins wr_valid_not_full = binsof(cp_wr_valid.valid) && 
                               (!binsof(cp_fifo_state.full));
      bins rd_valid_not_empty = binsof(cp_rd_valid.valid) && 
                                (!binsof(cp_fifo_state.empty));
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 16: Pointer Wraparound Coverage
  // ========================================================================
  covergroup cg_pointer_wraparound @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_pointer_wraparound";
    
    cp_wr_ptr_at_max: coverpoint wr_ptr {
      bins at_max = {DEPTH-1};
      bins not_at_max = {[0:DEPTH-2]};
    }
    
    cp_rd_ptr_at_max: coverpoint rd_ptr {
      bins at_max = {DEPTH-1};
      bins not_at_max = {[0:DEPTH-2]};
    }
    
    cp_wr_wrap_event: coverpoint {wr_ptr, wr_valid} {
      bins wrap_occurs = {[DEPTH-1:DEPTH-1], 1'b1};
    }
    
    cp_rd_wrap_event: coverpoint {rd_ptr, rd_valid} {
      bins wrap_occurs = {[DEPTH-1:DEPTH-1], 1'b1};
    }
    
    cp_wr_ptr_sequence: coverpoint wr_ptr {
      bins wrap_sequence = (DEPTH-1 => 0);
    }
    
    cp_rd_ptr_sequence: coverpoint rd_ptr {
      bins wrap_sequence = (DEPTH-1 => 0);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 17: Data Integrity Coverage
  // ========================================================================
  covergroup cg_data_integrity @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_data_integrity";
    
    cp_rd_data: coverpoint rd_data {
      bins all_zeros = {0};
      bins all_ones = {'1};
      bins low_range[] = {[1:63]};
      bins mid_range[] = {[64:191]};
      bins high_range[] = {[192:254]};
    }
    
    cp_rd_data_when_valid: coverpoint rd_data iff (rd_valid) {
      bins valid_data[] = {[0:$]};
    }
    
    cp_data_match: coverpoint (wr_data == rd_data) iff (wr_valid && rd_valid) {
      bins match = {1};
      bins mismatch = {0};
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 18: Timing Coverage
  // ========================================================================
  covergroup cg_timing @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_timing";
    
    cp_operation_spacing: coverpoint current_operation {
      bins continuous_write = (WRITE_ONLY[*3:$]);
      bins continuous_read = (READ_ONLY[*3:$]);
      bins continuous_simul = (SIMUL_RW[*3:$]);
      bins mixed_ops = default sequence;
    }
    
    cp_idle_cycles: coverpoint current_operation {
      bins no_idle = (NO_OP[*0]);
      bins short_idle = (NO_OP[*1:2]);
      bins medium_idle = (NO_OP[*3:10]);
      bins long_idle = (NO_OP[*11:$]);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 19: Stress Scenarios Coverage
  // ========================================================================
  covergroup cg_stress_scenarios @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_stress_scenarios";
    
    cp_rapid_fill: coverpoint count {
      bins rapid_fill = (0 => DEPTH);
    }
    
    cp_rapid_empty: coverpoint count {
      bins rapid_empty = (DEPTH => 0);
    }
    
    cp_oscillation: coverpoint count {
      bins low_to_high = (0 => DEPTH);
      bins high_to_low = (DEPTH => 0);
      bins oscillate = (0 => DEPTH => 0);
    }
    
    cp_sustained_activity: coverpoint {wr_valid, rd_valid} {
      bins sustained_wr = (2'b10[*10:$]);
      bins sustained_rd = (2'b01[*10:$]);
      bins sustained_both = (2'b11[*10:$]);
    }
  endgroup
  
  // ========================================================================
  // COVERGROUP 20: Edge Cases Coverage
  // ========================================================================
  covergroup cg_edge_cases @(posedge clk);
    option.per_instance = 1;
    option.name = "cg_edge_cases";
    
    cp_single_entry: coverpoint (count == 1) {
      bins single_entry = {1};
    }
    
    cp_operations_at_single: coverpoint current_operation iff (count == 1) {
      bins write_at_single = {WRITE_ONLY};
      bins read_at_single = {READ_ONLY};
      bins simul_at_single = {SIMUL_RW};
    }
    
    cp_full_minus_one: coverpoint (count == DEPTH-1) {
      bins almost_full_count = {1};
    }
    
    cp_operations_at_almost_full: coverpoint current_operation iff (count == DEPTH-1) {
      bins write_at_almost_full = {WRITE_ONLY};
      bins read_at_almost_full = {READ_ONLY};
      bins simul_at_almost_full = {SIMUL_RW};
    }
    
    cp_ptr_collision_empty: coverpoint {(wr_ptr == rd_ptr), empty} {
      bins collision_when_empty = {2'b11};
    }
    
    cp_ptr_collision_full: coverpoint {(wr_ptr == rd_ptr), full} {
      bins collision_when_full = {2'b11};
    }
  endgroup
  
  // ========================================================================
  // Constructor and Sampling Functions
  // ========================================================================
  function new();
    cg_count_values = new();
    cg_flag_states = new();
    cg_operations = new();
    cg_state_transitions = new();
    cg_boundary_conditions = new();
    cg_corner_cases = new();
    cg_data_patterns = new();
    cg_pointer_values = new();
    cg_count_changes = new();
    cg_reset_scenarios = new();
    cg_simultaneous_rw = new();
    cg_back_to_back = new();
    cg_flag_transitions = new();
    cg_enable_signals = new();
    cg_valid_signals = new();
    cg_pointer_wraparound = new();
    cg_data_integrity = new();
    cg_timing = new();
    cg_stress_scenarios = new();
    cg_edge_cases = new();
  endfunction
  
  function void sample(
    input logic i_clk,
    input logic i_rst_n,
    input logic i_wr_en,
    input logic i_rd_en,
    input logic [DATA_WIDTH-1:0] i_wr_data,
    input logic [DATA_WIDTH-1:0] i_rd_data,
    input logic i_full,
    input logic i_empty,
    input logic i_almost_full,
    input logic i_almost_empty,
    input logic [COUNT_WIDTH-1:0] i_count,
    input logic [ADDR_WIDTH-1:0] i_wr_ptr,
    input logic [ADDR_WIDTH-1:0] i_rd_ptr
  );
    clk = i_clk;
    rst_n = i_rst_n;
    wr_en = i_wr_en;
    rd_en = i_rd_en;
    wr_data = i_wr_data;
    rd_data = i_rd_data;
    full = i_full;
    empty = i_empty;
    almost_full = i_almost_full;
    almost_empty = i_almost_empty;
    count = i_count;
    wr_ptr = i_wr_ptr;
    rd_ptr = i_rd_ptr;
    
    cg_count_values.sample();
    cg_flag_states.sample();
    cg_operations.sample();
    cg_state_transitions.sample();
    cg_boundary_conditions.sample();
    cg_corner_cases.sample();
    cg_data_patterns.sample();
    cg_pointer_values.sample();
    cg_count_changes.sample();
    cg_simultaneous_rw.sample();
    cg_back_to_back.sample();
    cg_flag_transitions.sample();
    cg_enable_signals.sample();
    cg_valid_signals.sample();
    cg_pointer_wraparound.sample();
    cg_data_integrity.sample();
    cg_timing.sample();
    cg_stress_scenarios.sample();
    cg_edge_cases.sample();
  endfunction
  
endclass