// FIFO Formal Assertions Module
// Multi-file formal verification example - Assertions file
// Bound to FIFO via top-level instantiation

`default_nettype none

module fifo_assertions #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 4,
    parameter ADDR_WIDTH = $clog2(DEPTH)
)(
    input wire                  clk,
    input wire                  rst_n,
    input wire                  wr_en,
    input wire [DATA_WIDTH-1:0] wr_data,
    input wire                  rd_en,
    input wire [DATA_WIDTH-1:0] rd_data,
    input wire                  full,
    input wire                  empty,
    input wire [ADDR_WIDTH:0]   count
);

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION (Yosys-compatible)
    //=========================================================================
    
    // Track valid past
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // Assertion 1: Empty flag consistency
    always @(*)
        assert(empty == (count == 0));
    
    // Assertion 2: Full flag consistency  
    always @(*)
        assert(full == (count == DEPTH));
    
    // Assertion 3: Count never exceeds depth
    always @(*)
        assert(count <= DEPTH);
    
    // Assertion 4: After reset, FIFO should be empty
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n))
            assert(empty && !full && count == 0);
    
    // Assertion 5: Count increments on write (when not full and not reading)
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(wr_en) && !$past(full) && !$past(rd_en))
            assert(count == $past(count) + 1);
    
    // Assertion 6: Count decrements on read (when not empty and not writing)
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(rd_en) && !$past(empty) && !$past(wr_en))
            assert(count == $past(count) - 1);
    
    // Assertion 7: Count stable when no operation
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && !$past(wr_en) && !$past(rd_en))
            assert(count == $past(count));

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover: FIFO becomes full
    always @(posedge clk)
        cover(rst_n && full);
    
    // Cover: FIFO becomes empty after being non-empty
    always @(posedge clk)
        cover(rst_n && f_past_valid && empty && !$past(empty));
    
    // Cover: Simultaneous read and write
    always @(posedge clk)
        cover(rst_n && wr_en && rd_en && !full && !empty);
`endif

endmodule
