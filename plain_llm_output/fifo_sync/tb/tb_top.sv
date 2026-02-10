`timescale 1ns/1ps

module tb_top;
  
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  
  // Parameters
  parameter DATA_WIDTH = 8;
  parameter DEPTH = 16;
  parameter ADDR_WIDTH = $clog2(DEPTH);
  
  // Clock and reset signals
  logic clk;
  logic rst_n;
  
  // Interface instantiation
  fifo_interface #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(ADDR_WIDTH)
  ) fifo_if (
    .clk(clk),
    .rst_n(rst_n)
  );
  
  // DUT instantiation
  sync_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH),
    .ADDR_WIDTH(ADDR_WIDTH)
  ) dut (
    .clk(fifo_if.clk),
    .rst_n(fifo_if.rst_n),
    .wr_en(fifo_if.wr_en),
    .rd_en(fifo_if.rd_en),
    .data_in(fifo_if.data_in),
    .data_out(fifo_if.data_out),
    .full(fifo_if.full),
    .empty(fifo_if.empty),
    .count(fifo_if.count)
  );
  
  // Clock generation
  initial begin
    clk = 0;
    forever #5 clk = ~clk; // 100MHz clock
  end
  
  // Reset generation
  initial begin
    rst_n = 0;
    repeat(5) @(posedge clk);
    rst_n = 1;
  end
  
  // UVM testbench setup
  initial begin
    // Set interface in config_db
    uvm_config_db#(virtual fifo_interface)::set(
      null, 
      "uvm_test_top.*", 
      "fifo_if", 
      fifo_if
    );
    
    // Set test parameters in config_db
    uvm_config_db#(int)::set(
      null,
      "uvm_test_top.*",
      "DATA_WIDTH",
      DATA_WIDTH
    );
    
    uvm_config_db#(int)::set(
      null,
      "uvm_test_top.*",
      "DEPTH",
      DEPTH
    );
    
    uvm_config_db#(int)::set(
      null,
      "uvm_test_top.*",
      "ADDR_WIDTH",
      ADDR_WIDTH
    );
    
    // Enable waveform dumping
    $dumpfile("fifo_test.vcd");
    $dumpvars(0, tb_top);
    
    // Run the test
    run_test();
  end
  
  // Timeout watchdog
  initial begin
    #1000000; // 1ms timeout
    $display("ERROR: Test timeout!");
    $finish;
  end
  
endmodule