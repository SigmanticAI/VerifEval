```systemverilog
`timescale 1ns/1ps

module sync_fifo_tb_top;

  import uvm_pkg::*;
  `include "uvm_macros.svh"
  
  // Import test package
  import sync_fifo_test_pkg::*;

  // Parameters
  parameter DATA_WIDTH = 8;
  parameter DEPTH = 16;
  parameter ADDR_WIDTH = $clog2(DEPTH);
  parameter CLK_PERIOD = 10; // 100MHz

  // Clock and reset signals
  logic clk;
  logic rst_n;

  // Interface instantiation
  sync_fifo_if #(
    .DATA_WIDTH(DATA_WIDTH),
    .DEPTH(DEPTH),
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
    .wr_data(fifo_if.wr_data),
    .rd_en(fifo_if.rd_en),
    .rd_data(fifo_if.rd_data),
    .full(fifo_if.full),
    .empty(fifo_if.empty),
    .almost_full(fifo_if.almost_full),
    .almost_empty(fifo_if.almost_empty),
    .count(fifo_if.count),
    .error(fifo_if.error)
  );

  // Clock generation
  initial begin
    clk = 0;
    forever #(CLK_PERIOD/2) clk = ~clk;
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
    uvm_config_db#(virtual sync_fifo_if)::set(
      uvm_root::get(), 
      "*", 
      "fifo_vif", 
      fifo_if
    );

    // Set DUT parameters in config_db
    uvm_config_db#(int)::set(
      uvm_root::get(), 
      "*", 
      "DATA_WIDTH", 
      DATA_WIDTH
    );
    
    uvm_config_db#(int)::set(
      uvm_root::get(), 
      "*", 
      "DEPTH", 
      DEPTH
    );
    
    uvm_config_db#(int)::set(
      uvm_root::get(), 
      "*", 
      "ADDR_WIDTH", 
      ADDR_WIDTH
    );

    // Enable UVM verbosity
    uvm_config_db#(int)::set(
      uvm_root::get(), 
      "*", 
      "recording_detail", 
      UVM_FULL
    );

    // Run the test
    run_test();
  end

  // Timeout watchdog
  initial begin
    #1000000; // 1ms timeout
    `uvm_fatal("TIMEOUT", "Test timed out!")
  end

  // Waveform dumping
  initial begin
    if ($test$plusargs("DUMP_VCD")) begin
      $dumpfile("sync_fifo_tb.vcd");
      $dumpvars(0, sync_fifo_tb_top);
    end
    
    if ($test$plusargs("DUMP_FSDB")) begin
      $fsdbDumpfile("sync_fifo_tb.fsdb");
      $fsdbDumpvars(0, sync_fifo_tb_top);
    end
  end

  // Coverage collection
  initial begin
    if ($test$plusargs("COVERAGE")) begin
      $set_coverage_db_name("sync_fifo_coverage.ucdb");
    end
  end

  // Assertions for basic protocol checks
  property no_overflow;
    @(posedge clk) disable iff (!rst_n)
    (fifo_if.full && fifo_if.wr_en && !fifo_if.rd_en) |=> fifo_if.error;
  endproperty

  property no_underflow;
    @(posedge clk) disable iff (!rst_n)
    (fifo_if.empty && fifo_if.rd_en && !fifo_if.wr_en) |=> fifo_if.error;
  endproperty

  property count_bounds;
    @(posedge clk) disable iff (!rst_n)
    fifo_if.count <= DEPTH;
  endproperty

  property full_empty_mutex;
    @(posedge clk) disable iff (!rst_n)
    !(fifo_if.full && fifo_if.empty);
  endproperty

  property reset_state;
    @(posedge clk)
    !rst_n |=> (fifo_if.empty && !fifo_if.full && !fifo_if.almost_full && 
                 fifo_if.count == 0 && !fifo_if.error);
  endproperty

  // Bind assertions
  assert_no_overflow: assert property(no_overflow)
    else `uvm_error("ASSERT", "Overflow not detected properly")

  assert_no_underflow: assert property(no_underflow)
    else `uvm_error("ASSERT", "Underflow not detected properly")

  assert_count_bounds: assert property(count_bounds)
    else `uvm_error("ASSERT", "Count exceeded DEPTH")

  assert_full_empty_mutex: assert property(full_empty_mutex)
    else `uvm_error("ASSERT", "Full and empty flags both asserted")

  assert_reset_state: assert property(reset_state)
    else `uvm_error("ASSERT", "Reset state incorrect")

  // Coverage assertions
  cover_overflow: cover property(no_overflow);
  cover_underflow: cover property(no_underflow);
  cover_full_state: cover property(@(posedge clk) fifo_if.full);
  cover_empty_state: cover property(@(posedge clk) fifo_if.empty);
  cover_almost_full: cover property(@(posedge clk) fifo_if.almost_full);
  cover_almost_empty: cover property(@(posedge clk) fifo_if.almost_empty);

  // Debug information
  initial begin
    `uvm_info("TB_TOP", $sformatf("Starting sync_fifo testbench with parameters: DATA_WIDTH=%0d, DEPTH=%0d, ADDR_WIDTH=%0d", 
              DATA_WIDTH, DEPTH, ADDR_WIDTH), UVM_LOW)
  end

  // Final report
  final begin
    `uvm_info("TB_TOP", "Testbench completed", UVM_LOW)
  end

endmodule
```