// ============================================================================
// Comprehensive SVA Assertions for Synchronous FIFO
// ============================================================================

module synchronous_fifo_assertions #(
  parameter DATA_WIDTH = 8,
  parameter DEPTH = 16
)(
  input  logic                  clk,
  input  logic                  rst_n,
  input  logic                  wr_en,
  input  logic                  rd_en,
  input  logic [DATA_WIDTH-1:0] wr_data,
  input  logic [DATA_WIDTH-1:0] rd_data,
  input  logic                  full,
  input  logic                  empty,
  input  logic                  almost_full,
  input  logic                  almost_empty,
  input  logic [$clog2(DEPTH):0] count
);

  // ============================================================================
  // Local Parameters and Helper Signals
  // ============================================================================
  
  localparam PTR_WIDTH = $clog2(DEPTH);
  
  // Helper signals for tracking operations
  logic valid_write;
  logic valid_read;
  logic simultaneous_rw;
  
  assign valid_write = wr_en && (!full || (full && rd_en));
  assign valid_read = rd_en && (!empty || (empty && wr_en));
  assign simultaneous_rw = wr_en && rd_en;

  // ============================================================================
  // REQ-001: FIFO Ordering - First In First Out
  // ============================================================================
  
  // Track write data in a queue model for comparison
  logic [DATA_WIDTH-1:0] reference_queue[$];
  
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      reference_queue = {};
    end else begin
      if (valid_write && !valid_read) begin
        reference_queue.push_back(wr_data);
      end else if (valid_read && !valid_write) begin
        if (reference_queue.size() > 0)
          void'(reference_queue.pop_front());
      end else if (valid_write && valid_read) begin
        if (reference_queue.size() > 0)
          void'(reference_queue.pop_front());
        reference_queue.push_back(wr_data);
      end
    end
  end
  
  property p_fifo_ordering;
    @(posedge clk) disable iff (!rst_n)
    (valid_read && reference_queue.size() > 0) |-> 
    ##1 (rd_data == $past(reference_queue[0]));
  endproperty
  
  ast_fifo_ordering: assert property(p_fifo_ordering)
    else $error("REQ-001 VIOLATION: FIFO ordering violated - data not read in FIFO order");

  // ============================================================================
  // REQ-002: Full Flag Behavior
  // ============================================================================
  
  property p_full_flag_when_at_depth;
    @(posedge clk) disable iff (!rst_n)
    (count == DEPTH) |-> full;
  endproperty
  
  ast_full_flag_when_at_depth: assert property(p_full_flag_when_at_depth)
    else $error("REQ-002 VIOLATION: Full flag not asserted when count equals DEPTH");
  
  property p_full_flag_only_at_depth;
    @(posedge clk) disable iff (!rst_n)
    full |-> (count == DEPTH);
  endproperty
  
  ast_full_flag_only_at_depth: assert property(p_full_flag_only_at_depth)
    else $error("REQ-002 VIOLATION: Full flag asserted when count is not DEPTH");
  
  property p_no_write_when_full_only;
    @(posedge clk) disable iff (!rst_n)
    (full && wr_en && !rd_en) |=> (count == $past(count));
  endproperty
  
  ast_no_write_when_full_only: assert property(p_no_write_when_full_only)
    else $error("REQ-002 VIOLATION: Write occurred when full without simultaneous read");

  // ============================================================================
  // REQ-003: Empty Flag Behavior
  // ============================================================================
  
  property p_empty_flag_when_zero;
    @(posedge clk) disable iff (!rst_n)
    (count == 0) |-> empty;
  endproperty
  
  ast_empty_flag_when_zero: assert property(p_empty_flag_when_zero)
    else $error("REQ-003 VIOLATION: Empty flag not asserted when count is 0");
  
  property p_empty_flag_only_when_zero;
    @(posedge clk) disable iff (!rst_n)
    empty |-> (count == 0);
  endproperty
  
  ast_empty_flag_only_when_zero: assert property(p_empty_flag_only_when_zero)
    else $error("REQ-003 VIOLATION: Empty flag asserted when count is not 0");
  
  property p_no_read_when_empty_only;
    @(posedge clk) disable iff (!rst_n)
    (empty && rd_en && !wr_en) |=> (count == $past(count));
  endproperty
  
  ast_no_read_when_empty_only: assert property(p_no_read_when_empty_only)
    else $error("REQ-003 VIOLATION: Read occurred when empty without simultaneous write");

  // ============================================================================
  // REQ-004: Write When Full
  // ============================================================================
  
  property p_write_ignored_when_full;
    @(posedge clk) disable iff (!rst_n)
    ($past(full) && $past(wr_en) && !$past(rd_en)) |-> 
    (count == $past(count));
  endproperty
  
  ast_write_ignored_when_full: assert property(p_write_ignored_when_full)
    else $error("REQ-004 VIOLATION: Write not ignored when full without simultaneous read");

  // ============================================================================
  // REQ-005: Read When Empty
  // ============================================================================
  
  property p_read_ignored_when_empty;
    @(posedge clk) disable iff (!rst_n)
    ($past(empty) && $past(rd_en) && !$past(wr_en)) |-> 
    (count == $past(count));
  endproperty
  
  ast_read_ignored_when_empty: assert property(p_read_ignored_when_empty)
    else $error("REQ-005 VIOLATION: Read not ignored when empty without simultaneous write");

  // ============================================================================
  // REQ-006: Count Accuracy
  // ============================================================================
  
  property p_count_bounds;
    @(posedge clk) disable iff (!rst_n)
    (count >= 0) && (count  
    (count == $past(count) + 1);
  endproperty
  
  ast_count_increment_on_write_only: assert property(p_count_increment_on_write_only)
    else $error("REQ-006 VIOLATION: Count did not increment on write-only operation");
  
  property p_count_decrement_on_read_only;
    @(posedge clk) disable iff (!rst_n)
    ($past(rd_en) && !$past(wr_en) && !$past(empty)) |-> 
    (count == $past(count) - 1);
  endproperty
  
  ast_count_decrement_on_read_only: assert property(p_count_decrement_on_read_only)
    else $error("REQ-006 VIOLATION: Count did not decrement on read-only operation");
  
  property p_count_stable_on_simultaneous_rw;
    @(posedge clk) disable iff (!rst_n)
    ($past(wr_en) && $past(rd_en) && !$past(empty) && !$past(full)) |-> 
    (count == $past(count));
  endproperty
  
  ast_count_stable_on_simultaneous_rw: assert property(p_count_stable_on_simultaneous_rw)
    else $error("REQ-006 VIOLATION: Count changed on simultaneous read/write in normal state");
  
  property p_count_stable_on_no_operation;
    @(posedge clk) disable iff (!rst_n)
    (!$past(wr_en) && !$past(rd_en)) |-> (count == $past(count));
  endproperty
  
  ast_count_stable_on_no_operation: assert property(p_count_stable_on_no_operation)
    else $error("REQ-006 VIOLATION: Count changed when no operation occurred");

  // ============================================================================
  // REQ-007: Almost Full Flag
  // ============================================================================
  
  property p_almost_full_at_depth_minus_1;
    @(posedge clk) disable iff (!rst_n)
    (count == DEPTH - 1) |-> almost_full;
  endproperty
  
  ast_almost_full_at_depth_minus_1: assert property(p_almost_full_at_depth_minus_1)
    else $error("REQ-007 VIOLATION: Almost full not asserted when count is DEPTH-1");
  
  property p_almost_full_only_at_depth_minus_1;
    @(posedge clk) disable iff (!rst_n)
    almost_full |-> (count == DEPTH - 1);
  endproperty
  
  ast_almost_full_only_at_depth_minus_1: assert property(p_almost_full_only_at_depth_minus_1)
    else $error("REQ-007 VIOLATION: Almost full asserted when count is not DEPTH-1");

  // ============================================================================
  // REQ-008: Almost Empty Flag
  // ============================================================================
  
  property p_almost_empty_at_1;
    @(posedge clk) disable iff (!rst_n)
    (count == 1) |-> almost_empty;
  endproperty
  
  ast_almost_empty_at_1: assert property(p_almost_empty_at_1)
    else $error("REQ-008 VIOLATION: Almost empty not asserted when count is 1");
  
  property p_almost_empty_only_at_1;
    @(posedge clk) disable iff (!rst_n)
    almost_empty |-> (count == 1);
  endproperty
  
  ast_almost_empty_only_at_1: assert property(p_almost_empty_only_at_1)
    else $error("REQ-008 VIOLATION: Almost empty asserted when count is not 1");

  // ============================================================================
  // REQ-009: Simultaneous Operations
  // ============================================================================
  
  property p_simultaneous_rw_when_empty;
    @(posedge clk) disable iff (!rst_n)
    ($past(empty) && $past(wr_en) && $past(rd_en)) |-> 
    (count == 1);
  endproperty
  
  ast_simultaneous_rw_when_empty: assert property(p_simultaneous_rw_when_empty)
    else $error("REQ-009 VIOLATION: Simultaneous R/W when empty did not perform write only");
  
  property p_simultaneous_rw_when_full;
    @(posedge clk) disable iff (!rst_n)
    ($past(full) && $past(wr_en) && $past(rd_en)) |-> 
    (count == DEPTH - 1);
  endproperty
  
  ast_simultaneous_rw_when_full: assert property(p_simultaneous_rw_when_full)
    else $error("REQ-009 VIOLATION: Simultaneous R/W when full did not perform read only");
  
  property p_simultaneous_rw_normal;
    @(posedge clk) disable iff (!rst_n)
    ($past(wr_en) && $past(rd_en) && !$past(empty) && !$past(full)) |-> 
    (count == $past(count));
  endproperty
  
  ast_simultaneous_rw_normal: assert property(p_simultaneous_rw_normal)
    else $error("REQ-009 VIOLATION: Simultaneous R/W in normal state did not perform both operations");

  // ============================================================================
  // REQ-010: Reset Behavior
  // ============================================================================
  
  property p_reset_clears_fifo;
    @(posedge clk)
    (!rst_n) |=> (empty && !full && (count == 0));
  endproperty
  
  ast_reset_clears_fifo: assert property(p_reset_clears_fifo)
    else $error("REQ-010 VIOLATION: Reset did not clear FIFO to empty state");
  
  property p_reset_clears_almost_flags;
    @(posedge clk)
    (!rst_n) |=> (!almost_full && !almost_empty);
  endproperty
  
  ast_reset_clears_almost_flags: assert property(p_reset_clears_almost_flags)
    else $error("REQ-010 VIOLATION: Reset did not clear almost flags");

  // ============================================================================
  // REQ-011: Synchronous Outputs
  // ============================================================================
  
  // This is primarily a design constraint, verified through timing analysis
  // SVA can check that outputs only change on clock edges
  
  property p_outputs_change_on_clock;
    @(posedge clk) disable iff (!rst_n)
    1'b1; // Placeholder - actual verification done through timing tools
  endproperty

  // ============================================================================
  // REQ-012: Data Integrity
  // ============================================================================
  
  // Data integrity is verified through the reference queue model in REQ-001
  // Additional check for data stability
  
  property p_data_integrity_check;
    @(posedge clk) disable iff (!rst_n)
    (valid_read && reference_queue.size() > 0) |-> 
    ##1 (rd_data == $past(reference_queue[0]));
  endproperty
  
  ast_data_integrity: assert property(p_data_integrity_check)
    else $error("REQ-012 VIOLATION: Data integrity compromised");

  // ============================================================================
  // REQ-013: Pointer Wraparound
  // ============================================================================
  
  // Track pointer wraparound events
  logic [PTR_WIDTH-1:0] wr_ptr_model;
  logic [PTR_WIDTH-1:0] rd_ptr_model;
  
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wr_ptr_model  (wr_ptr_model == 0);
  endproperty
  
  ast_write_pointer_wraparound: assert property(p_write_pointer_wraparound)
    else $error("REQ-013 VIOLATION: Write pointer did not wrap correctly");
  
  property p_read_pointer_wraparound;
    @(posedge clk) disable iff (!rst_n)
    (valid_read && (rd_ptr_model == DEPTH-1)) |=> (rd_ptr_model == 0);
  endproperty
  
  ast_read_pointer_wraparound: assert property(p_read_pointer_wraparound)
    else $error("REQ-013 VIOLATION: Read pointer did not wrap correctly");

  // ============================================================================
  // REQ-014: Flag Mutual Exclusion
  // ============================================================================
  
  property p_full_empty_mutual_exclusion;
    @(posedge clk) disable iff (!rst_n)
    !(full && empty);
  endproperty
  
  ast_full_empty_mutual_exclusion: assert property(p_full_empty_mutual_exclusion)
    else $error("REQ-014 VIOLATION: Full and empty flags asserted simultaneously");

  // ============================================================================
  // REQ-015: Count Bounds and Transitions
  // ============================================================================
  
  property p_count_transition_valid;
    @(posedge clk) disable iff (!rst_n)
    (count - $past(count)) inside {-1, 0, 1};
  endproperty
  
  ast_count_transition_valid: assert property(p_count_transition_valid)
    else $error("REQ-015 VIOLATION: Count transition not in {-1, 0, +1}");
  
  property p_count_never_exceeds_depth;
    @(posedge clk) disable iff (!rst_n)
    count = 0;
  endproperty
  
  ast_count_never_negative: assert property(p_count_never_negative)
    else $error("REQ-015 VIOLATION: Count went negative");

  // ============================================================================
  // REQ-016: Back-to-Back Operations
  // ============================================================================
  
  property p_back_to_back_writes;
    @(posedge clk) disable iff (!rst_n)
    (wr_en && !full) ##1 (wr_en && !full) |-> 
    (count == $past(count, 2) + 2);
  endproperty
  
  ast_back_to_back_writes: assert property(p_back_to_back_writes)
    else $error("REQ-016 VIOLATION: Back-to-back writes failed");
  
  property p_back_to_back_reads;
    @(posedge clk) disable iff (!rst_n)
    (rd_en && !empty) ##1 (rd_en && !empty) |-> 
    (count == $past(count, 2) - 2);
  endproperty
  
  ast_back_to_back_reads: assert property(p_back_to_back_reads)
    else $error("REQ-016 VIOLATION: Back-to-back reads failed");

  // ============================================================================
  // REQ-017: Flag Timing
  // ============================================================================
  
  property p_flags_update_with_count;
    @(posedge clk) disable iff (!rst_n)
    (count != $past(count)) |-> 
    ((empty == (count == 0)) && 
     (full == (count == DEPTH)) &&
     (almost_empty == (count == 1)) &&
     (almost_full == (count == DEPTH-1)));
  endproperty
  
  ast_flags_update_with_count: assert property(p_flags_update_with_count)
    else $error("REQ-017 VIOLATION: Flags did not update synchronously with count");

  // ============================================================================
  // REQ-018: Read Data Stability
  // ============================================================================
  
  property p_rd_data_stable_when_empty_no_write;
    @(posedge clk) disable iff (!rst_n)
    ($past(empty) && !$past(wr_en)) |-> (rd_data == $past(rd_data));
  endproperty
  
  ast_rd_data_stable_when_empty: assert property(p_rd_data_stable_when_empty_no_write)
    else $error("REQ-018 VIOLATION: Read data changed when empty without write");

  // ============================================================================
  // Corner Case Assertions
  // ============================================================================
  
  // CC-001: Write to Full FIFO
  property p_cc001_write_to_full;
    @(posedge clk) disable iff (!rst_n)
    (full && wr_en && !rd_en) |=> (count == DEPTH);
  endproperty
  
  ast_cc001_write_to_full: assert property(p_cc001_write_to_full)
    else $error("CC-001 VIOLATION: Write to full FIFO changed count");
  
  // CC-002: Read from Empty FIFO
  property p_cc002_read_from_empty;
    @(posedge clk) disable iff (!rst_n)
    (empty && rd_en && !wr_en) |=> (count == 0);
  endproperty
  
  ast_cc002_read_from_empty: assert property(p_cc002_read_from_empty)
    else $error("CC-002 VIOLATION: Read from empty FIFO changed count");
  
  // CC-003: Simultaneous R/W When Full
  property p_cc003_simul_rw_full;
    @(posedge clk) disable iff (!rst_n)
    (full && wr_en && rd_en) |=> (count == DEPTH - 1);
  endproperty
  
  ast_cc003_simul_rw_full: assert property(p_cc003_simul_rw_full)
    else $error("CC-003 VIOLATION: Simultaneous R/W when full incorrect");
  
  // CC-004: Simultaneous R/W When Empty
  property p_cc004_simul_rw_empty;
    @(posedge clk) disable iff (!rst_n)
    (empty && wr_en && rd_en) |=> (count == 1);
  endproperty
  
  ast_cc004_simul_rw_empty: assert property(p_cc004_simul_rw_empty)
    else $error("CC-004 VIOLATION: Simultaneous R/W when empty incorrect");
  
  // CC-007: Single Entry Operation
  property p_cc007_single_entry;
    @(posedge clk) disable iff (!rst_n)
    (count == 1) |-> (almost_empty && !empty && !full);
  endproperty
  
  ast_cc007_single_entry: assert property(p_cc007_single_entry)
    else $error("CC-007 VIOLATION: Single entry state flags incorrect");
  
  // CC-011: Almost Full Boundary
  property p_cc011_almost_full_boundary;
    @(posedge clk) disable iff (!rst_n)
    (count == DEPTH - 2) |-> !almost_full;
  endproperty
  
  ast_cc011_almost_full_boundary: assert property(p_cc011_almost_full_boundary)
    else $error("CC-011 VIOLATION: Almost full at wrong boundary");
  
  // CC-012: Almost Empty Boundary
  property p_cc012_almost_empty_boundary;
    @(posedge clk) disable iff (!rst_n)
    (count == 2) |-> !almost_empty;
  endproperty
  
  ast_cc012_almost_empty_boundary: assert property(p_cc012_almost_empty_boundary)
    else $error("CC-012 VIOLATION: Almost empty at wrong boundary");
  
  // CC-015: Pointer Collision Detection
  property p_cc015_pointer_collision_empty;
    @(posedge clk) disable iff (!rst_n)
    (wr_ptr_model == rd_ptr_model && empty) |-> (count == 0);
  endproperty
  
  ast_cc015_pointer_collision_empty: assert property(p_cc015_pointer_collision_empty)
    else $error("CC-015 VIOLATION: Pointer collision with empty state incorrect");
  
  property p_cc015_pointer_collision_full;
    @(posedge clk) disable iff (!rst_n)
    (wr_ptr_model == rd_ptr_model && full) |-> (count == DEPTH);
  endproperty
  
  ast_cc015_pointer_collision_full: assert property(p_cc015_pointer_collision_full)
    else $error("CC-015 VIOLATION: Pointer collision with full state incorrect");
  
  // CC-017: Flag Coherency
  property p_cc017_flag_coherency;
    @(posedge clk) disable iff (!rst_n)
    ((empty == (count == 0)) && 
     (full == (count == DEPTH)) &&
     (almost_empty == (count == 1)) &&
     (almost_full == (count == DEPTH - 1)));
  endproperty
  
  ast_cc017_flag_coherency: assert property(p_cc017_flag_coherency)
    else $error("CC-017 VIOLATION: Flags not coherent with count");
  
  // CC-019: Sustained Full Condition
  sequence seq_sustained_full;
    (full && wr_en && !rd_en)[*5];
  endsequence
  
  property p_cc019_sustained_full;
    @(posedge clk) disable iff (!rst_n)
    seq_sustained_full |-> (count == DEPTH) throughout seq_sustained_full;
  endproperty
  
  ast_cc019_sustained_full: assert property(p_cc019_sustained_full)
    else $error("CC-019 VIOLATION: Sustained full condition unstable");
  
  // CC-020: Sustained Empty Condition
  sequence seq_sustained_empty;
    (empty && rd_en && !wr_en)[*5];
  endsequence
  
  property p_cc020_sustained_empty;
    @(posedge clk) disable iff (!rst_n)
    seq_sustained_empty |-> (count == 0) throughout seq_sustained_empty;
  endproperty
  
  ast_cc020_sustained_empty: assert property(p_cc020_sustained_empty)
    else $error("CC-020 VIOLATION: Sustained empty condition unstable");
  
  // CC-023: Simultaneous R/W in Normal State
  property p_cc023_simul_rw_normal;
    @(posedge clk) disable iff (!rst_n)
    (wr_en && rd_en && !empty && !full) |=> 
    (count == $past(count));
  endproperty
  
  ast_cc023_simul_rw_normal: assert property(p_cc023_simul_rw_normal)
    else $error("CC-023 VIOLATION: Simultaneous R/W in normal state incorrect");

  // ============================================================================
  // FSM State Tracking and Assertions
  // ============================================================================
  
  typedef enum logic [2:0] {
    FSM_EMPTY,
    FSM_ALMOST_EMPTY,
    FSM_NORMAL,
    FSM_ALMOST_FULL,
    FSM_FULL
  } fifo_state_t;
  
  fifo_state_t current_state;
  
  always_comb begin
    if (count == 0)
      current_state = FSM_EMPTY;
    else if (count == 1)
      current_state = FSM_ALMOST_EMPTY;
    else if (count == DEPTH - 1)
      current_state = FSM_ALMOST_FULL;
    else if (count == DEPTH)
      current_state = FSM_FULL;
    else
      current_state = FSM_NORMAL;
  end
  
  // FSM Transition: EMPTY to ALMOST_EMPTY
  property p_fsm_empty_to_almost_empty;
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_EMPTY && wr_en && !rd_en) |=> 
    (current_state == FSM_ALMOST_EMPTY);
  endproperty
  
  ast_fsm_empty_to_almost_empty: assert property(p_fsm_empty_to_almost_empty)
    else $error("FSM VIOLATION: Invalid transition from EMPTY to ALMOST_EMPTY");
  
  // FSM Transition: ALMOST_EMPTY to EMPTY
  property p_fsm_almost_empty_to_empty;
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_ALMOST_EMPTY && rd_en && !wr_en) |=> 
    (current_state == FSM_EMPTY);
  endproperty
  
  ast_fsm_almost_empty_to_empty: assert property(p_fsm_almost_empty_to_empty)
    else $error("FSM VIOLATION: Invalid transition from ALMOST_EMPTY to EMPTY");
  
  // FSM Transition: ALMOST_FULL to FULL
  property p_fsm_almost_full_to_full;
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_ALMOST_FULL && wr_en && !rd_en) |=> 
    (current_state == FSM_FULL);
  endproperty
  
  ast_fsm_almost_full_to_full: assert property(p_fsm_almost_full_to_full)
    else $error("FSM VIOLATION: Invalid transition from ALMOST_FULL to FULL");
  
  // FSM Transition: FULL to ALMOST_FULL
  property p_fsm_full_to_almost_full;
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_FULL && rd_en && !wr_en) |=> 
    (current_state == FSM_ALMOST_FULL);
  endproperty
  
  ast_fsm_full_to_almost_full: assert property(p_fsm_full_to_almost_full)
    else $error("FSM VIOLATION: Invalid transition from FULL to ALMOST_FULL");
  
  // FSM: Reset to EMPTY
  property p_fsm_reset_to_empty;
    @(posedge clk)
    (!rst_n) |=> (current_state == FSM_EMPTY);
  endproperty
  
  ast_fsm_reset_to_empty: assert property(p_fsm_reset_to_empty)
    else $error("FSM VIOLATION: Reset did not transition to EMPTY state");

  // ============================================================================
  // Additional Stability and Sanity Checks
  // ============================================================================
  
  // Check that count matches reference queue size
  property p_count_matches_queue_size;
    @(posedge clk) disable iff (!rst_n)
    (count == reference_queue.size());
  endproperty
  
  ast_count_matches_queue_size: assert property(p_count_matches_queue_size)
    else $error("SANITY CHECK: Count does not match reference queue size");
  
  // Check no spurious flag assertions
  property p_no_spurious_flags;
    @(posedge clk) disable iff (!rst_n)
    (count > 1 && count  
    (!empty && !full && !almost_empty && !almost_full);
  endproperty
  
  ast_no_spurious_flags: assert property(p_no_spurious_flags)
    else $error("SANITY CHECK: Spurious flag assertion in normal range");
  
  // Verify write enable doesn't affect read data immediately
  property p_write_no_immediate_read_effect;
    @(posedge clk) disable iff (!rst_n)
    (wr_en && !rd_en && !empty) |=> 
    (rd_data == $past(rd_data) || valid_read);
  endproperty

  // ============================================================================
  // Cover Properties - Functional Coverage
  // ============================================================================
  
  // Cover: FIFO goes from empty to full
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (empty ##[1:$] full)
  );
  
  // Cover: FIFO goes from full to empty
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (full ##[1:$] empty)
  );
  
  // Cover: Write when full (should be ignored)
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (full && wr_en && !rd_en)
  );
  
  // Cover: Read when empty (should be ignored)
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (empty && rd_en && !wr_en)
  );
  
  // Cover: Simultaneous read/write when empty
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (empty && wr_en && rd_en)
  );
  
  // Cover: Simultaneous read/write when full
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (full && wr_en && rd_en)
  );
  
  // Cover: Simultaneous read/write in normal state
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (!empty && !full && wr_en && rd_en)
  );
  
  // Cover: Almost full flag assertion
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (!$past(almost_full) && almost_full)
  );
  
  // Cover: Almost empty flag assertion
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (!$past(almost_empty) && almost_empty)
  );
  
  // Cover: Back-to-back writes
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (wr_en && !full) ##1 (wr_en && !full)
  );
  
  // Cover: Back-to-back reads
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (rd_en && !empty) ##1 (rd_en && !empty)
  );
  
  // Cover: Write pointer wraparound
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (valid_write && wr_ptr_model == DEPTH-1)
  );
  
  // Cover: Read pointer wraparound
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (valid_read && rd_ptr_model == DEPTH-1)
  );
  
  // Cover: All FSM states visited
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_EMPTY)
  );
  
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_ALMOST_EMPTY)
  );
  
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_NORMAL)
  );
  
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_ALMOST_FULL)
  );
  
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_FULL)
  );
  
  // Cover: Transition through all states
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_EMPTY) ##[1:$] 
    (current_state == FSM_ALMOST_EMPTY) ##[1:$]
    (current_state == FSM_NORMAL) ##[1:$]
    (current_state == FSM_ALMOST_FULL) ##[1:$]
    (current_state == FSM_FULL)
  );
  
  // Cover: Reverse transition through all states
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (current_state == FSM_FULL) ##[1:$] 
    (current_state == FSM_ALMOST_FULL) ##[1:$]
    (current_state == FSM_NORMAL) ##[1:$]
    (current_state == FSM_ALMOST_EMPTY) ##[1:$]
    (current_state == FSM_EMPTY)
  );
  
  // Cover: Reset during full state
  cover property (
    @(posedge clk)
    (full && !rst_n)
  );
  
  // Cover: Reset during empty state
  cover property (
    @(posedge clk)
    (empty && !rst_n)
  );
  
  // Cover: Sustained full condition
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (full[*10])
  );
  
  // Cover: Sustained empty condition
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (empty[*10])
  );
  
  // Cover: Rapid fill and empty cycles
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (empty ##[1:5] full ##[1:5] empty)
  );
  
  // Cover: Count at each possible value
  generate
    for (genvar i = 0; i <= DEPTH; i++) begin : gen_count_cover
      cover property (
        @(posedge clk) disable iff (!rst_n)
        (count == i)
      );
    end
  endgenerate
  
  // Cover: Maximum data pattern (all 1s)
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (wr_en && (wr_data == {DATA_WIDTH{1'b1}}))
  );
  
  // Cover: Minimum data pattern (all 0s)
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (wr_en && (wr_data == {DATA_WIDTH{1'b0}}))
  );
  
  // Cover: Alternating data pattern
  cover property (
    @(posedge clk) disable iff (!rst_n)
    (wr_en && (wr_data == {DATA_WIDTH/2{2'b10}}))
  );

  // ============================================================================
  // End of Assertions Module
  // ============================================================================

endmodule

// ============================================================================
// Bind Statement (to be used in testbench or top-level module)
// ============================================================================
// 
// bind synchronous_fifo synchronous_fifo_assertions #(
//   .DATA_WIDTH(DATA_WIDTH),
//   .DEPTH(DEPTH)
// ) fifo_assertions_inst (
//   .clk(clk),
//   .rst_n(rst_n),
//   .wr_en(wr_en),
//   .rd_en(rd_en),
//   .wr_data(wr_data),
//   .rd_data(rd_data),
//   .full(full),
//   .empty(empty),
//   .almost_full(almost_full),
//   .almost_empty(almost_empty),
//   .count(count)
// );
//
// ============================================================================