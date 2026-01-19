// Synchronous FIFO DUT
// Multi-file verification example

module fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16
)(
    input  wire                  clk,
    input  wire                  rst_n,
    
    // Write interface
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    
    // Read interface
    input  wire                  rd_en,
    output reg  [DATA_WIDTH-1:0] rd_data,
    
    // Status flags
    output wire                  full,
    output wire                  empty,
    output wire [$clog2(DEPTH):0] count
);

    // Memory and pointers
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    reg [$clog2(DEPTH)-1:0] wr_ptr;
    reg [$clog2(DEPTH)-1:0] rd_ptr;
    reg [$clog2(DEPTH):0] fifo_count;
    
    // Status flags
    assign full = (fifo_count == DEPTH);
    assign empty = (fifo_count == 0);
    assign count = fifo_count;
    
    // Write logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
        end else if (wr_en && !full) begin
            mem[wr_ptr] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end
    
    // Read logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= 0;
            rd_data <= 0;
        end else if (rd_en && !empty) begin
            rd_data <= mem[rd_ptr];
            rd_ptr <= rd_ptr + 1;
        end
    end
    
    // Count logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fifo_count <= 0;
        end else begin
            case ({wr_en && !full, rd_en && !empty})
                2'b10: fifo_count <= fifo_count + 1;
                2'b01: fifo_count <= fifo_count - 1;
                default: fifo_count <= fifo_count;
            endcase
        end
    end

endmodule

