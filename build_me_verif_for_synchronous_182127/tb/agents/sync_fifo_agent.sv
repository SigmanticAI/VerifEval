// ============================================================================
// Synchronous FIFO UVM Sequence Item
// ============================================================================
class sync_fifo_seq_item extends uvm_sequence_item;
  
  // Randomized transaction fields
  rand bit wr_en;
  rand bit rd_en;
  rand bit [31:0] wr_data;  // Parameterizable via config
  
  // Response fields (from monitor)
  bit [31:0] rd_data;
  bit full;
  bit empty;
  bit almost_full;
  bit almost_empty;
  bit [31:0] count;
  
  // Constraints
  constraint valid_ops_c {
    wr_en dist {1 := 70, 0 := 30};
    rd_en dist {1 := 70, 0 := 30};
  }
  
  // UVM automation macros
  `uvm_object_utils_begin(sync_fifo_seq_item)
    `uvm_field_int(wr_en, UVM_ALL_ON)
    `uvm_field_int(rd_en, UVM_ALL_ON)
    `uvm_field_int(wr_data, UVM_ALL_ON | UVM_HEX)
    `uvm_field_int(rd_data, UVM_ALL_ON | UVM_HEX)
    `uvm_field_int(full, UVM_ALL_ON)
    `uvm_field_int(empty, UVM_ALL_ON)
    `uvm_field_int(almost_full, UVM_ALL_ON)
    `uvm_field_int(almost_empty, UVM_ALL_ON)
    `uvm_field_int(count, UVM_ALL_ON | UVM_DEC)
  `uvm_object_utils_end
  
  // Constructor
  function new(string name = "sync_fifo_seq_item");
    super.new(name);
  endfunction
  
  // Convert to string for printing
  function string convert2string();
    string s;
    s = super.convert2string();
    s = {s, $sformatf("\n  wr_en=%0b rd_en=%0b wr_data=0x%0h", wr_en, rd_en, wr_data)};
    s = {s, $sformatf("\n  rd_data=0x%0h full=%0b empty=%0b", rd_data, full, empty)};
    s = {s, $sformatf("\n  almost_full=%0b almost_empty=%0b count=%0d", almost_full, almost_empty, count)};
    return s;
  endfunction
  
endclass : sync_fifo_seq_item


// ============================================================================
// Synchronous FIFO UVM Sequencer
// ============================================================================
class sync_fifo_sequencer extends uvm_sequencer #(sync_fifo_seq_item);
  
  `uvm_component_utils(sync_fifo_sequencer)
  
  // Constructor
  function new(string name = "sync_fifo_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
endclass : sync_fifo_sequencer


// ============================================================================
// Synchronous FIFO UVM Driver
// ============================================================================
class sync_fifo_driver extends uvm_driver #(sync_fifo_seq_item);
  
  `uvm_component_utils(sync_fifo_driver)
  
  // Virtual interface handle
  virtual sync_fifo_if vif;
  
  // Constructor
  function new(string name = "sync_fifo_driver", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  // Build phase - get virtual interface from config DB
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db#(virtual sync_fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal(get_type_name(), "Virtual interface not found in config DB")
    end
  endfunction
  
  // Run phase - drive transactions
  task run_phase(uvm_phase phase);
    sync_fifo_seq_item req;
    
    // Initialize signals
    vif.wr_en  $stable(count);
  endproperty
  
  property p_no_read_when_empty;
    @(posedge clk) disable iff (!rst_n)
    (empty && rd_en && !wr_en) |=> $stable(count);
  endproperty
  
  property p_count_range;
    @(posedge clk) disable iff (!rst_n)
    count  full;
  endproperty
  
  property p_empty_when_count_zero;
    @(posedge clk) disable iff (!rst_n)
    (count == 0) |-> empty;
  endproperty
  
  property p_almost_full_when_count_depth_minus_1;
    @(posedge clk) disable iff (!rst_n)
    (count == (DEPTH-1)) |-> almost_full;
  endproperty
  
  property p_almost_empty_when_count_1;
    @(posedge clk) disable iff (!rst_n)
    (count == 1) |-> almost_empty;
  endproperty
  
  // Assertion instantiation
  assert_no_write_when_full: assert property(p_no_write_when_full)
    else `uvm_error("FIFO_IF", "Write attempted when FIFO full")
  
  assert_no_read_when_empty: assert property(p_no_read_when_empty)
    else `uvm_error("FIFO_IF", "Read attempted when FIFO empty")
  
  assert_count_range: assert property(p_count_range)
    else `uvm_error("FIFO_IF", "Count exceeded DEPTH")
  
  assert_full_when_count_max: assert property(p_full_when_count_max)
    else `uvm_error("FIFO_IF", "Full flag not set when count equals DEPTH")
  
  assert_empty_when_count_zero: assert property(p_empty_when_count_zero)
    else `uvm_error("FIFO_IF", "Empty flag not set when count equals 0")
  
  assert_almost_full: assert property(p_almost_full_when_count_depth_minus_1)
    else `uvm_error("FIFO_IF", "Almost full flag incorrect")
  
  assert_almost_empty: assert property(p_almost_empty_when_count_1)
    else `uvm_error("FIFO_IF", "Almost empty flag incorrect")
  
endinterface : sync_fifo_if