//==============================================================================
// File: fifo_if.sv
// Description: SystemVerilog Interface for Synchronous FIFO
//==============================================================================

interface fifo_if #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
) (
    input logic clk,
    input logic rst_n
);

    //--------------------------------------------------------------------------
    // Interface Signals
    //--------------------------------------------------------------------------
    
    // Input signals (driven by testbench)
    logic                  wr_en;
    logic                  rd_en;
    logic [DATA_WIDTH-1:0] wr_data;
    
    // Output signals (driven by DUT)
    logic [DATA_WIDTH-1:0] rd_data;
    logic                  full;
    logic                  empty;
    logic                  almost_full;
    logic                  almost_empty;
    logic [ADDR_WIDTH:0]   count;

    //--------------------------------------------------------------------------
    // Clocking Blocks
    //--------------------------------------------------------------------------
    
    // Driver clocking block - inputs sampled before clock, outputs driven after
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

    // Monitor clocking block - all signals sampled
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

    //--------------------------------------------------------------------------
    // Modports
    //--------------------------------------------------------------------------
    
    // Driver modport - for UVM driver
    modport driver (
        clocking driver_cb,
        input clk,
        input rst_n
    );
    
    // Monitor modport - for UVM monitor
    modport monitor (
        clocking monitor_cb,
        input clk,
        input rst_n
    );
    
    // DUT modport - connects to design under test
    modport dut (
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

    //--------------------------------------------------------------------------
    // Helper Tasks for Direct Interface Access
    //--------------------------------------------------------------------------
    
    // Wait for specified number of clock cycles
    task automatic wait_clocks(int num_clocks);
        repeat(num_clocks) @(posedge clk);
    endtask

    // Wait for reset to complete
    task automatic wait_for_reset();
        @(posedge rst_n);
        @(posedge clk);
    endtask

    // Perform single write operation
    task automatic write_data(input logic [DATA_WIDTH-1:0] data);
        @(posedge clk);
        wr_en   <= 1'b1;
        wr_data <= data;
        @(posedge clk);
        wr_en   <= 1'b0;
    endtask

    // Perform single read operation
    task automatic read_data(output logic [DATA_WIDTH-1:0] data);
        @(posedge clk);
        rd_en <= 1'b1;
        @(posedge clk);
        rd_en <= 1'b0;
        data = rd_data;
    endtask

    // Perform simultaneous read and write
    task automatic read_write(
        input  logic [DATA_WIDTH-1:0] wdata,
        output logic [DATA_WIDTH-1:0] rdata
    );
        @(posedge clk);
        wr_en   <= 1'b1;
        rd_en   <= 1'b1;
        wr_data <= wdata;
        @(posedge clk);
        wr_en   <= 1'b0;
        rd_en   <= 1'b0;
        rdata = rd_data;
    endtask

    // Initialize interface signals
    task automatic init();
        wr_en   <= 1'b0;
        rd_en   <= 1'b0;
        wr_data <= '0;
    endtask

    //--------------------------------------------------------------------------
    // Utility Functions
    //--------------------------------------------------------------------------
    
    // Check if write is possible
    function automatic logic can_write();
        return (!full || rd_en);
    endfunction

    // Check if read is possible
    function automatic logic can_read();
        return (!empty || wr_en);
    endfunction

    // Get current FIFO level as percentage
    function automatic int get_fill_percentage();
        return (count * 100) / DEPTH;
    endfunction

endinterface : fifo_if

