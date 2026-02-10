// FIFO Interface
interface fifo_if(input logic clk, rst_n);
  logic wr_en;
  logic rd_en;
  logic [7:0] data_in;
  logic [7:0] data_out;
  logic full;
  logic empty;
  logic almost_full;
  logic almost_empty;
  
  clocking driver_cb @(posedge clk);
    output wr_en, rd_en, data_in;
    input data_out, full, empty, almost_full, almost_empty;
  endclocking
  
  clocking monitor_cb @(posedge clk);
    input wr_en, rd_en, data_in, data_out, full, empty, almost_full, almost_empty;
  endclocking
  
  modport driver(clocking driver_cb);
  modport monitor(clocking monitor_cb);
  
endinterface

// Sequence Item
class fifo_seq_item extends uvm_sequence_item;
  rand bit wr_en;
  rand bit rd_en;
  rand logic [7:0] data_in;
  logic [7:0] data_out;
  logic full;
  logic empty;
  logic almost_full;
  logic almost_empty;
  
  constraint valid_op {
    wr_en dist {1 := 70, 0 := 30};
    rd_en dist {1 := 70, 0 := 30};
  }
  
  `uvm_object_utils_begin(fifo_seq_item)
    `uvm_field_int(wr_en, UVM_ALL_ON)
    `uvm_field_int(rd_en, UVM_ALL_ON)
    `uvm_field_int(data_in, UVM_ALL_ON)
    `uvm_field_int(data_out, UVM_ALL_ON)
    `uvm_field_int(full, UVM_ALL_ON)
    `uvm_field_int(empty, UVM_ALL_ON)
    `uvm_field_int(almost_full, UVM_ALL_ON)
    `uvm_field_int(almost_empty, UVM_ALL_ON)
  `uvm_object_utils_end
  
  function new(string name = "fifo_seq_item");
    super.new(name);
  endfunction
  
endclass

// Base Sequence
class fifo_base_seq extends uvm_sequence#(fifo_seq_item);
  `uvm_object_utils(fifo_base_seq)
  
  function new(string name = "fifo_base_seq");
    super.new(name);
  endfunction
  
endclass

// Basic Sequence
class fifo_basic_seq extends fifo_base_seq;
  `uvm_object_utils(fifo_basic_seq)
  
  function new(string name = "fifo_basic_seq");
    super.new(name);
  endfunction
  
  task body();
    fifo_seq_item req;
    repeat(50) begin
      req = fifo_seq_item::type_id::create("req");
      start_item(req);
      assert(req.randomize());
      finish_item(req);
    end
  endtask
  
endclass

// Write Only Sequence
class fifo_write_seq extends fifo_base_seq;
  `uvm_object_utils(fifo_write_seq)
  
  function new(string name = "fifo_write_seq");
    super.new(name);
  endfunction
  
  task body();
    fifo_seq_item req;
    repeat(20) begin
      req = fifo_seq_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
  
endclass

// Read Only Sequence
class fifo_read_seq extends fifo_base_seq;
  `uvm_object_utils(fifo_read_seq)
  
  function new(string name = "fifo_read_seq");
    super.new(name);
  endfunction
  
  task body();
    fifo_seq_item req;
    repeat(20) begin
      req = fifo_seq_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
  
endclass

// Reset Sequence
class fifo_reset_seq extends fifo_base_seq;
  `uvm_object_utils(fifo_reset_seq)
  
  function new(string name = "fifo_reset_seq");
    super.new(name);
  endfunction
  
  task body();
    fifo_seq_item req;
    repeat(5) begin
      req = fifo_seq_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
  
endclass

// Stress Test Sequence
class fifo_stress_seq extends fifo_base_seq;
  `uvm_object_utils(fifo_stress_seq)
  
  function new(string name = "fifo_stress_seq");
    super.new(name);
  endfunction
  
  task body();
    fifo_seq_item req;
    repeat(200) begin
      req = fifo_seq_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en dist {1 := 80, 0 := 20};
        rd_en dist {1 := 80, 0 := 20};
      });
      finish_item(req);
    end
  endtask
  
endclass

// Driver
class fifo_driver extends uvm_driver#(fifo_seq_item);
  `uvm_component_utils(fifo_driver)
  
  virtual fifo_if vif;
  
  function new(string name = "fifo_driver", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("DRIVER", "Could not get vif")
    end
  endfunction
  
  task run_phase(uvm_phase phase);
    fifo_seq_item req;
    forever begin
      seq_item_port.get_next_item(req);
      drive_item(req);
      seq_item_port.item_done();
    end
  endtask
  
  task drive_item(fifo_seq_item req);
    @(vif.driver_cb);
    vif.driver_cb.wr_en <= req.wr_en;
    vif.driver_cb.rd_en <= req.rd_en;
    vif.driver_cb.data_in <= req.data_in;
  endtask
  
endclass

// Monitor
class fifo_monitor extends uvm_monitor;
  `uvm_component_utils(fifo_monitor)
  
  virtual fifo_if vif;
  uvm_analysis_port#(fifo_seq_item) ap;
  
  function new(string name = "fifo_monitor", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap = new("ap", this);
    if(!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("MONITOR", "Could not get vif")
    end
  endfunction
  
  task run_phase(uvm_phase phase);
    fifo_seq_item item;
    forever begin
      @(vif.monitor_cb);
      item = fifo_seq_item::type_id::create("item");
      item.wr_en = vif.monitor_cb.wr_en;
      item.rd_en = vif.monitor_cb.rd_en;
      item.data_in = vif.monitor_cb.data_in;
      item.data_out = vif.monitor_cb.data_out;
      item.full = vif.monitor_cb.full;
      item.empty = vif.monitor_cb.empty;
      item.almost_full = vif.monitor_cb.almost_full;
      item.almost_empty = vif.monitor_cb.almost_empty;
      ap.write(item);
    end
  endtask
  
endclass

// Agent
class fifo_agent extends uvm_agent;
  `uvm_component_utils(fifo_agent)
  
  fifo_driver driver;
  fifo_monitor monitor;
  uvm_sequencer#(fifo_seq_item) sequencer;
  
  function new(string name = "fifo_agent", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(is_active == UVM_ACTIVE) begin
      driver = fifo_driver::type_id::create("driver", this);
      sequencer = uvm_sequencer#(fifo_seq_item)::type_id::create("sequencer", this);
    end
    monitor = fifo_monitor::type_id::create("monitor", this);
  endfunction
  
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if(is_active == UVM_ACTIVE) begin
      driver.seq_item_port.connect(sequencer.seq_item_export);
    end
  endfunction
  
endclass

// Scoreboard
class fifo_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(fifo_scoreboard)
  
  uvm_analysis_imp#(fifo_seq_item, fifo_scoreboard) ap_imp;
  
  fifo_seq_item expected_queue[$];
  logic [7:0] reference_fifo[$];
  int write_count = 0;
  int read_count = 0;
  int error_count = 0;
  
  function new(string name = "fifo_scoreboard", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap_imp = new("ap_imp", this);
  endfunction
  
  function void write(fifo_seq_item item);
    check_transaction(item);
  endfunction
  
  function void check_transaction(fifo_seq_item item);
    logic expected_full, expected_empty;
    
    // Check write operation
    if(item.wr_en && !item.full) begin
      reference_fifo.push_back(item.data_in);
      write_count++;
      `uvm_info("SCOREBOARD", $sformatf("Write data: %0h", item.data_in), UVM_MEDIUM)
    end
    
    // Check read operation
    if(item.rd_en && !item.empty) begin
      logic [7:0] expected_data;
      if(reference_fifo.size() > 0) begin
        expected_data = reference_fifo.pop_front();
        read_count++;
        if(item.data_out !== expected_data) begin
          error_count++;
          `uvm_error("SCOREBOARD", $sformatf("Data mismatch! Expected: %0h, Got: %0h", expected_data, item.data_out))
        end else begin
          `uvm_info("SCOREBOARD", $sformatf("Read data match: %0h", item.data_out), UVM_MEDIUM)
        end
      end
    end
    
    // Check status flags
    expected_empty = (reference_fifo.size() == 0);
    expected_full = (reference_fifo.size() >= 16);
    
    if(item.empty !== expected_empty) begin
      error_count++;
      `uvm_error("SCOREBOARD", $sformatf("Empty flag mismatch! Expected: %0b, Got: %0b", expected_empty, item.empty))
    end
    
    if(item.full !== expected_full) begin
      error_count++;
      `uvm_error("SCOREBOARD", $sformatf("Full flag mismatch! Expected: %0b, Got: %0b", expected_full, item.full))
    end
  endfunction
  
  function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    `uvm_info("SCOREBOARD", $sformatf("Write Count: %0d", write_count), UVM_LOW)
    `uvm_info("SCOREBOARD", $sformatf("Read Count: %0d", read_count), UVM_LOW)
    `uvm_info("SCOREBOARD", $sformatf("Error Count: %0d", error_count), UVM_LOW)
    if(error_count == 0)
      `uvm_info("SCOREBOARD", "TEST PASSED!", UVM_LOW)
    else
      `uvm_error("SCOREBOARD", "TEST FAILED!")
  endfunction
  
endclass

// Environment
class fifo_env extends uvm_env;
  `uvm_component_utils(fifo_env)
  
  fifo_agent agent;
  fifo_scoreboard sb;
  
  function new(string name = "fifo_env", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agent = fifo_agent::type_id::create("agent", this);
    sb = fifo_scoreboard::type_id::create("sb", this);
  endfunction
  
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agent.monitor.ap.connect(sb.ap_imp);
  endfunction
  
endclass

// Base Test
class fifo_base_test extends uvm_test;
  `uvm_component_utils(fifo_base_test)
  
  fifo_env env;
  
  function new(string name = "fifo_base_test", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = fifo_env::type_id::create("env", this);
  endfunction
  
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    #100;
    phase.drop_objection(this);
  endtask
  
endclass

// Reset Test
class fifo_reset_test extends fifo_base_test;
  `uvm_component_utils(fifo_reset_test)
  
  function new(string name = "fifo_reset_test", uvm_component parent);
    super.new(name, parent);
  endfunction
  
  task run_phase(uvm_phase phase);
    fifo_reset_seq seq;
    phase