package fifo_test_pkg;
  
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  
  // FIFO Interface
  interface fifo_if (input logic clk, rst_n);
    logic        wr_en;
    logic        rd_en;
    logic [7:0]  data_in;
    logic [7:0]  data_out;
    logic        full;
    logic        empty;
    logic        almost_full;
    logic        almost_empty;
    
    clocking driver_cb @(posedge clk);
      default input #1 output #1;
      output wr_en, rd_en, data_in;
      input data_out, full, empty, almost_full, almost_empty;
    endclocking
    
    clocking monitor_cb @(posedge clk);
      default input #1;
      input wr_en, rd_en, data_in, data_out, full, empty, almost_full, almost_empty;
    endclocking
    
    modport driver(clocking driver_cb, input clk, rst_n);
    modport monitor(clocking monitor_cb, input clk, rst_n);
  endinterface

  // Transaction class
  class fifo_transaction extends uvm_sequence_item;
    rand bit        wr_en;
    rand bit        rd_en;
    rand bit [7:0]  data_in;
    bit [7:0]       data_out;
    bit             full;
    bit             empty;
    bit             almost_full;
    bit             almost_empty;
    
    constraint valid_ops_c {
      wr_en dist {0 := 30, 1 := 70};
      rd_en dist {0 := 30, 1 := 70};
    }
    
    `uvm_object_utils_begin(fifo_transaction)
      `uvm_field_int(wr_en, UVM_ALL_ON)
      `uvm_field_int(rd_en, UVM_ALL_ON)
      `uvm_field_int(data_in, UVM_ALL_ON)
      `uvm_field_int(data_out, UVM_ALL_ON)
      `uvm_field_int(full, UVM_ALL_ON)
      `uvm_field_int(empty, UVM_ALL_ON)
      `uvm_field_int(almost_full, UVM_ALL_ON)
      `uvm_field_int(almost_empty, UVM_ALL_ON)
    `uvm_object_utils_end
    
    function new(string name = "fifo_transaction");
      super.new(name);
    endfunction
  endclass

  // Sequencer
  class fifo_sequencer extends uvm_sequencer #(fifo_transaction);
    `uvm_component_utils(fifo_sequencer)
    
    function new(string name = "fifo_sequencer", uvm_component parent = null);
      super.new(name, parent);
    endfunction
  endclass

  // Driver
  class fifo_driver extends uvm_driver #(fifo_transaction);
    virtual fifo_if vif;
    
    `uvm_component_utils(fifo_driver)
    
    function new(string name = "fifo_driver", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "Virtual interface not found")
    endfunction
    
    task run_phase(uvm_phase phase);
      forever begin
        seq_item_port.get_next_item(req);
        drive_transaction(req);
        seq_item_port.item_done();
      end
    endtask
    
    task drive_transaction(fifo_transaction trans);
      @(vif.driver_cb);
      vif.driver_cb.wr_en <= trans.wr_en;
      vif.driver_cb.rd_en <= trans.rd_en;
      vif.driver_cb.data_in <= trans.data_in;
    endtask
  endclass

  // Monitor
  class fifo_monitor extends uvm_monitor;
    virtual fifo_if vif;
    uvm_analysis_port #(fifo_transaction) ap;
    
    `uvm_component_utils(fifo_monitor)
    
    function new(string name = "fifo_monitor", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      ap = new("ap", this);
      if (!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "Virtual interface not found")
    endfunction
    
    task run_phase(uvm_phase phase);
      forever begin
        fifo_transaction trans = fifo_transaction::type_id::create("trans");
        @(vif.monitor_cb);
        trans.wr_en = vif.monitor_cb.wr_en;
        trans.rd_en = vif.monitor_cb.rd_en;
        trans.data_in = vif.monitor_cb.data_in;
        trans.data_out = vif.monitor_cb.data_out;
        trans.full = vif.monitor_cb.full;
        trans.empty = vif.monitor_cb.empty;
        trans.almost_full = vif.monitor_cb.almost_full;
        trans.almost_empty = vif.monitor_cb.almost_empty;
        ap.write(trans);
      end
    endtask
  endclass

  // Agent
  class fifo_agent extends uvm_agent;
    fifo_driver    driver;
    fifo_monitor   monitor;
    fifo_sequencer sequencer;
    
    `uvm_component_utils(fifo_agent)
    
    function new(string name = "fifo_agent", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      driver = fifo_driver::type_id::create("driver", this);
      monitor = fifo_monitor::type_id::create("monitor", this);
      sequencer = fifo_sequencer::type_id::create("sequencer", this);
    endfunction
    
    function void connect_phase(uvm_phase phase);
      driver.seq_item_port.connect(sequencer.seq_item_export);
    endfunction
  endclass

  // Scoreboard
  class fifo_scoreboard extends uvm_scoreboard;
    uvm_analysis_imp #(fifo_transaction, fifo_scoreboard) ap_imp;
    
    int unsigned write_count;
    int unsigned read_count;
    bit [7:0] expected_data[$];
    
    `uvm_component_utils(fifo_scoreboard)
    
    function new(string name = "fifo_scoreboard", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      ap_imp = new("ap_imp", this);
    endfunction
    
    function void write(fifo_transaction trans);
      if (trans.wr_en && !trans.full) begin
        expected_data.push_back(trans.data_in);
        write_count++;
        `uvm_info("SCB", $sformatf("Write data: 0x%02h", trans.data_in), UVM_MEDIUM)
      end
      
      if (trans.rd_en && !trans.empty) begin
        if (expected_data.size() > 0) begin
          bit [7:0] expected = expected_data.pop_front();
          read_count++;
          if (trans.data_out == expected) begin
            `uvm_info("SCB", $sformatf("Read data matched: 0x%02h", trans.data_out), UVM_MEDIUM)
          end else begin
            `uvm_error("SCB", $sformatf("Data mismatch! Expected: 0x%02h, Got: 0x%02h", expected, trans.data_out))
          end
        end
      end
      
      // Check flags
      if (expected_data.size() == 0 && !trans.empty) begin
        `uvm_error("SCB", "Empty flag should be asserted when FIFO is empty")
      end
      
      if (expected_data.size() == 16 && !trans.full) begin
        `uvm_error("SCB", "Full flag should be asserted when FIFO is full")
      end
    endfunction
    
    function void report_phase(uvm_phase phase);
      `uvm_info("SCB", $sformatf("Writes: %0d, Reads: %0d", write_count, read_count), UVM_LOW)
    endfunction
  endclass

  // Environment
  class fifo_env extends uvm_env;
    fifo_agent      agent;
    fifo_scoreboard scoreboard;
    
    `uvm_component_utils(fifo_env)
    
    function new(string name = "fifo_env", uvm_component parent = null);
      super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      agent = fifo_agent::type_id::create("agent", this);
      scoreboard = fifo_scoreboard::type_id::create("scoreboard", this);
    endfunction
    
    function void connect_phase(uvm_phase phase);
      agent.monitor.ap.connect(scoreboard.ap_imp);
    endfunction
  endclass

  // Base sequence
  class fifo_base_sequence extends uvm_sequence #(fifo_transaction);
    `uvm_object_utils(fifo_base_sequence)
    
    function new(string name = "fifo_base_sequence");
      super.new(name);
    endfunction
    
    task body();
      for (int i = 0; i < 100; i++) begin
        req = fifo_transaction::type_id::create("req");
        start_item(req);
        if (!req.randomize()) begin
          `uvm_error("SEQ", "Randomization failed")
        end
        finish_item(req);
      end
    endtask
  endclass

  // Write only sequence
  class fifo_write_sequence extends uvm_sequence #(fifo_transaction);
    `uvm_object_utils(fifo_write_sequence)
    
    function new(string name = "fifo_write_sequence");
      super.new(name);
    endfunction
    
    task body();
      for (int i = 0; i < 20; i++) begin
        req = fifo_transaction::type_id::create("req");
        start_item(req);
        req.wr_en = 1'b1;
        req.rd_en = 1'b0;
        req.data_in = $random();
        finish_item(req);
      end
    endtask
  endclass

  // Read only sequence
  class fifo_read_sequence extends uvm_sequence #(fifo_transaction);
    `uvm_object_utils(fifo_read_sequence)
    
    function new(string name = "fifo_read_sequence");
      super.new(name);
    endfunction
    