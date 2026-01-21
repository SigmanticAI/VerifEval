// FIFO Top-level with Assertions Bound
// Multi-file formal verification example - Top file

`default_nettype none

module fifo_top #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 4
)(
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       wr_en,
    input  wire [DATA_WIDTH-1:0]      wr_data,
    input  wire                       rd_en,
    output wire [DATA_WIDTH-1:0]      rd_data,
    output wire                       full,
    output wire                       empty,
    output wire [$clog2(DEPTH):0]     count
);

    // Instantiate FIFO
    fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH)
    ) u_fifo (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .wr_data(wr_data),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .full(full),
        .empty(empty),
        .count(count)
    );
    
    // Bind assertions
    fifo_assertions #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH)
    ) u_assertions (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .wr_data(wr_data),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .full(full),
        .empty(empty),
        .count(count)
    );

endmodule
