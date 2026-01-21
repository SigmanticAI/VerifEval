// Buggy Counter - For testing failure detection
// Contains an obviously false assertion

`default_nettype none

module counter_buggy #(
    parameter WIDTH = 4
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,
    output reg  [WIDTH-1:0] count
);

    always @(posedge clk) begin
        if (!rst_n) begin
            count <= 0;
        end else if (enable) begin
            count <= count + 1;
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - Will detect the bug!
    //=========================================================================
    
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // This assertion is obviously FALSE - count WILL change
    // This should be detected as a failure
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(enable))
            assert(count == $past(count));  // WRONG: count should have incremented!
    
    // This is correct
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(enable))
            assert(count == $past(count) + 1);  // Correct assertion
`endif

endmodule
