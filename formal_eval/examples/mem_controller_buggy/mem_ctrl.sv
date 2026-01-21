// Memory Controller with BUG
// BUG: Write and Read can be acknowledged simultaneously (protocol violation)

`default_nettype none

module mem_ctrl (
    input  wire        clk,
    input  wire        rst_n,
    
    // Request interface
    input  wire        wr_req,
    input  wire        rd_req,
    input  wire [7:0]  addr,
    input  wire [7:0]  wr_data,
    output reg  [7:0]  rd_data,
    
    // Acknowledge signals
    output reg         wr_ack,
    output reg         rd_ack,
    
    // Status
    output wire        busy
);

    // Simple state machine
    localparam IDLE  = 2'b00;
    localparam WRITE = 2'b01;
    localparam READ  = 2'b10;
    
    reg [1:0] state;
    reg [7:0] mem [0:255];
    
    assign busy = (state != IDLE);
    
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            wr_ack <= 0;
            rd_ack <= 0;
            rd_data <= 0;
        end else begin
            // BUG: Acks are not mutually exclusive!
            // Both can be high at the same time
            wr_ack <= wr_req;  // BUG: Should check state!
            rd_ack <= rd_req;  // BUG: Should check state!
            
            case (state)
                IDLE: begin
                    if (wr_req) begin
                        state <= WRITE;
                        mem[addr] <= wr_data;
                    end else if (rd_req) begin
                        state <= READ;
                        rd_data <= mem[addr];
                    end
                end
                
                WRITE: begin
                    state <= IDLE;
                end
                
                READ: begin
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

`ifdef FORMAL
    //=========================================================================
    // FORMAL VERIFICATION - Should catch protocol bugs!
    //=========================================================================
    
    reg f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;
    
    // CRITICAL: Write and Read acks must be mutually exclusive
    // This assertion WILL FAIL!
    always @(*)
        assert(!(wr_ack && rd_ack));  // FAILS when both reqs come simultaneously
    
    // Ack should only happen when there was a request
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && wr_ack)
            assert($past(wr_req));
    
    always @(posedge clk)
        if (f_past_valid && $past(rst_n) && rd_ack)
            assert($past(rd_req));
    
    // State is valid
    always @(*)
        assert(state == IDLE || state == WRITE || state == READ);
    
    // After reset
    always @(posedge clk)
        if (f_past_valid && !$past(rst_n)) begin
            assert(state == IDLE);
            assert(!wr_ack && !rd_ack);
        end

    //=========================================================================
    // COVER POINTS
    //=========================================================================
    
    always @(posedge clk) cover(rst_n && wr_req && !rd_req);
    always @(posedge clk) cover(rst_n && rd_req && !wr_req);
    always @(posedge clk) cover(rst_n && wr_ack);
    always @(posedge clk) cover(rst_n && rd_ack);
`endif

endmodule


