// Priority Encoder - CORRECT Implementation
// Outputs the index of the highest priority active input

`default_nettype none

module priority_encoder #(
    parameter WIDTH = 8,
    parameter IDX_WIDTH = $clog2(WIDTH)
)(
    input  wire [WIDTH-1:0]     req,
    output wire [IDX_WIDTH-1:0] idx,
    output wire                 valid
);

    reg [IDX_WIDTH-1:0] idx_reg;
    reg                 valid_reg;
    
    integer i;
    
    always @(*) begin
        idx_reg = 0;
        valid_reg = 0;
        
        // Priority: higher index = higher priority
        for (i = 0; i < WIDTH; i = i + 1) begin
            if (req[i]) begin
                idx_reg = i[IDX_WIDTH-1:0];
                valid_reg = 1;
            end
        end
    end
    
    assign idx = idx_reg;
    assign valid = valid_reg;

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - All should pass
    //=========================================================================
    
    // Valid is high if any request
    always @(*)
        assert(valid == |req);
    
    // Index is bounded
    always @(*)
        assert(idx < WIDTH);
    
    // If valid, the indexed bit must be set
    always @(*)
        if (valid)
            assert(req[idx]);
    
    // If valid, no higher priority bit is set
    // (higher index = higher priority)
    genvar g;
    generate
        for (g = 0; g < WIDTH-1; g = g + 1) begin : check_priority
            always @(*)
                if (valid && idx == g)
                    assert(req[WIDTH-1:g+1] == 0);
        end
    endgenerate
    
    // If not valid, index should be 0
    always @(*)
        if (!valid)
            assert(idx == 0);

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover: Single request
    always @(*) cover(req != 0 && $onehot(req));
    
    // Cover: Multiple requests
    always @(*) cover($countones(req) > 1);
    
    // Cover: All requests active
    always @(*) cover(req == {WIDTH{1'b1}});
`endif

endmodule


