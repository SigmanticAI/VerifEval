//==============================================================================
// SVA Assertions for Synchronous FIFO Design
// Generated for comprehensive verification coverage
//==============================================================================

module sync_fifo_assertions #(
    parameter DATA_WIDTH = 32,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH),
    parameter ALMOST_FULL_THRESHOLD = (DEPTH * 3) / 4,
    parameter ALMOST_EMPTY_THRESHOLD = DEPTH / 4
)(
    input logic clk,
    input logic rst_n,
    input logic wr_en,
    input logic rd_en,
    input logic [DATA_WIDTH-1:0] wr_data,
    input logic [DATA_WIDTH-1:0] rd_data,
    input logic full,
    input logic empty,
    input logic almost_full,
    input logic almost_empty,
    input logic error,
    input logic [ADDR_WIDTH:0] count,
    input logic [ADDR_WIDTH-1:0] wr_ptr,
    input logic [ADDR_WIDTH-1:0] rd_ptr
);

    //==========================================================================
    // Helper Functions and Local Variables
    //==========================================================================
    
    // Previous cycle values for edge detection
    logic prev_wr_en, prev_rd_en, prev_full, prev_empty;
    logic [ADDR_WIDTH:0] prev_count;
    
    always_ff @(posedge clk) begin
        if (rst_n) begin
            prev_wr_en <= wr_en;
            prev_rd_en <= rd_en;
            prev_full <= full;
            prev_empty <= empty;
            prev_count <= count;
        end
    end
    
    // Operation detection
    logic write_op = wr_en && !full;
    logic read_op = rd_en && !empty;
    logic overflow_op = wr_en && full && !rd_en;
    logic underflow_op = rd_en && empty && !wr_en;
    logic simultaneous_op = wr_en && rd_en;
    
    //==========================================================================
    // PROPERTY DEFINITIONS
    //==========================================================================
    
    //--------------------------------------------------------------------------
    // REQ-001: FIFO shall store data when wr_en is asserted and FIFO is not full
    //--------------------------------------------------------------------------
    property p_write_when_not_full;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && !full && !rd_en) |=> (count == $past(count) + 1);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-002: FIFO shall output data when rd_en is asserted and FIFO is not empty
    //--------------------------------------------------------------------------
    property p_read_when_not_empty;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && !empty && !wr_en) |=> (count == $past(count) - 1);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-003: rd_data shall be combinational (same cycle as rd_en)
    //--------------------------------------------------------------------------
    property p_read_data_combinational;
        @(posedge clk) disable iff (!rst_n)
        rd_en && !empty |-> ##0 $stable(rd_data) throughout (rd_en[*1]);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-004: full flag shall be asserted when count equals DEPTH
    //--------------------------------------------------------------------------
    property p_full_flag_correct;
        @(posedge clk) disable iff (!rst_n)
        (count == DEPTH) <-> full;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-005: empty flag shall be asserted when count equals 0
    //--------------------------------------------------------------------------
    property p_empty_flag_correct;
        @(posedge clk) disable iff (!rst_n)
        (count == 0) <-> empty;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-006: almost_full flag shall be asserted when count >= 3/4 of DEPTH
    //--------------------------------------------------------------------------
    property p_almost_full_flag_correct;
        @(posedge clk) disable iff (!rst_n)
        (count >= ALMOST_FULL_THRESHOLD) <-> almost_full;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-007: almost_empty flag shall be asserted when count <= 1/4 of DEPTH
    //--------------------------------------------------------------------------
    property p_almost_empty_flag_correct;
        @(posedge clk) disable iff (!rst_n)
        (count <= ALMOST_EMPTY_THRESHOLD) <-> almost_empty;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-008: Simultaneous read/write operations when FIFO is full
    //--------------------------------------------------------------------------
    property p_simultaneous_rw_when_full;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && rd_en && full) |=> (count == $past(count) && !full);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-009: Simultaneous read/write operations when FIFO is empty
    //--------------------------------------------------------------------------
    property p_simultaneous_rw_when_empty;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && rd_en && empty) |=> (count == $past(count) && !empty);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-010: error flag on overflow (write to full FIFO without read)
    //--------------------------------------------------------------------------
    property p_overflow_error;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && full && !rd_en) |=> error;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-011: error flag on underflow (read from empty FIFO without write)
    //--------------------------------------------------------------------------
    property p_underflow_error;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && empty && !wr_en) |=> error;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-012: error flag shall be sticky (remain asserted once set)
    //--------------------------------------------------------------------------
    property p_error_sticky;
        @(posedge clk) disable iff (!rst_n)
        error |=> error;
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-013: count shall accurately reflect number of valid entries
    //--------------------------------------------------------------------------
    property p_count_increment;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && !rd_en && !full) |=> (count == $past(count) + 1);
    endproperty
    
    property p_count_decrement;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && !wr_en && !empty) |=> (count == $past(count) - 1);
    endproperty
    
    property p_count_stable_simultaneous;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && rd_en && !empty && !full) |=> (count == $past(count));
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-014: Write and read pointers shall wrap around correctly
    //--------------------------------------------------------------------------
    property p_wr_ptr_wraparound;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && !full && wr_ptr == DEPTH-1) |=> (wr_ptr == 0);
    endproperty
    
    property p_rd_ptr_wraparound;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && !empty && rd_ptr == DEPTH-1) |=> (rd_ptr == 0);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-015: Reset shall clear all pointers, count, and error flag
    //--------------------------------------------------------------------------
    property p_reset_clears_state;
        @(posedge clk)
        !rst_n |=> (count == 0 && wr_ptr == 0 && rd_ptr == 0 && !error);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-016: Reset shall set empty flag and clear all other status flags
    //--------------------------------------------------------------------------
    property p_reset_sets_flags;
        @(posedge clk)
        !rst_n |=> (empty && !full && !almost_full && !almost_empty);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-017: Data integrity - FIFO order preserved
    //--------------------------------------------------------------------------
    property p_fifo_order;
        logic [DATA_WIDTH-1:0] written_data;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && !full, written_data = wr_data) |-> 
        ##[1:DEPTH] (rd_en && !empty && rd_data == written_data);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-018: No data loss during normal operations
    //--------------------------------------------------------------------------
    property p_no_data_loss;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && !full) |-> ##[1:DEPTH] (rd_en && !empty);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-019: Status flags shall never have conflicting states
    //--------------------------------------------------------------------------
    property p_no_conflicting_flags;
        @(posedge clk) disable iff (!rst_n)
        !(full && empty);
    endproperty
    
    //--------------------------------------------------------------------------
    // REQ-020: Count shall never exceed DEPTH
    //--------------------------------------------------------------------------
    property p_count_bounds;
        @(posedge clk) disable iff (!rst_n)
        count <= DEPTH;
    endproperty
    
    //--------------------------------------------------------------------------
    // Additional Corner Case Properties
    //--------------------------------------------------------------------------
    
    // CC-003 & CC-004: Simultaneous operations
    property p_simultaneous_ops_valid;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && rd_en) |=> (count == $past(count) + (($past(empty) ? 1 : 0) - ($past(full) ? 1 : 0)));
    endproperty
    
    // CC-007: Pointer wraparound integrity
    property p_pointer_integrity;
        @(posedge clk) disable iff (!rst_n)
        (wr_ptr < DEPTH) && (rd_ptr < DEPTH);
    endproperty
    
    // CC-014: Error flag persistence until reset
    property p_error_until_reset;
        @(posedge clk) disable iff (!rst_n)
        $rose(error) |-> error s_until !rst_n;
    endproperty
    
    // FSM State Consistency
    property p_fsm_state_consistency;
        @(posedge clk) disable iff (!rst_n)
        (empty -> count == 0) &&
        (full -> count == DEPTH) &&
        (almost_empty -> count <= ALMOST_EMPTY_THRESHOLD) &&
        (almost_full -> count >= ALMOST_FULL_THRESHOLD);
    endproperty
    
    //==========================================================================
    // ASSERTION BINDINGS
    //==========================================================================
    
    // Functional Requirements
    ast_write_when_not_full: assert property(p_write_when_not_full)
        else $error("REQ-001 VIOLATION: Write operation failed when FIFO not full");
        
    ast_read_when_not_empty: assert property(p_read_when_not_empty)
        else $error("REQ-002 VIOLATION: Read operation failed when FIFO not empty");
        
    ast_read_data_combinational: assert property(p_read_data_combinational)
        else $error("REQ-003 VIOLATION: Read data not combinational");
        
    ast_full_flag_correct: assert property(p_full_flag_correct)
        else $error("REQ-004 VIOLATION: Full flag incorrect");
        
    ast_empty_flag_correct: assert property(p_empty_flag_correct)
        else $error("REQ-005 VIOLATION: Empty flag incorrect");
        
    ast_almost_full_flag_correct: assert property(p_almost_full_flag_correct)
        else $error("REQ-006 VIOLATION: Almost full flag incorrect");
        
    ast_almost_empty_flag_correct: assert property(p_almost_empty_flag_correct)
        else $error("REQ-007 VIOLATION: Almost empty flag incorrect");
        
    ast_simultaneous_rw_when_full: assert property(p_simultaneous_rw_when_full)
        else $error("REQ-008 VIOLATION: Simultaneous R/W when full failed");
        
    ast_simultaneous_rw_when_empty: assert property(p_simultaneous_rw_when_empty)
        else $error("REQ-009 VIOLATION: Simultaneous R/W when empty failed");
        
    ast_overflow_error: assert property(p_overflow_error)
        else $error("REQ-010 VIOLATION: Overflow error not detected");
        
    ast_underflow_error: assert property(p_underflow_error)
        else $error("REQ-011 VIOLATION: Underflow error not detected");
        
    ast_error_sticky: assert property(p_error_sticky)
        else $error("REQ-012 VIOLATION: Error flag not sticky");
        
    ast_count_increment: assert property(p_count_increment)
        else $error("REQ-013 VIOLATION: Count increment incorrect");
        
    ast_count_decrement: assert property(p_count_decrement)
        else $error("REQ-013 VIOLATION: Count decrement incorrect");
        
    ast_count_stable_simultaneous: assert property(p_count_stable_simultaneous)
        else $error("REQ-013 VIOLATION: Count not stable during simultaneous ops");
        
    ast_wr_ptr_wraparound: assert property(p_wr_ptr_wraparound)
        else $error("REQ-014 VIOLATION: Write pointer wraparound failed");
        
    ast_rd_ptr_wraparound: assert property(p_rd_ptr_wraparound)
        else $error("REQ-014 VIOLATION: Read pointer wraparound failed");
        
    ast_reset_clears_state: assert property(p_reset_clears_state)
        else $error("REQ-015 VIOLATION: Reset did not clear state");
        
    ast_reset_sets_flags: assert property(p_reset_sets_flags)
        else $error("REQ-016 VIOLATION: Reset did not set flags correctly");
        
    ast_fifo_order: assert property(p_fifo_order)
        else $error("REQ-017 VIOLATION: FIFO order not preserved");
        
    ast_no_data_loss: assert property(p_no_data_loss)
        else $error("REQ-018 VIOLATION: Data loss detected");
        
    ast_no_conflicting_flags: assert property(p_no_conflicting_flags)
        else $error("REQ-019 VIOLATION: Conflicting flags detected");
        
    ast_count_bounds: assert property(p_count_bounds)
        else $error("REQ-020 VIOLATION: Count exceeded DEPTH");
        
    // Corner Case Assertions
    ast_simultaneous_ops_valid: assert property(p_simultaneous_ops_valid)
        else $error("CORNER CASE VIOLATION: Simultaneous operations invalid");
        
    ast_pointer_integrity: assert property(p_pointer_integrity)
        else $error("CORNER CASE VIOLATION: Pointer out of bounds");
        
    ast_error_until_reset: assert property(p_error_until_reset)
        else $error("CORNER CASE VIOLATION: Error flag cleared without reset");
        
    ast_fsm_state_consistency: assert property(p_fsm_state_consistency)
        else $error("FSM VIOLATION: State inconsistency detected");
    
    //==========================================================================
    // COVER PROPERTIES
    //==========================================================================
    
    // Basic Operations Coverage
    cov_write_operation: cover property(
        @(posedge clk) disable iff (!rst_n)
        wr_en && !full
    );
    
    cov_read_operation: cover property(
        @(posedge clk) disable iff (!rst_n)
        rd_en && !empty
    );
    
    cov_simultaneous_operations: cover property(
        @(posedge clk) disable iff (!rst_n)
        wr_en && rd_en
    );
    
    // State Coverage
    cov_fifo_empty: cover property(
        @(posedge clk) disable iff (!rst_n)
        empty
    );
    
    cov_fifo_full: cover property(
        @(posedge clk) disable iff (!rst_n)
        full
    );
    
    cov_fifo_almost_empty: cover property(
        @(posedge clk) disable iff (!rst_n)
        almost_empty && !empty
    );
    
    cov_fifo_almost_full: cover property(
        @(posedge clk) disable iff (!rst_n)
        almost_full && !full
    );
    
    cov_fifo_normal: cover property(
        @(posedge clk) disable iff (!rst_n)
        !empty && !full && !almost_empty && !almost_full
    );
    
    // Error Conditions Coverage
    cov_overflow_error: cover property(
        @(posedge clk) disable iff (!rst_n)
        wr_en && full && !rd_en
    );
    
    cov_underflow_error: cover property(
        @(posedge clk) disable iff (!rst_n)
        rd_en && empty && !wr_en
    );
    
    cov_error_flag_set: cover property(
        @(posedge clk) disable iff (!rst_n)
        error
    );
    
    // Transition Coverage
    cov_empty_to_normal: cover property(
        @(posedge clk) disable iff (!rst_n)
        $past(empty) && !empty && !almost_empty
    );
    
    cov_full_to_normal: cover property(
        @(posedge clk) disable iff (!rst_n)
        $past(full) && !full && !almost_full
    );
    
    cov_wraparound_write: cover property(
        @(posedge clk) disable iff (!rst_n)
        wr_en && !full && wr_ptr == DEPTH-1
    );
    
    cov_wraparound_read: cover property(
        @(posedge clk) disable iff (!rst_n)
        rd_en && !empty && rd_ptr == DEPTH-1
    );
    
    // Corner Cases Coverage
    cov_reset_during_write: cover property(
        @(posedge clk)
        $past(wr_en) && !rst_n
    );
    
    cov_reset_during_read: cover property(
        @(posedge clk)
        $past(rd_en) && !rst_n
    );
    
    cov_max_count: cover property(
        @(posedge clk) disable iff (!rst_n)
        count == DEPTH
    );
    
    cov_threshold_boundaries: cover property(
        @(posedge clk) disable iff (!rst_n)
        (count == ALMOST_EMPTY_THRESHOLD) || (count == ALMOST_FULL_THRESHOLD)
    );
    
    // Sequence Coverage
    cov_fill_and_empty_sequence: cover property(
        @(posedge clk) disable iff (!rst_n)
        empty ##[1:DEPTH] full ##[1:DEPTH] empty
    );
    
    cov_rapid_operations: cover property(
        @(posedge clk) disable iff (!rst_n)
        (wr_en || rd_en)[*10]
    );

endmodule

//==============================================================================
// Bind Statement (to be included in testbench or separate bind file)
//==============================================================================
/*
bind sync_fifo sync_fifo_assertions #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH),
    .ADDR_WIDTH(ADDR_WIDTH),
    .ALMOST_FULL_THRESHOLD(ALMOST_FULL_THRESHOLD),
    .ALMOST_EMPTY_THRESHOLD(ALMOST_EMPTY_THRESHOLD)
) u_assertions (
    .clk(clk),
    .rst_n(rst_n),
    .wr_en(wr_en),
    .rd_en(rd_en),
    .wr_data(wr_data),
    .rd_data(rd_data),
    .full(full),
    .empty(empty),
    .almost_full(almost_full),
    .almost_empty(almost_empty),
    .error(error),
    .count(count),
    .wr_ptr(wr_ptr),
    .rd_ptr(rd_ptr)
);
*/
```

This comprehensive SVA assertion module provides:

1. **Complete Property Coverage**: All 20 requirements are covered with dedicated properties
2. **Corner Case Handling**: Special properties for edge cases and boundary conditions
3. **FSM State Verification**: Properties to ensure state machine consistency
4. **Comprehensive Coverage**: Cover properties for all major scenarios, transitions, and corner cases
5. **Error Detection**: Detailed error messages for each requirement violation
6. **Parameterizable**: Works with different FIFO configurations
7. **Reset Handling**: Proper disable conditions and reset verification
8. **Timing Considerations**: Combinational and sequential property checks

The assertions can be easily integrated into any verification environment and provide thorough coverage of the FIFO design requirements.