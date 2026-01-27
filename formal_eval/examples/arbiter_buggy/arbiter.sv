// Round-Robin Arbiter with BUG
// BUG: Grant can be given to multiple requestors simultaneously!

`default_nettype none

module arbiter #(
    parameter NUM_REQ = 4
)(
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NUM_REQ-1:0]   req,
    output reg  [NUM_REQ-1:0]   grant
);

    reg [$clog2(NUM_REQ)-1:0] last_grant;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            grant <= 0;
            last_grant <= 0;
        end else begin
            // BUG: Should only grant to ONE requestor!
            // This buggy code grants to ALL active requestors
            grant <= req;  // BUG! Should be one-hot grant
            
            if (|grant)
                last_grant <= last_grant + 1;
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - Should catch the mutual exclusion bug!
    //=========================================================================
    
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // CRITICAL: Grant must be one-hot or zero (mutual exclusion)
    // This assertion WILL FAIL because grant can have multiple bits set!
    always @(*)
        assert(grant == 0 || $onehot(grant));
    
    // Grant should only go to active requestors
    always @(*)
        assert((grant & ~req) == 0);
    
    // After reset, no grants
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n))
            assert(grant == 0);

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover: Multiple simultaneous requests
    always @(posedge clk)
        cover(rst_n && $countones(req) > 1);
    
    // Cover: Grant issued
    always @(posedge clk)
        cover(rst_n && |grant);
`endif

endmodule




