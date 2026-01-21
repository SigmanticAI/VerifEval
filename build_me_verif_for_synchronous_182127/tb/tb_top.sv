//==============================================================================
// File: tb_top.sv
// Description: UVM Testbench Top Module for Synchronous FIFO
// This module instantiates the DUT, generates clock and reset, creates
// interfaces, and starts the UVM test environment
//==============================================================================

`timescale 1ns/1ps

module tb_top;

  //============================================================================
  // Parameters
  //============================================================================
  parameter DATA_WIDTH = 8;
  parameter DEPTH = 16;
  parameter CLK_PERIOD = 10;
  
  //============================================================================
  // Clock and Reset Signals
  //============================================================================
  logic clk;
  logic rst_n;
  
  //============================================================================
  // Interface Instantiation
  //============================================================================
  fifo_if #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH)
  ) vif (
    .clk(clk),
    .rst_n(rst_n)
  );
  
  //============================================================================
  // DUT Instantiation
  //============================================================================
  sync_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH)
  ) dut (
    .clk(vif.clk),
    .rst_n(vif.rst_n),
    .wr_en(vif.wr_en),
    .rd_en(vif.rd_en),
    .wr_data(vif.wr_data),
    .rd_data(vif.rd_data),
    .full(vif.full),
    .empty(vif.empty),
    .almost_full(vif.almost_full),
    .almost_empty(vif.almost_empty),
    .count(vif.count)
  );
  
  //============================================================================
  // Clock Generation
  //============================================================================
  initial begin
    clk = 0;
    forever #(CLK_PERIOD/2) clk = ~clk;
  end
  
  //============================================================================
  // Reset Generation
  //============================================================================
  initial begin
    rst_n = 0;
    repeat(5) @(posedge clk);
    rst_n = 1;
  end
  
  //============================================================================
  // UVM Configuration and Test Execution
  //============================================================================
  initial begin
    // Set the interface in the configuration database
    uvm_config_db#(virtual fifo_if#(DATA_WIDTH, DEPTH))::set(
      null, 
      "uvm_test_top", 
      "vif", 
      vif
    );
    
    // Set parameters in configuration database
    uvm_config_db#(int)::set(null, "uvm_test_top", "DATA_WIDTH", DATA_WIDTH);
    uvm_config_db#(int)::set(null, "uvm_test_top", "DEPTH", DEPTH);
    
    // Enable waveform dumping
    `ifdef VCS
      $vcdpluson;
    `elsif QUESTA
      $wlfdumpvars(0, tb_top);
    `else
      $dumpfile("fifo_tb.vcd");
      $dumpvars(0, tb_top);
    `endif
    
    // Run the test
    run_test();
  end
  
  //============================================================================
  // Timeout Watchdog
  //============================================================================
  initial begin
    #100ms;
    $display("ERROR: Simulation timeout at %0t", $time);
    $finish;
  end
  
  //============================================================================
  // Assertions Binding
  //============================================================================
  bind sync_fifo fifo_assertions #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH)
  ) fifo_assert_inst (
    .clk(clk),
    .rst_n(rst_n),
    .wr_en(wr_en),
    .rd_en(rd_en),
    .wr_data(wr_data),
    .rd_data(rd_data),
    .full(full),
    .empty(empty),
    .almost_full(almost_full),
    .almost_empty(almost_empty),
    .count(count)
  );
  
  //============================================================================
  // Coverage Binding
  //============================================================================
  bind sync_fifo fifo_coverage #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH)
  ) fifo_cov_inst (
    .clk(clk),
    .rst_n(rst_n),
    .wr_en(wr_en),
    .rd_en(rd_en),
    .wr_data(wr_data),
    .rd_data(rd_data),
    .full(full),
    .empty(empty),
    .almost_full(almost_full),
    .almost_empty(almost_empty),
    .count(count)
  );
  
  //============================================================================
  // Simulation Control and Reporting
  //============================================================================
  initial begin
    $display("========================================");
    $display("  FIFO UVM Testbench");
    $display("  DATA_WIDTH = %0d", DATA_WIDTH);
    $display("  DEPTH = %0d", DEPTH);
    $display("  CLK_PERIOD = %0d ns", CLK_PERIOD);
    $display("========================================");
  end
  
  final begin
    $display("========================================");
    $display("  Simulation Complete at %0t", $time);
    $display("========================================");
  end
  
  //============================================================================
  // Signal Monitoring for Debug
  //============================================================================
  `ifdef DEBUG
  always @(posedge clk) begin
    if (vif.wr_en && !vif.full) begin
      $display("[%0t] WRITE: data=0x%0h, count=%0d", $time, vif.wr_data, vif.count);
    end
    if (vif.rd_en && !vif.empty) begin
      $display("[%0t] READ: data=0x%0h, count=%0d", $time, vif.rd_data, vif.count);
    end
    if (vif.full) begin
      $display("[%0t] FIFO FULL", $time);
    end
    if (vif.empty) begin
      $display("[%0t] FIFO EMPTY", $time);
    end
  end
  `endif
  
  //============================================================================
  // Protocol Checks
  //============================================================================
  property p_no_x_on_outputs;
    @(posedge clk) disable iff (!rst_n)
    !$isunknown({vif.rd_data, vif.full, vif.empty, vif.almost_full, vif.almost_empty, vif.count});
  endproperty
  
  assert_no_x_on_outputs: assert property(p_no_x_on_outputs)
    else $error("[%0t] X detected on outputs", $time);
  
  property p_reset_behavior;
    @(posedge clk)
    !rst_n |=> (vif.empty && !vif.full && vif.count == 0);
  endproperty
  
  assert_reset_behavior: assert property(p_reset_behavior)
    else $error("[%0t] Reset behavior violation", $time);
  
  //============================================================================
  // End of Module
  //============================================================================
endmodule

//==============================================================================
// Interface Definition
//==============================================================================
interface fifo_if #(
  parameter DATA_WIDTH = 8,
  parameter DEPTH = 16
)(
  input logic clk,
  input logic rst_n
);

  // Signals
  logic wr_en;
  logic rd_en;
  logic [DATA_WIDTH-1:0] wr_data;
  logic [DATA_WIDTH-1:0] rd_data;
  logic full;
  logic empty;
  logic almost_full;
  logic almost_empty;
  logic [$clog2(DEPTH+1)-1:0] count;
  
  // Clocking blocks for driver
  clocking driver_cb @(posedge clk);
    default input #1step output #1ns;
    output wr_en;
    output rd_en;
    output wr_data;
    input rd_data;
    input full;
    input empty;
    input almost_full;
    input almost_empty;
    input count;
  endclocking
  
  // Clocking block for monitor
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
    input clk,
    input rst_n,
    input wr_en,
    input rd_en,
    input wr_data,
    output rd_data,
    output full,
    output empty,
    output almost_full,
    output almost_empty,
    output count
  );

endinterface