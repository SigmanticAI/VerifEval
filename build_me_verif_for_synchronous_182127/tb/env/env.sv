// ============================================================================
// File: sync_fifo_env_pkg.sv
// Description: UVM Environment Package for Synchronous FIFO
// ============================================================================

`ifndef SYNC_FIFO_ENV_PKG_SV
`define SYNC_FIFO_ENV_PKG_SV

package sync_fifo_env_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"
  
  import sync_fifo_agent_pkg::*;

  `include "sync_fifo_scoreboard.sv"
  `include "sync_fifo_coverage.sv"
  `include "sync_fifo_virtual_sequencer.sv"
  `include "sync_fifo_env.sv"

endpackage : sync_fifo_env_pkg

`endif // SYNC_FIFO_ENV_PKG_SV

// ============================================================================
// File: sync_fifo_scoreboard.sv
// Description: Scoreboard for Synchronous FIFO verification
// ============================================================================

class sync_fifo_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(sync_fifo_scoreboard)

  // Analysis imports
  uvm_analysis_imp_write #(sync_fifo_transaction, sync_fifo_scoreboard) write_export;
  uvm_analysis_imp_read #(sync_fifo_transaction, sync_fifo_scoreboard) read_export;

  // Configuration
  int DATA_WIDTH = 8;
  int DEPTH = 16;

  // Reference model - queue to store expected data
  sync_fifo_transaction reference_queue[$];
  
  // Statistics
  int write_count;
  int read_count;
  int match_count;
  int mismatch_count;
  int overflow_attempts;
  int underflow_attempts;
  
  // Current FIFO state tracking
  int current_count;
  bit current_full;
  bit current_empty;
  bit current_almost_full;
  bit current_almost_empty;
  
  // Flags for tracking
  bit reset_occurred;

  function new(string name = "sync_fifo_scoreboard", uvm_component parent = null);
    super.new(name, parent);
    write_export = new("write_export", this);
    read_export = new("read_export", this);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    if (!uvm_config_db#(int)::get(this, "", "DATA_WIDTH", DATA_WIDTH))
      `uvm_info(get_type_name(), "DATA_WIDTH not set, using default 8", UVM_MEDIUM)
    
    if (!uvm_config_db#(int)::get(this, "", "DEPTH", DEPTH))
      `uvm_info(get_type_name(), "DEPTH not set, using default 16", UVM_MEDIUM)
      
    write_count = 0;
    read_count = 0;
    match_count = 0;
    mismatch_count = 0;
    overflow_attempts = 0;
    underflow_attempts = 0;
    current_count = 0;
    current_full = 0;
    current_empty = 1;
    current_almost_full = 0;
    current_almost_empty = 0;
    reset_occurred = 0;
  endfunction

  // Write analysis port implementation
  virtual function void write_write(sync_fifo_transaction trans);
    sync_fifo_transaction cloned_trans;
    
    // Handle reset
    if (!trans.rst_n) begin
      handle_reset();
      return;
    end
    
    // Check for write operation
    if (trans.wr_en) begin
      write_count++;
      
      // Check if write should be accepted
      if (current_full && !trans.rd_en) begin
        // Write to full FIFO without simultaneous read - should be ignored
        overflow_attempts++;
        `uvm_info(get_type_name(), 
                  $sformatf("Write attempt to full FIFO ignored (data=0x%0h)", trans.wr_data), 
                  UVM_HIGH)
      end
      else if (current_empty && trans.rd_en) begin
        // Simultaneous R/W when empty - only write should occur
        $cast(cloned_trans, trans.clone());
        reference_queue.push_back(cloned_trans);
        `uvm_info(get_type_name(), 
                  $sformatf("Write accepted (simultaneous R/W when empty): data=0x%0h, queue_size=%0d", 
                            trans.wr_data, reference_queue.size()), 
                  UVM_HIGH)
      end
      else if (!current_full) begin
        // Normal write operation
        $cast(cloned_trans, trans.clone());
        reference_queue.push_back(cloned_trans);
        `uvm_info(get_type_name(), 
                  $sformatf("Write accepted: data=0x%0h, queue_size=%0d", 
                            trans.wr_data, reference_queue.size()), 
                  UVM_HIGH)
      end
    end
    
    // Update state based on transaction
    update_state(trans);
  endfunction

  // Read analysis port implementation
  virtual function void write_read(sync_fifo_transaction trans);
    sync_fifo_transaction expected_trans;
    
    // Handle reset
    if (!trans.rst_n) begin
      return; // Already handled in write_write
    end
    
    // Check for read operation
    if (trans.rd_en) begin
      read_count++;
      
      // Check if read should be accepted
      if (current_empty && !trans.wr_en) begin
        // Read from empty FIFO without simultaneous write - should be ignored
        underflow_attempts++;
        `uvm_info(get_type_name(), 
                  "Read attempt from empty FIFO ignored", 
                  UVM_HIGH)
      end
      else if (current_full && trans.wr_en) begin
        // Simultaneous R/W when full - only read should occur
        if (reference_queue.size() > 0) begin
          expected_trans = reference_queue.pop_front();
          check_read_data(trans, expected_trans);
        end
        else begin
          `uvm_error(get_type_name(), "Reference queue empty during read from full FIFO!")
        end
      end
      else if (!current_empty) begin
        // Normal read operation
        if (reference_queue.size() > 0) begin
          expected_trans = reference_queue.pop_front();
          check_read_data(trans, expected_trans);
        end
        else begin
          `uvm_error(get_type_name(), "Reference queue empty during read!")
        end
      end
    end
  endfunction

  // Check read data against expected
  virtual function void check_read_data(sync_fifo_transaction actual, sync_fifo_transaction expected);
    if (actual.rd_data === expected.wr_data) begin
      match_count++;
      `uvm_info(get_type_name(), 
                $sformatf("READ MATCH: expected=0x%0h, actual=0x%0h", 
                          expected.wr_data, actual.rd_data), 
                UVM_HIGH)
    end
    else begin
      mismatch_count++;
      `uvm_error(get_type_name(), 
                 $sformatf("READ MISMATCH: expected=0x%0h, actual=0x%0h", 
                           expected.wr_data, actual.rd_data))
    end
  endfunction

  // Update internal state tracking
  virtual function void update_state(sync_fifo_transaction trans);
    bit write_occurs, read_occurs;
    
    // Determine if operations actually occur
    write_occurs = trans.wr_en && (!current_full || (current_full && trans.rd_en));
    read_occurs = trans.rd_en && (!current_empty || (current_empty && trans.wr_en));
    
    // Handle simultaneous operations
    if (current_empty && trans.wr_en && trans.rd_en) begin
      write_occurs = 1;
      read_occurs = 0;
    end
    else if (current_full && trans.wr_en && trans.rd_en) begin
      write_occurs = 0;
      read_occurs = 1;
    end
    
    // Update count
    if (write_occurs && !read_occurs) begin
      current_count++;
    end
    else if (read_occurs && !write_occurs) begin
      current_count--;
    end
    // If both occur, count stays same
    
    // Bounds checking
    if (current_count  DEPTH) current_count = DEPTH;
    
    // Update flags
    current_empty = (current_count == 0);
    current_full = (current_count == DEPTH);
    current_almost_empty = (current_count == 1);
    current_almost_full = (current_count == DEPTH - 1);
    
    // Check DUT flags against expected
    check_flags(trans);
  endfunction

  // Check flags
  virtual function void check_flags(sync_fifo_transaction trans);
    if (trans.empty !== current_empty) begin
      `uvm_error(get_type_name(), 
                 $sformatf("EMPTY flag mismatch: expected=%0b, actual=%0b, count=%0d", 
                           current_empty, trans.empty, current_count))
    end
    
    if (trans.full !== current_full) begin
      `uvm_error(get_type_name(), 
                 $sformatf("FULL flag mismatch: expected=%0b, actual=%0b, count=%0d", 
                           current_full, trans.full, current_count))
    end
    
    if (trans.almost_empty !== current_almost_empty) begin
      `uvm_error(get_type_name(), 
                 $sformatf("ALMOST_EMPTY flag mismatch: expected=%0b, actual=%0b, count=%0d", 
                           current_almost_empty, trans.almost_empty, current_count))
    end
    
    if (trans.almost_full !== current_almost_full) begin
      `uvm_error(get_type_name(), 
                 $sformatf("ALMOST_FULL flag mismatch: expected=%0b, actual=%0b, count=%0d", 
                           current_almost_full, trans.almost_full, current_count))
    end
    
    if (trans.count !== current_count) begin
      `uvm_error(get_type_name(), 
                 $sformatf("COUNT mismatch: expected=%0d, actual=%0d", 
                           current_count, trans.count))
    end
    
    // Check mutual exclusion
    if (trans.full && trans.empty) begin
      `uvm_error(get_type_name(), "FULL and EMPTY both asserted simultaneously!")
    end
  endfunction

  // Handle reset
  virtual function void handle_reset();
    `uvm_info(get_type_name(), "Reset detected - clearing reference model", UVM_MEDIUM)
    reference_queue.delete();
    current_count = 0;
    current_full = 0;
    current_empty = 1;
    current_almost_full = 0;
    current_almost_empty = 0;
    reset_occurred = 1;
  endfunction

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    `uvm_info(get_type_name(), "    SCOREBOARD FINAL REPORT", UVM_LOW)
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Total Writes:          %0d", write_count), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Total Reads:           %0d", read_count), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Data Matches:          %0d", match_count), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Data Mismatches:       %0d", mismatch_count), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Overflow Attempts:     %0d", overflow_attempts), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Underflow Attempts:    %0d", underflow_attempts), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Final Queue Size:      %0d", reference_queue.size()), UVM_LOW)
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    
    if (mismatch_count > 0) begin
      `uvm_error(get_type_name(), $sformatf("TEST FAILED: %0d data mismatches detected!", mismatch_count))
    end
    else if (reference_queue.size() != 0) begin
      `uvm_warning(get_type_name(), $sformatf("Reference queue not empty at end: %0d entries remaining", reference_queue.size()))
    end
    else begin
      `uvm_info(get_type_name(), "TEST PASSED: All data matched!", UVM_LOW)
    end
  endfunction

endclass : sync_fifo_scoreboard

// ============================================================================
// File: sync_fifo_coverage.sv
// Description: Functional coverage collector for Synchronous FIFO
// ============================================================================

class sync_fifo_coverage extends uvm_subscriber #(sync_fifo_transaction);
  `uvm_component_utils(sync_fifo_coverage)

  // Configuration
  int DATA_WIDTH = 8;
  int DEPTH = 16;

  // Coverage variables
  bit wr_en;
  bit rd_en;
  bit rst_n;
  bit full;
  bit empty;
  bit almost_full;
  bit almost_empty;
  int count;
  bit [31:0] wr_data;
  bit [31:0] rd_data;
  
  // Derived variables
  typedef enum {WRITE_ONLY, READ_ONLY, SIMULTANEOUS_RW, NO_OPERATION} operation_type_e;
  operation_type_e operation_type;
  
  typedef enum {STATE_EMPTY, STATE_ALMOST_EMPTY, STATE_NORMAL, STATE_ALMOST_FULL, STATE_FULL} fifo_state_e;
  fifo_state_e fifo_state;
  fifo_state_e prev_fifo_state;
  
  typedef enum {ALL_ZEROS, ALL_ONES, ALTERNATING_01, ALTERNATING_10, RANDOM} data_pattern_e;
  data_pattern_e data_pattern;

  // Covergroups
  
  // Count coverage - cover all possible count values
  covergroup cg_count;
    cp_count: coverpoint count {
      bins count_values[] = {[0:DEPTH]};
      option.at_least = 1;
    }
  endgroup

  // Flag coverage
  covergroup cg_flags;
    cp_full: coverpoint full {
      bins full_low = {0};
      bins full_high = {1};
    }
    
    cp_empty: coverpoint empty {
      bins empty_low = {0};
      bins empty_high = {1};
    }
    
    cp_almost_full: coverpoint almost_full {
      bins almost_full_low = {0};
      bins almost_full_high = {1};
    }
    
    cp_almost_empty: coverpoint almost_empty {
      bins almost_empty_low = {0};
      bins almost_empty_high = {1};
    }
    
    // Cross coverage for flag combinations
    flag_combinations: cross cp_full, cp_empty, cp_almost_full, cp_almost_empty {
      illegal_bins full_and_empty = binsof(cp_full.full_high) && binsof(cp_empty.empty_high);
    }
  endgroup

  // Operation coverage
  covergroup cg_operations;
    cp_operation: coverpoint operation_type {
      bins write_only = {WRITE_ONLY};
      bins read_only = {READ_ONLY};
      bins simultaneous_rw = {SIMULTANEOUS_RW};
      bins no_operation = {NO_OPERATION};
    }
    
    cp_state: coverpoint fifo_state {
      bins empty = {STATE_EMPTY};
      bins almost_empty = {STATE_ALMOST_EMPTY};
      bins normal = {STATE_NORMAL};
      bins almost_full = {STATE_ALMOST_FULL};
      bins full = {STATE_FULL};
    }
    
    // Cross coverage - operations in different states
    operation_in_state: cross cp_operation, cp_state;
  endgroup

  // State transition coverage
  covergroup cg_transitions;
    cp_state_transition: coverpoint fifo_state {
      bins empty_to_almost_empty = (STATE_EMPTY => STATE_ALMOST_EMPTY);
      bins almost_empty_to_empty = (STATE_ALMOST_EMPTY => STATE_EMPTY);
      bins almost_empty_to_normal = (STATE_ALMOST_EMPTY => STATE_NORMAL);
      bins normal_to_almost_empty = (STATE_NORMAL => STATE_ALMOST_EMPTY);
      bins normal_to_almost_full = (STATE_NORMAL => STATE_ALMOST_FULL);
      bins almost_full_to_normal = (STATE_ALMOST_FULL => STATE_NORMAL);
      bins almost_full_to_full = (STATE_ALMOST_FULL => STATE_FULL);
      bins full_to_almost_full = (STATE_FULL => STATE_ALMOST_FULL);
      bins empty_to_normal = (STATE_EMPTY => STATE_NORMAL);
      bins normal_to_full = (STATE_NORMAL => STATE_FULL);
      bins full_to_normal = (STATE_FULL => STATE_NORMAL);
      bins normal_to_empty = (STATE_NORMAL => STATE_EMPTY);
    }
  endgroup

  // Corner case coverage
  covergroup cg_corner_cases;
    cp_write_when_full: coverpoint (wr_en && full && !rd_en) {
      bins write_to_full = {1};
    }
    
    cp_read_when_empty: coverpoint (rd_en && empty && !wr_en) {
      bins read_from_empty = {1};
    }
    
    cp_simul_rw_when_full: coverpoint (wr_en && rd_en && full) {
      bins simul_rw_full = {1};
    }
    
    cp_simul_rw_when_empty: coverpoint (wr_en && rd_en && empty) {
      bins simul_rw_empty = {1};
    }
    
    cp_back_to_back_writes: coverpoint (wr_en && !rd_en && !full) {
      bins consecutive_writes = (1 => 1);
    }
    
    cp_back_to_back_reads: coverpoint (rd_en && !wr_en && !empty) {
      bins consecutive_reads = (1 => 1);
    }
    
    cp_reset: coverpoint rst_n {
      bins reset_asserted = {0};
      bins reset_deasserted = {1};
      bins reset_transition = (1 => 0 => 1);
    }
  endgroup

  // Boundary coverage
  covergroup cg_boundaries;
    cp_count_boundaries: coverpoint count {
      bins count_0_to_1 = (0 => 1);
      bins count_1_to_0 = (1 => 0);
      bins count_1_to_2 = (1 => 2);
      bins count_2_to_1 = (2 => 1);
    }
    
    cp_almost_full_boundary: coverpoint count {
      bins approach_almost_full = ([0:DEPTH-2] => DEPTH-1);
      bins leave_almost_full = (DEPTH-1 => [0:DEPTH-2]);
    }
    
    cp_full_boundary: coverpoint count {
      bins approach_full = ([0:DEPTH-1] => DEPTH);
      bins leave_full = (DEPTH => [0:DEPTH-1]);
    }
  endgroup

  // Data pattern coverage
  covergroup cg_data_patterns;
    cp_data_pattern: coverpoint data_pattern {
      bins all_zeros = {ALL_ZEROS};
      bins all_ones = {ALL_ONES};
      bins alternating_01 = {ALTERNATING_01};
      bins alternating_10 = {ALTERNATING_10};
      bins random = {RANDOM};
    }
  endgroup

  function new(string name = "sync_fifo_coverage", uvm_component parent = null);
    super.new(name, parent);
    cg_count = new();
    cg_flags = new();
    cg_operations = new();
    cg_transitions = new();
    cg_corner_cases = new();
    cg_boundaries = new();
    cg_data_patterns = new();
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    if (!uvm_config_db#(int)::get(this, "", "DATA_WIDTH", DATA_WIDTH))
      `uvm_info(get_type_name(), "DATA_WIDTH not set, using default 8", UVM_MEDIUM)
    
    if (!uvm_config_db#(int)::get(this, "", "DEPTH", DEPTH))
      `uvm_info(get_type_name(), "DEPTH not set, using default 16", UVM_MEDIUM)
      
    prev_fifo_state = STATE_EMPTY;
  endfunction

  virtual function void write(sync_fifo_transaction t);
    // Sample transaction fields
    wr_en = t.wr_en;
    rd_en = t.rd_en;
    rst_n = t.rst_n;
    full = t.full;
    empty = t.empty;
    almost_full = t.almost_full;
    almost_empty = t.almost_empty;
    count = t.count;
    wr_data = t.wr_data;
    rd_data = t.rd_data;
    
    // Determine operation type
    if (wr_en && rd_en)
      operation_type = SIMULTANEOUS_RW;
    else if (wr_en)
      operation_type = WRITE_ONLY;
    else if (rd_en)
      operation_type = READ_ONLY;
    else
      operation_type = NO_OPERATION;
    
    // Determine FIFO state
    if (empty)
      fifo_state = STATE_EMPTY;
    else if (almost_empty)
      fifo_state = STATE_ALMOST_EMPTY;
    else if (full)
      fifo_state = STATE_FULL;
    else if (almost_full)
      fifo_state = STATE_ALMOST_FULL;
    else
      fifo_state = STATE_NORMAL;
    
    // Determine data pattern
    if (wr_en) begin
      if (wr_data == 0)
        data_pattern = ALL_ZEROS;
      else if (wr_data == {DATA_WIDTH{1'b1}})
        data_pattern = ALL_ONES;
      else if (wr_data == {{(DATA_WIDTH/2){2'b01}}})
        data_pattern = ALTERNATING_01;
      else if (wr_data == {{(DATA_WIDTH/2){2'b10}}})
        data_pattern = ALTERNATING_10;
      else
        data_pattern = RANDOM;
    end
    
    // Sample covergroups
    if (rst_n) begin
      cg_count.sample();
      cg_flags.sample();
      cg_operations.sample();
      cg_transitions.sample();
      cg_corner_cases.sample();
      cg_boundaries.sample();
      if (wr_en)
        cg_data_patterns.sample();
    end
    
    // Update previous state
    prev_fifo_state = fifo_state;
  endfunction

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    `uvm_info(get_type_name(), "    COVERAGE REPORT", UVM_LOW)
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Count Coverage:        %0.2f%%", cg_count.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Flag Coverage:         %0.2f%%", cg_flags.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Operation Coverage:    %0.2f%%", cg_operations.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Transition Coverage:   %0.2f%%", cg_transitions.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Corner Case Coverage:  %0.2f%%", cg_corner_cases.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Boundary Coverage:     %0.2f%%", cg_boundaries.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), $sformatf("Data Pattern Coverage: %0.2f%%", cg_data_patterns.get_coverage()), UVM_LOW)
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
  endfunction

endclass : sync_fifo_coverage

// ============================================================================
// File: sync_fifo_virtual_sequencer.sv
// Description: Virtual sequencer for coordinating sequences
// ============================================================================

class sync_fifo_virtual_sequencer extends uvm_sequencer;
  `uvm_component_utils(sync_fifo_virtual_sequencer)

  // Agent sequencers
  sync_fifo_sequencer fifo_sequencer;

  function new(string name = "sync_fifo_virtual_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
  endfunction

endclass : sync_fifo_virtual_sequencer

// ============================================================================
// File: sync_fifo_env.sv
// Description: UVM Environment for Synchronous FIFO
// ============================================================================

class sync_fifo_env extends uvm_env;
  `uvm_component_utils(sync_fifo_env)

  // Configuration
  int DATA_WIDTH = 8;
  int DEPTH = 16;

  // Components
  sync_fifo_agent fifo_agent;
  sync_fifo_scoreboard scoreboard;
  sync_fifo_coverage coverage;
  sync_fifo_virtual_sequencer virtual_sequencer;

  function new(string name = "sync_fifo_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    // Get configuration
    if (!uvm_config_db#(int)::get(this, "", "DATA_WIDTH", DATA_WIDTH))
      `uvm_info(get_type_name(), "DATA_WIDTH not set, using default 8", UVM_MEDIUM)
    
    if (!uvm_config_db#(int)::get(this, "", "DEPTH", DEPTH))
      `uvm_info(get_type_name(), "DEPTH not set, using default 16", UVM_MEDIUM)
    
    // Set configuration for sub-components
    uvm_config_db#(int)::set(this, "fifo_agent", "DATA_WIDTH", DATA_WIDTH);
    uvm_config_db#(int)::set(this, "fifo_agent", "DEPTH", DEPTH);
    uvm_config_db#(int)::set(this, "scoreboard", "DATA_WIDTH", DATA_WIDTH);
    uvm_config_db#(int)::set(this, "scoreboard", "DEPTH", DEPTH);
    uvm_config_db#(int)::set(this, "coverage", "DATA_WIDTH", DATA_WIDTH);
    uvm_config_db#(int)::set(this, "coverage", "DEPTH", DEPTH);
    
    // Create components
    fifo_agent = sync_fifo_agent::type_id::create("fifo_agent", this);
    scoreboard = sync_fifo_scoreboard::type_id::create("scoreboard", this);
    coverage = sync_fifo_coverage::type_id::create("coverage", this);
    virtual_sequencer = sync_fifo_virtual_sequencer::type_id::create("virtual_sequencer", this);
  endfunction

  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    
    // Connect agent monitor to scoreboard
    fifo_agent.monitor.write_ap.connect(scoreboard.write_export);
    fifo_agent.monitor.read_ap.connect(scoreboard.read_export);
    
    // Connect agent monitor to coverage
    fifo_agent.monitor.analysis_port.connect(coverage.analysis_export);
    
    // Connect virtual sequencer to agent sequencer
    virtual_sequencer.fifo_sequencer = fifo_agent.sequencer;
    
    `uvm_info(get_type_name(), "Environment connections completed", UVM_MEDIUM)
  endfunction

  virtual function void end_of_elaboration_phase(uvm_phase phase);
    super.end_of_elaboration_phase(phase);
    `uvm_info(get_type_name(), "Environment elaboration completed", UVM_MEDIUM)
    print();
  endfunction

  virtual function void start_of_simulation_phase(uvm_phase phase);
    super.start_of_simulation_phase(phase);
    `uvm_info(get_type_name(), 
              $sformatf("Starting simulation with DATA_WIDTH=%0d, DEPTH=%0d", DATA_WIDTH, DEPTH), 
              UVM_LOW)
  endfunction

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
    `uvm_info(get_type_name(), "    ENVIRONMENT FINAL REPORT", UVM_LOW)
    `uvm_info(get_type_name(), "========================================", UVM_LOW)
  endfunction

endclass : sync_fifo_env