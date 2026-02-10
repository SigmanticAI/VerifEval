// FIFO Sequence Item
class fifo_seq_item extends uvm_sequence_item;
  
  // Data signals
  rand bit        wr_en;
  rand bit        rd_en;
  rand bit [7:0]  wr_data;
  bit [7:0]       rd_data;
  
  // Status signals
  bit             full;
  bit             empty;
  bit             almost_full;
  bit             almost_empty;
  bit [4:0]       count;
  
  // Control fields
  rand bit [3:0]  burst_length;
  rand operation_type_e op_type;
  
  typedef enum {WRITE_ONLY, READ_ONLY, WRITE_READ, IDLE} operation_type_e;
  
  // Constraints
  constraint valid_burst_c {
    burst_length inside {[1:16]};
  }
  
  constraint valid_operation_c {
    op_type inside {WRITE_ONLY, READ_ONLY, WRITE_READ, IDLE};
    if (op_type == WRITE_ONLY) {
      wr_en == 1'b1;
      rd_en == 1'b0;
    }
    if (op_type == READ_ONLY) {
      wr_en == 1'b0;
      rd_en == 1'b1;
    }
    if (op_type == WRITE_READ) {
      wr_en == 1'b1;
      rd_en == 1'b1;
    }
    if (op_type == IDLE) {
      wr_en == 1'b0;
      rd_en == 1'b0;
    }
  }
  
  `uvm_object_utils_begin(fifo_seq_item)
    `uvm_field_int(wr_en, UVM_ALL_ON)
    `uvm_field_int(rd_en, UVM_ALL_ON)
    `uvm_field_int(wr_data, UVM_ALL_ON)
    `uvm_field_int(rd_data, UVM_ALL_ON)
    `uvm_field_int(full, UVM_ALL_ON)
    `uvm_field_int(empty, UVM_ALL_ON)
    `uvm_field_int(almost_full, UVM_ALL_ON)
    `uvm_field_int(almost_empty, UVM_ALL_ON)
    `uvm_field_int(count, UVM_ALL_ON)
    `uvm_field_int(burst_length, UVM_ALL_ON)
    `uvm_field_enum(operation_type_e, op_type, UVM_ALL_ON)
  `uvm_object_utils_end
  
  function new(string name = "fifo_seq_item");
    super.new(name);
  endfunction
  
endclass

// FIFO Driver
class fifo_driver extends uvm_driver #(fifo_seq_item);
  
  virtual sync_fifo_if vif;
  
  `uvm_component_utils(fifo_driver)
  
  function new(string name = "fifo_driver", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual sync_fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF", "Virtual interface must be set for driver")
    end
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    fifo_seq_item req;
    
    // Initialize signals
    vif.wr_en <= 1'b0;
    vif.rd_en <= 1'b0;
    vif.wr_data <= 8'h00;
    
    wait(vif.rst_n === 1'b1);
    @(posedge vif.clk);
    
    forever begin
      seq_item_port.get_next_item(req);
      drive_item(req);
      seq_item_port.item_done();
    end
  endtask
  
  virtual task drive_item(fifo_seq_item req);
    @(posedge vif.clk);
    vif.wr_en <= req.wr_en;
    vif.rd_en <= req.rd_en;
    vif.wr_data <= req.wr_data;
    
    `uvm_info("FIFO_DRIVER", $sformatf("Driving: wr_en=%0b, rd_en=%0b, wr_data=0x%0h", 
              req.wr_en, req.rd_en, req.wr_data), UVM_HIGH)
  endtask
  
endclass

// FIFO Monitor
class fifo_monitor extends uvm_monitor;
  
  virtual sync_fifo_if vif;
  uvm_analysis_port #(fifo_seq_item) item_collected_port;
  
  `uvm_component_utils(fifo_monitor)
  
  function new(string name = "fifo_monitor", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual sync_fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF", "Virtual interface must be set for monitor")
    end
    item_collected_port = new("item_collected_port", this);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    fifo_seq_item trans;
    
    wait(vif.rst_n === 1'b1);
    
    forever begin
      @(posedge vif.clk);
      trans = fifo_seq_item::type_id::create("trans");
      collect_transaction(trans);
      item_collected_port.write(trans);
    end
  endtask
  
  virtual task collect_transaction(fifo_seq_item trans);
    trans.wr_en = vif.wr_en;
    trans.rd_en = vif.rd_en;
    trans.wr_data = vif.wr_data;
    trans.rd_data = vif.rd_data;
    trans.full = vif.full;
    trans.empty = vif.empty;
    trans.almost_full = vif.almost_full;
    trans.almost_empty = vif.almost_empty;
    trans.count = vif.count;
    
    `uvm_info("FIFO_MONITOR", $sformatf("Collected: wr_en=%0b, rd_en=%0b, wr_data=0x%0h, rd_data=0x%0h, full=%0b, empty=%0b, count=%0d", 
              trans.wr_en, trans.rd_en, trans.wr_data, trans.rd_data, trans.full, trans.empty, trans.count), UVM_HIGH)
  endtask
  
endclass

// FIFO Sequencer
typedef uvm_sequencer #(fifo_seq_item) fifo_sequencer;

// FIFO Agent
class fifo_agent extends uvm_agent;
  
  fifo_driver    driver;
  fifo_monitor   monitor;
  fifo_sequencer sequencer;
  
  uvm_analysis_port #(fifo_seq_item) item_collected_port;
  
  `uvm_component_utils(fifo_agent)
  
  function new(string name = "fifo_agent", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    monitor = fifo_monitor::type_id::create("monitor", this);
    
    if (is_active == UVM_ACTIVE) begin
      driver = fifo_driver::type_id::create("driver", this);
      sequencer = fifo_sequencer::type_id::create("sequencer", this);
    end
  endfunction
  
  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    
    item_collected_port = monitor.item_collected_port;
    
    if (is_active == UVM_ACTIVE) begin
      driver.seq_item_port.connect(sequencer.seq_item_export);
    end
  endfunction
  
endclass