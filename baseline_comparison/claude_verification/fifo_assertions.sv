//==============================================================================
// File: fifo_assertions.sv
// Description: SystemVerilog Assertions for Synchronous FIFO Verification
//==============================================================================

module fifo_assertions #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
) (
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
    input  logic [ADDR_WIDTH:0]   count
);

    //==========================================================================
    // Internal Signal Declarations
    //==========================================================================
    
    // Internal write/read enable (mirrors DUT logic)
    wire wr_en_int = wr_en && (!full || rd_en);
    wire rd_en_int = rd_en && (!empty || wr_en);
    
    // Previous cycle values for transition checking
    logic [ADDR_WIDTH:0] count_prev;
    logic                full_prev;
    logic                empty_prev;
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_prev <= '0;
            full_prev  <= 1'b0;
            empty_prev <= 1'b1;
        end else begin
            count_prev <= count;
            full_prev  <= full;
            empty_prev <= empty;
        end
    end

    //==========================================================================
    // Reset Assertions
    //==========================================================================
    
    // AST_RST_001: After reset, FIFO should be empty
    property p_reset_empty;
        @(posedge clk) !rst_n |-> ##1 empty;
    endproperty
    AST_RST_001: assert property (p_reset_empty)
        else $error("AST_RST_001 FAILED: FIFO not empty after reset");
    
    // AST_RST_002: After reset, count should be zero
    property p_reset_count;
        @(posedge clk) !rst_n |-> ##1 (count == 0);
    endproperty
    AST_RST_002: assert property (p_reset_count)
        else $error("AST_RST_002 FAILED: Count not zero after reset");
    
    // AST_RST_003: After reset, full should be deasserted
    property p_reset_not_full;
        @(posedge clk) !rst_n |-> ##1 !full;
    endproperty
    AST_RST_003: assert property (p_reset_not_full)
        else $error("AST_RST_003 FAILED: Full asserted after reset");
    
    // AST_RST_004: After reset, rd_data should be zero
    property p_reset_rd_data;
        @(posedge clk) !rst_n |-> ##1 (rd_data == '0);
    endproperty
    AST_RST_004: assert property (p_reset_rd_data)
        else $error("AST_RST_004 FAILED: rd_data not zero after reset");

    //==========================================================================
    // Count Assertions
    //==========================================================================
    
    // AST_CNT_001: Count should never exceed DEPTH
    property p_count_max;
        @(posedge clk) disable iff (!rst_n)
        count <= DEPTH;
    endproperty
    AST_CNT_001: assert property (p_count_max)
        else $error("AST_CNT_001 FAILED: Count %0d exceeds DEPTH %0d", count, DEPTH);
    
    // AST_CNT_002: Count increment on write only
    property p_count_increment;
        @(posedge clk) disable iff (!rst_n)
        (wr_en_int && !rd_en_int) |=> (count == $past(count) + 1);
    endproperty
    AST_CNT_002: assert property (p_count_increment)
        else $error("AST_CNT_002 FAILED: Count did not increment on write");
    
    // AST_CNT_003: Count decrement on read only
    property p_count_decrement;
        @(posedge clk) disable iff (!rst_n)
        (!wr_en_int && rd_en_int) |=> (count == $past(count) - 1);
    endproperty
    AST_CNT_003: assert property (p_count_decrement)
        else $error("AST_CNT_003 FAILED: Count did not decrement on read");
    
    // AST_CNT_004: Count unchanged on simultaneous read/write
    property p_count_stable_rw;
        @(posedge clk) disable iff (!rst_n)
        (wr_en_int && rd_en_int) |=> (count == $past(count));
    endproperty
    AST_CNT_004: assert property (p_count_stable_rw)
        else $error("AST_CNT_004 FAILED: Count changed on simultaneous R/W");
    
    // AST_CNT_005: Count unchanged when no operation
    property p_count_stable_noop;
        @(posedge clk) disable iff (!rst_n)
        (!wr_en_int && !rd_en_int) |=> (count == $past(count));
    endproperty
    AST_CNT_005: assert property (p_count_stable_noop)
        else $error("AST_CNT_005 FAILED: Count changed with no operation");

    //==========================================================================
    // Status Flag Assertions
    //==========================================================================
    
    // AST_FLG_001: Full flag accurate
    property p_full_accurate;
        @(posedge clk) disable iff (!rst_n)
        full == (count == DEPTH);
    endproperty
    AST_FLG_001: assert property (p_full_accurate)
        else $error("AST_FLG_001 FAILED: Full flag incorrect (full=%b, count=%0d)", full, count);
    
    // AST_FLG_002: Empty flag accurate
    property p_empty_accurate;
        @(posedge clk) disable iff (!rst_n)
        empty == (count == 0);
    endproperty
    AST_FLG_002: assert property (p_empty_accurate)
        else $error("AST_FLG_002 FAILED: Empty flag incorrect (empty=%b, count=%0d)", empty, count);
    
    // AST_FLG_003: Almost full flag accurate
    property p_almost_full_accurate;
        @(posedge clk) disable iff (!rst_n)
        almost_full == (count == DEPTH - 1);
    endproperty
    AST_FLG_003: assert property (p_almost_full_accurate)
        else $error("AST_FLG_003 FAILED: Almost full flag incorrect");
    
    // AST_FLG_004: Almost empty flag accurate
    property p_almost_empty_accurate;
        @(posedge clk) disable iff (!rst_n)
        almost_empty == (count == 1);
    endproperty
    AST_FLG_004: assert property (p_almost_empty_accurate)
        else $error("AST_FLG_004 FAILED: Almost empty flag incorrect");
    
    // AST_FLG_005: Full and empty mutually exclusive
    property p_full_empty_mutex;
        @(posedge clk) disable iff (!rst_n)
        !(full && empty);
    endproperty
    AST_FLG_005: assert property (p_full_empty_mutex)
        else $error("AST_FLG_005 FAILED: Full and empty both asserted");

    //==========================================================================
    // Write Operation Assertions
    //==========================================================================
    
    // AST_WR_001: No effective write when full without concurrent read
    property p_no_write_when_full;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && full && !rd_en) |=> (count == $past(count));
    endproperty
    AST_WR_001: assert property (p_no_write_when_full)
        else $error("AST_WR_001 FAILED: Write occurred when full without read");
    
    // AST_WR_002: Write succeeds when full with concurrent read
    property p_write_when_full_with_read;
        @(posedge clk) disable iff (!rst_n)
        (wr_en && full && rd_en) |-> wr_en_int;
    endproperty
    AST_WR_002: assert property (p_write_when_full_with_read)
        else $error("AST_WR_002 FAILED: Write blocked when full with concurrent read");

    //==========================================================================
    // Read Operation Assertions
    //==========================================================================
    
    // AST_RD_001: No effective read when empty without concurrent write
    property p_no_read_when_empty;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && empty && !wr_en) |=> (count == $past(count));
    endproperty
    AST_RD_001: assert property (p_no_read_when_empty)
        else $error("AST_RD_001 FAILED: Read occurred when empty without write");
    
    // AST_RD_002: Read succeeds when empty with concurrent write
    property p_read_when_empty_with_write;
        @(posedge clk) disable iff (!rst_n)
        (rd_en && empty && wr_en) |-> rd_en_int;
    endproperty
    AST_RD_002: assert property (p_read_when_empty_with_write)
        else $error("AST_RD_002 FAILED: Read blocked when empty with concurrent write");

    //==========================================================================
    // State Transition Assertions
    //==========================================================================
    
    // AST_TRN_001: Empty to not-empty requires write
    property p_empty_to_not_empty;
        @(posedge clk) disable iff (!rst_n)
        ($fell(empty)) |-> $past(wr_en_int);
    endproperty
    AST_TRN_001: assert property (p_empty_to_not_empty)
        else $error("AST_TRN_001 FAILED: Empty deasserted without write");
    
    // AST_TRN_002: Not-empty to empty requires read
    property p_not_empty_to_empty;
        @(posedge clk) disable iff (!rst_n)
        ($rose(empty)) |-> $past(rd_en_int);
    endproperty
    AST_TRN_002: assert property (p_not_empty_to_empty)
        else $error("AST_TRN_002 FAILED: Empty asserted without read");
    
    // AST_TRN_003: Full to not-full requires read
    property p_full_to_not_full;
        @(posedge clk) disable iff (!rst_n)
        ($fell(full)) |-> $past(rd_en_int);
    endproperty
    AST_TRN_003: assert property (p_full_to_not_full)
        else $error("AST_TRN_003 FAILED: Full deasserted without read");
    
    // AST_TRN_004: Not-full to full requires write
    property p_not_full_to_full;
        @(posedge clk) disable iff (!rst_n)
        ($rose(full)) |-> $past(wr_en_int);
    endproperty
    AST_TRN_004: assert property (p_not_full_to_full)
        else $error("AST_TRN_004 FAILED: Full asserted without write");

    //==========================================================================
    // Stability Assertions
    //==========================================================================
    
    // AST_STB_001: Count changes by at most 1 per cycle
    property p_count_change_max;
        @(posedge clk) disable iff (!rst_n)
        (count == $past(count)) || 
        (count == $past(count) + 1) || 
        (count == $past(count) - 1);
    endproperty
    AST_STB_001: assert property (p_count_change_max)
        else $error("AST_STB_001 FAILED: Count changed by more than 1");

    //==========================================================================
    // Cover Properties for Functional Coverage
    //==========================================================================
    
    // Cover simultaneous read and write
    COV_SIM_RW: cover property (
        @(posedge clk) disable iff (!rst_n)
        wr_en && rd_en && !full && !empty
    );
    
    // Cover write when full with concurrent read
    COV_WR_FULL_RD: cover property (
        @(posedge clk) disable iff (!rst_n)
        wr_en && rd_en && full
    );
    
    // Cover read when empty with concurrent write
    COV_RD_EMPTY_WR: cover property (
        @(posedge clk) disable iff (!rst_n)
        wr_en && rd_en && empty
    );
    
    // Cover FIFO becoming full
    COV_BECOME_FULL: cover property (
        @(posedge clk) disable iff (!rst_n)
        $rose(full)
    );
    
    // Cover FIFO becoming empty
    COV_BECOME_EMPTY: cover property (
        @(posedge clk) disable iff (!rst_n)
        $rose(empty)
    );
    
    // Cover almost_full transition
    COV_ALMOST_FULL: cover property (
        @(posedge clk) disable iff (!rst_n)
        $rose(almost_full)
    );
    
    // Cover almost_empty transition
    COV_ALMOST_EMPTY: cover property (
        @(posedge clk) disable iff (!rst_n)
        $rose(almost_empty)
    );
    
    // Cover full FIFO depth utilization
    COV_MAX_COUNT: cover property (
        @(posedge clk) disable iff (!rst_n)
        count == DEPTH
    );
    
    // Cover blocked write (full, no read)
    COV_BLOCKED_WR: cover property (
        @(posedge clk) disable iff (!rst_n)
        wr_en && full && !rd_en
    );
    
    // Cover blocked read (empty, no write)
    COV_BLOCKED_RD: cover property (
        @(posedge clk) disable iff (!rst_n)
        rd_en && empty && !wr_en
    );

    //==========================================================================
    // Assumption Properties (for formal verification)
    //==========================================================================
    
    // Assume reset is applied at start
    // ASM_RESET: assume property (@(posedge clk) $past(!rst_n, 1));

endmodule : fifo_assertions

