// Simple Counter with Formal Assertions
// Single-file formal verification example
// Uses Yosys-compatible assertion syntax

`default_nettype none

module counter #(
    parameter WIDTH = 4,
    parameter MAX_COUNT = 15
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,
    input  wire             load,
    input  wire [WIDTH-1:0] load_value,
    output reg  [WIDTH-1:0] count,
    output wire             overflow,
    output wire             at_max
);

    // Internal signals
    wire [WIDTH-1:0] next_count;
    reg              overflow_reg;
    
    // Combinational next state
    assign next_count = load ? load_value :
                        (enable && count < MAX_COUNT) ? count + 1 :
                        count;
    
    // Status flags
    assign at_max = (count == MAX_COUNT);
    assign overflow = overflow_reg;
    
    // Sequential logic
    always @(posedge clk) begin
        if (!rst_n) begin
            count <= 0;
            overflow_reg <= 1'b0;
        end else begin
            count <= next_count;
            overflow_reg <= enable && (count == MAX_COUNT);
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION (Yosys-compatible)
    //=========================================================================
    
    // Track valid past
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // Assertion 1: Count should never exceed MAX_COUNT
    always @(*)
        assert(count <= MAX_COUNT);
    
    // Assertion 2: at_max flag is correct
    always @(*)
        assert(at_max == (count == MAX_COUNT));
    
    // Assertion 3: After reset, count should be zero
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n))
            assert(count == 0);
    
    // Assertion 4: If not enabled and not loading, count stays same
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && !$past(enable) && !$past(load))
            assert(count == $past(count));
    
    // Assertion 5: Load takes priority over enable
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(load))
            assert(count == $past(load_value));
    
    // Assertion 6: Count increments when enabled and not at max
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(enable) && !$past(load) && $past(count) < MAX_COUNT)
            assert(count == $past(count) + 1);

    // Assertion 7: Overflow only when at max and enabled
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && overflow)
            assert($past(count) == MAX_COUNT && $past(enable));

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover: Reach maximum count
    always @(posedge clk)
        cover(rst_n && count == MAX_COUNT);
    
    // Cover: Overflow occurs
    always @(posedge clk)
        cover(rst_n && overflow);
    
    // Cover: Load while enabled
    always @(posedge clk)
        cover(rst_n && enable && load);
`endif

endmodule
