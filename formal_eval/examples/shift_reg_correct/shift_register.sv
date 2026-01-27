// Shift Register - CORRECT Implementation
// This should pass all formal assertions

`default_nettype none

module shift_register #(
    parameter WIDTH = 8
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             shift_en,
    input  wire             load,
    input  wire [WIDTH-1:0] data_in,
    input  wire             serial_in,
    output wire [WIDTH-1:0] data_out,
    output wire             serial_out
);

    reg [WIDTH-1:0] shift_reg;
    
    assign data_out = shift_reg;
    assign serial_out = shift_reg[WIDTH-1];
    
    always @(posedge clk) begin
        if (!rst_n) begin
            shift_reg <= 0;
        end else if (load) begin
            shift_reg <= data_in;
        end else if (shift_en) begin
            shift_reg <= {shift_reg[WIDTH-2:0], serial_in};
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - All should pass
    //=========================================================================
    
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // Output always reflects register
    always @(*)
        assert(data_out == shift_reg);
    
    // Serial out is MSB
    always @(*)
        assert(serial_out == shift_reg[WIDTH-1]);
    
    // After reset, register is zero
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n))
            assert(shift_reg == 0);
    
    // Load overwrites entire register
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(load))
            assert(shift_reg == $past(data_in));
    
    // Shift behavior when enabled (and not loading)
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(shift_en) && !$past(load))
            assert(shift_reg == {$past(shift_reg[WIDTH-2:0]), $past(serial_in)});
    
    // Stable when not shifting or loading
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && !$past(shift_en) && !$past(load))
            assert(shift_reg == $past(shift_reg));

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover: Load data
    always @(posedge clk)
        cover(rst_n && load && data_in != 0);
    
    // Cover: Shift operation
    always @(posedge clk)
        cover(rst_n && shift_en && !load);
    
    // Cover: Serial out goes high
    always @(posedge clk)
        cover(rst_n && serial_out);
`endif

endmodule




