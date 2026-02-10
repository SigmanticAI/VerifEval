interface sync_fifo_if #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 4
)(
    input logic clk,
    input logic rst_n
);

    // FIFO signals
    logic                    wr_en;
    logic [DATA_WIDTH-1:0]   wr_data;
    logic                    rd_en;
    logic [DATA_WIDTH-1:0]   rd_data;
    logic                    full;
    logic                    empty;
    logic                    almost_full;
    logic                    almost_empty;
    logic [ADDR_WIDTH:0]     count;
    logic                    error;

    // Clocking block for driver
    clocking driver_cb @(posedge clk);
        default input #1step output #1ns;
        output wr_en;
        output wr_data;
        output rd_en;
        input  rd_data;
        input  full;
        input  empty;
        input  almost_full;
        input  almost_empty;
        input  count;
        input  error;
    endclocking

    // Clocking block for monitor
    clocking monitor_cb @(posedge clk);
        default input #1step;
        input wr_en;
        input wr_data;
        input rd_en;
        input rd_data;
        input full;
        input empty;
        input almost_full;
        input almost_empty;
        input count;
        input error;
    endclocking

    // Modport for DUT
    modport dut (
        input  clk,
        input  rst_n,
        input  wr_en,
        input  wr_data,
        input  rd_en,
        output rd_data,
        output full,
        output empty,
        output almost_full,
        output almost_empty,
        output count,
        output error
    );

    // Modport for driver
    modport driver (
        input  clk,
        input  rst_n,
        clocking driver_cb
    );

    // Modport for monitor
    modport monitor (
        input  clk,
        input  rst_n,
        clocking monitor_cb
    );

    // Modport for testbench (direct access)
    modport tb (
        input  clk,
        input  rst_n,
        input  wr_en,
        input  wr_data,
        input  rd_en,
        input  rd_data,
        input  full,
        input  empty,
        input  almost_full,
        input  almost_empty,
        input  count,
        input  error
    );

endinterface
