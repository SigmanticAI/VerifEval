// Synchronous FIFO - Corrected Implementation
// Based on SystemVerilog Assertions Handbook Specification (fifo_req_001)
// Parameterized depth and data width
//
// Corrections from original design.sv:
//   1. Fixed almost_full threshold (>= 3/4 of depth, not == DEPTH-1)
//   2. Fixed almost_empty threshold (<= 1/4 of depth, not == 1)
//   3. Made rd_data combinational for same-cycle read (per spec 5.1.2.2)
//   4. Added error flag for overflow/underflow detection (per spec 5.1.6)

module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    
    // Write interface (spec: push, data_in)
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    
    // Read interface (spec: pop, data_out)
    input  wire                  rd_en,
    output wire [DATA_WIDTH-1:0] rd_data,      // Combinational output per spec 5.1.2.2
    
    // Status flags
    output wire                  full,
    output wire                  empty,
    output wire                  almost_full,
    output wire                  almost_empty,
    output wire [ADDR_WIDTH:0]   count,
    
    // Error flag (per spec 5.1.6) - asserted on overflow or underflow
    output reg                   error
);

    //==========================================================================
    // Parameters for thresholds per spec 8.1
    // Spec: FULL = 2^BIT_DEPTH - 1, ALMOST_FULL = 3*FULL/4, ALMOST_EMPTY = FULL/4
    //==========================================================================
    localparam FULL_LEVEL = DEPTH - 1;                              // Per spec: 2^BIT_DEPTH - 1 = 15
    localparam ALMOST_FULL_THRESHOLD = (3 * FULL_LEVEL) / 4;        // 3*15/4 = 11
    localparam ALMOST_EMPTY_THRESHOLD = FULL_LEVEL / 4;             // 15/4 = 3

    //==========================================================================
    // Internal memory and pointers
    //==========================================================================
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    
    reg [ADDR_WIDTH-1:0] wr_ptr;
    reg [ADDR_WIDTH-1:0] rd_ptr;
    reg [ADDR_WIDTH:0]   count_reg;
    
    //==========================================================================
    // Internal control signals
    //==========================================================================
    wire wr_en_int;
    wire rd_en_int;
    wire overflow_cond;
    wire underflow_cond;
    
    // Determine actual operations based on flags
    // Per spec: simultaneous push/pop when full allows the operation
    assign wr_en_int = wr_en && (!full || rd_en);
    assign rd_en_int = rd_en && (!empty || wr_en);
    
    // Error conditions per spec 5.1.2.1 and 5.1.2.2:
    // - Overflow: push with no pop on a full FIFO
    // - Underflow: pop on an empty FIFO (without simultaneous push)
    assign overflow_cond  = wr_en && full && !rd_en;
    assign underflow_cond = rd_en && empty && !wr_en;

    //==========================================================================
    // Status flags per spec 5.1.3
    //==========================================================================
    
    // Per spec 5.1.3.1: Full when FIFO reaches maximum depth
    assign full = (count_reg == DEPTH);
    
    // Per spec 5.1.3.3: Empty when no valid data
    assign empty = (count_reg == 0);
    
    // Per spec 5.1.3.2: Almost full when count >= 3/4 of depth
    // Spec sequence: qAlmost_full -> dataQsize >= ALMOST_FULL
    assign almost_full = (count_reg >= ALMOST_FULL_THRESHOLD);
    
    // Per spec 5.1.3.4: Almost empty when count <= 1/4 of depth
    // Spec sequence: qAlmost_empty -> dataQsize <= ALMOST_EMPTY
    assign almost_empty = (count_reg <= ALMOST_EMPTY_THRESHOLD);
    
    // Count output
    assign count = count_reg;

    //==========================================================================
    // Read data - COMBINATIONAL per spec 5.1.2.2
    // "The data_out shall be asserted in the same cycle of pop control"
    //==========================================================================
    assign rd_data = mem[rd_ptr];

    //==========================================================================
    // Write logic per spec 5.1.1.1
    // "When push is active, data_in shall be stored into the FIFO buffer 
    //  at the next clock cycle"
    //==========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= '0;
        end else if (wr_en_int) begin
            mem[wr_ptr] <= wr_data;
            wr_ptr <= (wr_ptr == DEPTH-1) ? '0 : wr_ptr + 1;
        end
    end

    //==========================================================================
    // Read pointer logic
    // Note: rd_data is combinational, only the pointer updates on clock
    //==========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= '0;
        end else if (rd_en_int) begin
            rd_ptr <= (rd_ptr == DEPTH-1) ? '0 : rd_ptr + 1;
        end
    end

    //==========================================================================
    // Count logic
    //==========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_reg <= '0;
        end else begin
            case ({wr_en_int, rd_en_int})
                2'b10:   count_reg <= count_reg + 1;  // Write only
                2'b01:   count_reg <= count_reg - 1;  // Read only
                default: count_reg <= count_reg;      // Both or neither
            endcase
        end
    end

    //==========================================================================
    // Error flag per spec 5.1.6
    // "When either an overflow (push on full) or underflow (pop on empty) 
    //  error has occurred, the error flag shall be asserted"
    // Property: p_error_flag -> q_push_error or q_pop_error |=> error
    // Note: |=> means error asserts in the NEXT cycle after error condition
    //==========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            error <= 1'b0;
        end else if (overflow_cond || underflow_cond) begin
            error <= 1'b1;
        end
        // Note: Error flag stays asserted once set (sticky)
        // Could add clear mechanism if needed
    end

    //==========================================================================
    // Assertions for self-checking (synthesis ignored, simulation only)
    //==========================================================================
    // synthesis translate_off
    
    // Check that full and empty are never both asserted
    always @(posedge clk) begin
        if (rst_n && full && empty) begin
            $error("ASSERTION FAILED: full and empty both asserted");
        end
    end
    
    // Check count never exceeds DEPTH
    always @(posedge clk) begin
        if (rst_n && count_reg > DEPTH) begin
            $error("ASSERTION FAILED: count exceeds DEPTH");
        end
    end
    
    // Verify reset behavior per spec 5.1.4
    // "Reset shall result in: !almost_empty && !full && !almost_full && empty"
    // Note: With ALMOST_EMPTY_THRESHOLD=3, almost_empty will be TRUE at count=0
    // This appears to be a spec inconsistency - at count=0, almost_empty should be true
    
    // synthesis translate_on

endmodule

//==============================================================================
// Summary of changes from original design.sv:
//
// 1. ALMOST_FULL threshold:
//    OLD: (count_reg == DEPTH - 1)     -> triggers only at 15
//    NEW: (count_reg >= ALMOST_FULL_THRESHOLD) -> triggers at >= 11
//
// 2. ALMOST_EMPTY threshold:
//    OLD: (count_reg == 1)             -> triggers only at 1  
//    NEW: (count_reg <= ALMOST_EMPTY_THRESHOLD) -> triggers at <= 3
//
// 3. Read data timing:
//    OLD: Registered (rd_data <= mem[rd_ptr])  -> 1 cycle latency
//    NEW: Combinational (assign rd_data = mem[rd_ptr]) -> 0 cycle latency
//
// 4. Error flag:
//    OLD: Not present
//    NEW: Added per spec section 5.1.6, asserts on overflow/underflow
//
// 5. Signal naming kept consistent with original for compatibility
//    (wr_en/rd_en instead of push/pop, wr_data/rd_data instead of data_in/data_out)
//==============================================================================

