interface fifo_if #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH)
) (
    input logic clk,
    input logic rst_n
);

    // DUT signals
    logic                  wr_en;
    logic                  rd_en;
    logic [DATA_WIDTH-1:0] wr_data;
    logic [DATA_WIDTH-1:0] rd_data;
    logic                  full;
    logic                  empty;
    logic                  almost_full;
    logic                  almost_empty;
    logic [ADDR_WIDTH:0]   count;

    // Clocking blocks
    clocking driver_cb @(posedge clk);
        default input #1step output #1ns;
        output wr_en;
        output rd_en;
        output wr_data;
        input  rd_data;
        input  full;
        input  empty;
        input  almost_full;
        input  almost_empty;
        input  count;
    endclocking

    clocking monitor_cb @(posedge clk);
        default input #1step;
        input wr_en;
        input rd_en;
        input wr_data;
        input rd_data;
        input full;
        input empty;
        input almost_full;
        input almost_empty;
        input count;
    endclocking

    // Modports
    modport driver_mp (
        clocking driver_cb,
        input clk,
        input rst_n
    );

    modport monitor_mp (
        clocking monitor_cb,
        input clk,
        input rst_n
    );

    modport dut_mp (
        input  clk,
        input  rst_n,
        input  wr_en,
        input  rd_en,
        input  wr_data,
        output rd_data,
        output full,
        output empty,
        output almost_full,
        output almost_empty,
        output count
    );

    modport tb_mp (
        input clk,
        input rst_n,
        input wr_en,
        input rd_en,
        input wr_data,
        input rd_data,
        input full,
        input empty,
        input almost_full,
        input almost_empty,
        input count
    );

    // Assertions for protocol checking
    property no_write_when_full;
        @(posedge clk) disable iff (!rst_n)
        (full && !rd_en) |-> !wr_en;
    endproperty

    property no_read_when_empty;
        @(posedge clk) disable iff (!rst_n)
        (empty && !wr_en) |-> !rd_en;
    endproperty

    property count_bounds;
        @(posedge clk) disable iff (!rst_n)
        count <= DEPTH;
    endproperty

    property full_flag_check;
        @(posedge clk) disable iff (!rst_n)
        full == (count == DEPTH);
    endproperty

    property empty_flag_check;
        @(posedge clk) disable iff (!rst_n)
        empty == (count == 0);
    endproperty

    property almost_full_flag_check;
        @(posedge clk) disable iff (!rst_n)
        almost_full == (count == DEPTH - 1);
    endproperty

    property almost_empty_flag_check;
        @(posedge clk) disable iff (!rst_n)
        almost_empty == (count == 1);
    endproperty

    assert property (no_write_when_full) else $error("Write attempted when FIFO is full");
    assert property (no_read_when_empty) else $error("Read attempted when FIFO is empty");
    assert property (count_bounds) else $error("Count exceeds FIFO depth");
    assert property (full_flag_check) else $error("Full flag mismatch");
    assert property (empty_flag_check) else $error("Empty flag mismatch");
    assert property (almost_full_flag_check) else $error("Almost full flag mismatch");
    assert property (almost_empty_flag_check) else $error("Almost empty flag mismatch");

endinterface