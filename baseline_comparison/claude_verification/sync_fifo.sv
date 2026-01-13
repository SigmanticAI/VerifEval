//==============================================================================
// File: sync_fifo.sv
// Description: Synchronous FIFO with configurable data width and depth
//==============================================================================

module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  wr_en,
    input  wire                  rd_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    output reg  [DATA_WIDTH-1:0] rd_data,
    output wire                  full,
    output wire                  empty,
    output wire                  almost_full,
    output wire                  almost_empty,
    output wire [ADDR_WIDTH:0]   count
);
    
    //--------------------------------------------------------------------------
    // Internal Storage
    //--------------------------------------------------------------------------
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [ADDR_WIDTH-1:0] wr_ptr;
    reg [ADDR_WIDTH-1:0] rd_ptr;
    reg [ADDR_WIDTH:0] count_reg;
    
    //--------------------------------------------------------------------------
    // Internal Write/Read Enable Signals
    //--------------------------------------------------------------------------
    // Write allowed when not full, OR when full but simultaneous read occurs
    wire wr_en_int = wr_en && (!full || rd_en);
    // Read allowed when not empty, OR when empty but simultaneous write occurs
    wire rd_en_int = rd_en && (!empty || wr_en);
    
    //--------------------------------------------------------------------------
    // Status Flag Generation
    //--------------------------------------------------------------------------
    assign full         = (count_reg == DEPTH);
    assign empty        = (count_reg == 0);
    assign almost_full  = (count_reg == DEPTH - 1);
    assign almost_empty = (count_reg == 1);
    assign count        = count_reg;
    
    //--------------------------------------------------------------------------
    // Write Logic
    //--------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
        end else if (wr_en_int) begin
            mem[wr_ptr] <= wr_data;
            wr_ptr <= (wr_ptr == DEPTH-1) ? 0 : wr_ptr + 1;
        end
    end
    
    //--------------------------------------------------------------------------
    // Read Logic
    //--------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= 0;
            rd_data <= 0;
        end else if (rd_en_int) begin
            rd_data <= mem[rd_ptr];
            rd_ptr <= (rd_ptr == DEPTH-1) ? 0 : rd_ptr + 1;
        end
    end
    
    //--------------------------------------------------------------------------
    // Count Management
    //--------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_reg <= 0;
        end else begin
            case ({wr_en_int, rd_en_int})
                2'b10:   count_reg <= count_reg + 1;  // Write only
                2'b01:   count_reg <= count_reg - 1;  // Read only
                default: count_reg <= count_reg;      // No change (both or neither)
            endcase
        end
    end

endmodule

