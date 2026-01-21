// Traffic Light Controller FSM with BUG
// BUG: Can transition from GREEN directly to RED (skipping YELLOW)!

`default_nettype none

module traffic_light (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sensor,    // Car sensor
    output reg  [1:0] state,
    output wire       red,
    output wire       yellow,
    output wire       green
);

    // States
    localparam RED    = 2'b00;
    localparam YELLOW = 2'b01;
    localparam GREEN  = 2'b10;
    
    // Timer
    reg [3:0] timer;
    
    // Output decode
    assign red    = (state == RED);
    assign yellow = (state == YELLOW);
    assign green  = (state == GREEN);
    
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= RED;
            timer <= 0;
        end else begin
            timer <= timer + 1;
            
            case (state)
                RED: begin
                    if (timer >= 10)
                        state <= GREEN;
                end
                
                GREEN: begin
                    // BUG: Goes directly to RED instead of YELLOW!
                    if (timer >= 8)
                        state <= RED;  // BUG! Should go to YELLOW first
                end
                
                YELLOW: begin
                    if (timer >= 3)
                        state <= RED;
                end
                
                default: state <= RED;
            endcase
            
            // Reset timer on state change
            if (state != $past(state))
                timer <= 0;
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - Should catch the transition bug!
    //=========================================================================
    
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // State must be valid
    always @(*)
        assert(state == RED || state == YELLOW || state == GREEN);
    
    // Only one light at a time
    always @(*)
        assert($onehot({red, yellow, green}));
    
    // CRITICAL: GREEN must transition to YELLOW, not directly to RED
    // This assertion WILL FAIL!
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(state) == GREEN && state != GREEN)
            assert(state == YELLOW);  // FAILS: Goes to RED instead
    
    // YELLOW must transition to RED
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && $past(state) == YELLOW && state != YELLOW)
            assert(state == RED);
    
    // After reset, should be RED
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n))
            assert(state == RED);

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    // Cover all states
    always @(posedge clk) cover(rst_n && state == RED);
    always @(posedge clk) cover(rst_n && state == GREEN);
    always @(posedge clk) cover(rst_n && state == YELLOW);
`endif

endmodule


