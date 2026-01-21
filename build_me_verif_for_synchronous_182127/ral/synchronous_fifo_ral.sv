// ============================================================================
// UVM RAL Model for Synchronous FIFO
// ============================================================================
// This RAL model provides register-level access to FIFO control and status
// Note: FIFO is primarily a data structure, not register-based, but we model
// control/status as registers for UVM RAL integration
// ============================================================================

// ============================================================================
// Register Field Definitions
// ============================================================================

// Write Enable Field
class wr_en_field extends uvm_reg_field;
  `uvm_object_utils(wr_en_field)
  
  function new(string name = "wr_en_field");
    super.new(name);
  endfunction
endclass

// Read Enable Field
class rd_en_field extends uvm_reg_field;
  `uvm_object_utils(rd_en_field)
  
  function new(string name = "rd_en_field");
    super.new(name);
  endfunction
endclass

// Full Flag Field
class full_field extends uvm_reg_field;
  `uvm_object_utils(full_field)
  
  function new(string name = "full_field");
    super.new(name);
  endfunction
endclass

// Empty Flag Field
class empty_field extends uvm_reg_field;
  `uvm_object_utils(empty_field)
  
  function new(string name = "empty_field");
    super.new(name);
  endfunction
endclass

// Almost Full Flag Field
class almost_full_field extends uvm_reg_field;
  `uvm_object_utils(almost_full_field)
  
  function new(string name = "almost_full_field");
    super.new(name);
  endfunction
endclass

// Almost Empty Flag Field
class almost_empty_field extends uvm_reg_field;
  `uvm_object_utils(almost_empty_field)
  
  function new(string name = "almost_empty_field");
    super.new(name);
  endfunction
endclass

// Count Field
class count_field extends uvm_reg_field;
  `uvm_object_utils(count_field)
  
  function new(string name = "count_field");
    super.new(name);
  endfunction
endclass

// Write Data Field
class wr_data_field extends uvm_reg_field;
  `uvm_object_utils(wr_data_field)
  
  function new(string name = "wr_data_field");
    super.new(name);
  endfunction
endclass

// Read Data Field
class rd_data_field extends uvm_reg_field;
  `uvm_object_utils(rd_data_field)
  
  function new(string name = "rd_data_field");
    super.new(name);
  endfunction
endclass

// ============================================================================
// Register Definitions
// ============================================================================

// Control Register - Write and Read Enable
class fifo_ctrl_reg extends uvm_reg;
  `uvm_object_utils(fifo_ctrl_reg)
  
  rand uvm_reg_field wr_en;
  rand uvm_reg_field rd_en;
  rand uvm_reg_field reserved;
  
  function new(string name = "fifo_ctrl_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    wr_en = uvm_reg_field::type_id::create("wr_en");
    rd_en = uvm_reg_field::type_id::create("rd_en");
    reserved = uvm_reg_field::type_id::create("reserved");
    
    // wr_en: bit 0, RW, reset=0
    wr_en.configure(this, 1, 0, "RW", 0, 1'h0, 1, 1, 1);
    
    // rd_en: bit 1, RW, reset=0
    rd_en.configure(this, 1, 1, "RW", 0, 1'h0, 1, 1, 1);
    
    // reserved: bits 31:2, RO, reset=0
    reserved.configure(this, 30, 2, "RO", 0, 30'h0, 1, 0, 0);
  endfunction
endclass

// Status Register - Full, Empty, Almost Full, Almost Empty flags
class fifo_status_reg extends uvm_reg;
  `uvm_object_utils(fifo_status_reg)
  
  rand uvm_reg_field full;
  rand uvm_reg_field empty;
  rand uvm_reg_field almost_full;
  rand uvm_reg_field almost_empty;
  rand uvm_reg_field reserved;
  
  function new(string name = "fifo_status_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    full = uvm_reg_field::type_id::create("full");
    empty = uvm_reg_field::type_id::create("empty");
    almost_full = uvm_reg_field::type_id::create("almost_full");
    almost_empty = uvm_reg_field::type_id::create("almost_empty");
    reserved = uvm_reg_field::type_id::create("reserved");
    
    // full: bit 0, RO, reset=0
    full.configure(this, 1, 0, "RO", 0, 1'h0, 1, 1, 0);
    
    // empty: bit 1, RO, reset=1 (FIFO starts empty)
    empty.configure(this, 1, 1, "RO", 0, 1'h1, 1, 1, 0);
    
    // almost_full: bit 2, RO, reset=0
    almost_full.configure(this, 1, 2, "RO", 0, 1'h0, 1, 1, 0);
    
    // almost_empty: bit 3, RO, reset=0
    almost_empty.configure(this, 1, 3, "RO", 0, 1'h0, 1, 1, 0);
    
    // reserved: bits 31:4, RO, reset=0
    reserved.configure(this, 28, 4, "RO", 0, 28'h0, 1, 0, 0);
  endfunction
endclass

// Count Register - Current number of entries
class fifo_count_reg extends uvm_reg;
  `uvm_object_utils(fifo_count_reg)
  
  rand uvm_reg_field count;
  rand uvm_reg_field reserved;
  
  function new(string name = "fifo_count_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    count = uvm_reg_field::type_id::create("count");
    reserved = uvm_reg_field::type_id::create("reserved");
    
    // count: bits 15:0, RO, reset=0 (supports up to 64K depth)
    count.configure(this, 16, 0, "RO", 0, 16'h0, 1, 1, 0);
    
    // reserved: bits 31:16, RO, reset=0
    reserved.configure(this, 16, 16, "RO", 0, 16'h0, 1, 0, 0);
  endfunction
endclass

// Write Data Register
class fifo_wr_data_reg extends uvm_reg;
  `uvm_object_utils(fifo_wr_data_reg)
  
  rand uvm_reg_field wr_data;
  
  function new(string name = "fifo_wr_data_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    wr_data = uvm_reg_field::type_id::create("wr_data");
    
    // wr_data: bits 31:0, WO, reset=0
    // Note: Actual width depends on DATA_WIDTH parameter
    wr_data.configure(this, 32, 0, "WO", 0, 32'h0, 1, 1, 1);
  endfunction
endclass

// Read Data Register
class fifo_rd_data_reg extends uvm_reg;
  `uvm_object_utils(fifo_rd_data_reg)
  
  rand uvm_reg_field rd_data;
  
  function new(string name = "fifo_rd_data_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    rd_data = uvm_reg_field::type_id::create("rd_data");
    
    // rd_data: bits 31:0, RO, reset=0
    // Note: Actual width depends on DATA_WIDTH parameter
    rd_data.configure(this, 32, 0, "RO", 0, 32'h0, 1, 1, 0);
  endfunction
endclass

// Configuration Register - FIFO parameters
class fifo_config_reg extends uvm_reg;
  `uvm_object_utils(fifo_config_reg)
  
  rand uvm_reg_field data_width;
  rand uvm_reg_field depth;
  
  function new(string name = "fifo_config_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    data_width = uvm_reg_field::type_id::create("data_width");
    depth = uvm_reg_field::type_id::create("depth");
    
    // data_width: bits 15:0, RO, reset=8 (default DATA_WIDTH)
    data_width.configure(this, 16, 0, "RO", 0, 16'h8, 1, 1, 0);
    
    // depth: bits 31:16, RO, reset=16 (default DEPTH)
    depth.configure(this, 16, 16, "RO", 0, 16'h10, 1, 1, 0);
  endfunction
endclass

// Reset Control Register
class fifo_reset_reg extends uvm_reg;
  `uvm_object_utils(fifo_reset_reg)
  
  rand uvm_reg_field soft_reset;
  rand uvm_reg_field reserved;
  
  function new(string name = "fifo_reset_reg");
    super.new(name, 32, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    soft_reset = uvm_reg_field::type_id::create("soft_reset");
    reserved = uvm_reg_field::type_id::create("reserved");
    
    // soft_reset: bit 0, W1C (Write 1 to Clear/Reset), reset=0
    soft_reset.configure(this, 1, 0, "W1C", 0, 1'h0, 1, 1, 1);
    
    // reserved: bits 31:1, RO, reset=0
    reserved.configure(this, 31, 1, "RO", 0, 31'h0, 1, 0, 0);
  endfunction
endclass

// ============================================================================
// Register Block - Top Level
// ============================================================================

class fifo_reg_block extends uvm_reg_block;
  `uvm_object_utils(fifo_reg_block)
  
  // Register instances
  rand fifo_ctrl_reg CTRL;
  rand fifo_status_reg STATUS;
  rand fifo_count_reg COUNT;
  rand fifo_wr_data_reg WR_DATA;
  rand fifo_rd_data_reg RD_DATA;
  rand fifo_config_reg CONFIG;
  rand fifo_reset_reg RESET;
  
  // Address map
  uvm_reg_map default_map;
  
  function new(string name = "fifo_reg_block");
    super.new(name, UVM_NO_COVERAGE);
  endfunction
  
  virtual function void build();
    // Create registers
    CTRL = fifo_ctrl_reg::type_id::create("CTRL");
    CTRL.configure(this, null, "");
    CTRL.build();
    
    STATUS = fifo_status_reg::type_id::create("STATUS");
    STATUS.configure(this, null, "");
    STATUS.build();
    
    COUNT = fifo_count_reg::type_id::create("COUNT");
    COUNT.configure(this, null, "");
    COUNT.build();
    
    WR_DATA = fifo_wr_data_reg::type_id::create("WR_DATA");
    WR_DATA.configure(this, null, "");
    WR_DATA.build();
    
    RD_DATA = fifo_rd_data_reg::type_id::create("RD_DATA");
    RD_DATA.configure(this, null, "");
    RD_DATA.build();
    
    CONFIG = fifo_config_reg::type_id::create("CONFIG");
    CONFIG.configure(this, null, "");
    CONFIG.build();
    
    RESET = fifo_reset_reg::type_id::create("RESET");
    RESET.configure(this, null, "");
    RESET.build();
    
    // Create address map
    default_map = create_map("default_map", 'h0, 4, UVM_LITTLE_ENDIAN);
    
    // Add registers to map with addresses
    default_map.add_reg(CTRL,    'h00, "RW");
    default_map.add_reg(STATUS,  'h04, "RO");
    default_map.add_reg(COUNT,   'h08, "RO");
    default_map.add_reg(WR_DATA, 'h0C, "WO");
    default_map.add_reg(RD_DATA, 'h10, "RO");
    default_map.add_reg(CONFIG,  'h14, "RO");
    default_map.add_reg(RESET,   'h18, "RW");
    
    // Lock the model
    lock_model();
  endfunction
endclass

// ============================================================================
// Register Adapter - Converts between RAL and Bus Protocol
// ============================================================================

class fifo_reg_adapter extends uvm_reg_adapter;
  `uvm_object_utils(fifo_reg_adapter)
  
  function new(string name = "fifo_reg_adapter");
    super.new(name);
    supports_byte_enable = 0;
    provides_responses = 1;
  endfunction
  
  // Convert register operation to bus transaction
  virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
    fifo_bus_transaction bus_trans;
    bus_trans = fifo_bus_transaction::type_id::create("bus_trans");
    
    bus_trans.addr = rw.addr;
    bus_trans.data = rw.data;
    bus_trans.kind = (rw.kind == UVM_READ) ? FIFO_READ : FIFO_WRITE;
    
    return bus_trans;
  endfunction
  
  // Convert bus transaction to register operation
  virtual function void bus2reg(uvm_sequence_item bus_item, ref uvm_reg_bus_op rw);
    fifo_bus_transaction bus_trans;
    
    if (!$cast(bus_trans, bus_item)) begin
      `uvm_fatal("CAST_FAIL", "Failed to cast bus_item to fifo_bus_transaction")
    end
    
    rw.kind = (bus_trans.kind == FIFO_READ) ? UVM_READ : UVM_WRITE;
    rw.addr = bus_trans.addr;
    rw.data = bus_trans.data;
    rw.status = UVM_IS_OK;
  endfunction
endclass

// ============================================================================
// Bus Transaction Item
// ============================================================================

typedef enum {FIFO_READ, FIFO_WRITE} fifo_op_kind_e;

class fifo_bus_transaction extends uvm_sequence_item;
  `uvm_object_utils(fifo_bus_transaction)
  
  rand bit [31:0] addr;
  rand bit [31:0] data;
  rand fifo_op_kind_e kind;
  
  function new(string name = "fifo_bus_transaction");
    super.new(name);
  endfunction
  
  function void do_copy(uvm_object rhs);
    fifo_bus_transaction rhs_;
    if (!$cast(rhs_, rhs)) begin
      `uvm_fatal("CAST_FAIL", "Failed to cast rhs to fifo_bus_transaction")
    end
    super.do_copy(rhs);
    addr = rhs_.addr;
    data = rhs_.data;
    kind = rhs_.kind;
  endfunction
  
  function bit do_compare(uvm_object rhs, uvm_comparer comparer);
    fifo_bus_transaction rhs_;
    if (!$cast(rhs_, rhs)) begin
      return 0;
    end
    return (super.do_compare(rhs, comparer) &&
            (addr == rhs_.addr) &&
            (data == rhs_.data) &&
            (kind == rhs_.kind));
  endfunction
  
  function string convert2string();
    string s;
    s = super.convert2string();
    $sformat(s, "%s\n addr = 0x%0h\n data = 0x%0h\n kind = %s",
             s, addr, data, kind.name());
    return s;
  endfunction
endclass

// ============================================================================
// Register Predictor
// ============================================================================

class fifo_reg_predictor extends uvm_reg_predictor #(fifo_bus_transaction);
  `uvm_component_utils(fifo_reg_predictor)
  
  function new(string name = "fifo_reg_predictor", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
  endfunction
endclass

// ============================================================================
// Register Sequence Base Class
// ============================================================================

class fifo_reg_base_seq extends uvm_reg_sequence;
  `uvm_object_utils(fifo_reg_base_seq)
  
  fifo_reg_block model;
  
  function new(string name = "fifo_reg_base_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    if (model == null) begin
      `uvm_fatal("NO_MODEL", "Register model is null")
    end
  endtask
endclass

// ============================================================================
// Example Register Sequences
// ============================================================================

// Write to FIFO sequence
class fifo_write_seq extends fifo_reg_base_seq;
  `uvm_object_utils(fifo_write_seq)
  
  rand bit [31:0] write_data;
  
  function new(string name = "fifo_write_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    uvm_status_e status;
    uvm_reg_data_t data;
    
    super.body();
    
    // Check if FIFO is full
    model.STATUS.read(status, data, UVM_FRONTDOOR, .parent(this));
    if (data[0] == 1'b1) begin
      `uvm_warning("FIFO_FULL", "Cannot write, FIFO is full")
      return;
    end
    
    // Write data
    model.WR_DATA.write(status, write_data, UVM_FRONTDOOR, .parent(this));
    
    // Set write enable
    model.CTRL.write(status, 32'h1, UVM_FRONTDOOR, .parent(this));
    
    // Clear write enable
    model.CTRL.write(status, 32'h0, UVM_FRONTDOOR, .parent(this));
  endtask
endclass

// Read from FIFO sequence
class fifo_read_seq extends fifo_reg_base_seq;
  `uvm_object_utils(fifo_read_seq)
  
  bit [31:0] read_data;
  
  function new(string name = "fifo_read_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    uvm_status_e status;
    uvm_reg_data_t data;
    
    super.body();
    
    // Check if FIFO is empty
    model.STATUS.read(status, data, UVM_FRONTDOOR, .parent(this));
    if (data[1] == 1'b1) begin
      `uvm_warning("FIFO_EMPTY", "Cannot read, FIFO is empty")
      return;
    end
    
    // Set read enable
    model.CTRL.write(status, 32'h2, UVM_FRONTDOOR, .parent(this));
    
    // Read data
    model.RD_DATA.read(status, data, UVM_FRONTDOOR, .parent(this));
    read_data = data;
    
    // Clear read enable
    model.CTRL.write(status, 32'h0, UVM_FRONTDOOR, .parent(this));
  endtask
endclass

// Reset FIFO sequence
class fifo_reset_seq extends fifo_reg_base_seq;
  `uvm_object_utils(fifo_reset_seq)
  
  function new(string name = "fifo_reset_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    uvm_status_e status;
    
    super.body();
    
    // Trigger soft reset
    model.RESET.write(status, 32'h1, UVM_FRONTDOOR, .parent(this));
    
    // Wait for reset to complete
    #100ns;
    
    // Verify FIFO is empty after reset
    model.STATUS.mirror(status, UVM_CHECK, UVM_FRONTDOOR, .parent(this));
  endtask
endclass

// Check status sequence
class fifo_check_status_seq extends fifo_reg_base_seq;
  `uvm_object_utils(fifo_check_status_seq)
  
  bit full;
  bit empty;
  bit almost_full;
  bit almost_empty;
  int count;
  
  function new(string name = "fifo_check_status_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    uvm_status_e status;
    uvm_reg_data_t data;
    
    super.body();
    
    // Read status register
    model.STATUS.read(status, data, UVM_FRONTDOOR, .parent(this));
    full = data[0];
    empty = data[1];
    almost_full = data[2];
    almost_empty = data[3];
    
    // Read count register
    model.COUNT.read(status, data, UVM_FRONTDOOR, .parent(this));
    count = data[15:0];
    
    `uvm_info("FIFO_STATUS", 
              $sformatf("Status: full=%0b, empty=%0b, almost_full=%0b, almost_empty=%0b, count=%0d",
                        full, empty, almost_full, almost_empty, count), UVM_MEDIUM)
  endtask
endclass

// ============================================================================
// Register Coverage Model
// ============================================================================

class fifo_reg_coverage extends uvm_object;
  `uvm_object_utils(fifo_reg_coverage)
  
  fifo_reg_block model;
  
  // Coverage groups
  covergroup cg_ctrl_reg;
    option.per_instance = 1;
    
    cp_wr_en: coverpoint model.CTRL.wr_en.value {
      bins wr_en_0 = {0};
      bins wr_en_1 = {1};
    }
    
    cp_rd_en: coverpoint model.CTRL.rd_en.value {
      bins rd_en_0 = {0};
      bins rd_en_1 = {1};
    }
    
    cp_wr_rd_cross: cross cp_wr_en, cp_rd_en {
      bins no_op = binsof(cp_wr_en.wr_en_0) && binsof(cp_rd_en.rd_en_0);
      bins wr_only = binsof(cp_wr_en.wr_en_1) && binsof(cp_rd_en.rd_en_0);
      bins rd_only = binsof(cp_wr_en.wr_en_0) && binsof(cp_rd_en.rd_en_1);
      bins simul_wr_rd = binsof(cp_wr_en.wr_en_1) && binsof(cp_rd_en.rd_en_1);
    }
  endgroup
  
  covergroup cg_status_reg;
    option.per_instance = 1;
    
    cp_full: coverpoint model.STATUS.full.value {
      bins not_full = {0};
      bins full = {1};
    }
    
    cp_empty: coverpoint model.STATUS.empty.value {
      bins not_empty = {0};
      bins empty = {1};
    }
    
    cp_almost_full: coverpoint model.STATUS.almost_full.value {
      bins not_almost_full = {0};
      bins almost_full = {1};
    }
    
    cp_almost_empty: coverpoint model.STATUS.almost_empty.value {
      bins not_almost_empty = {0};
      bins almost_empty = {1};
    }
    
    cp_status_cross: cross cp_full, cp_empty, cp_almost_full, cp_almost_empty {
      illegal_bins full_and_empty = binsof(cp_full.full) && binsof(cp_empty.empty);
    }
  endgroup
  
  covergroup cg_count_reg;
    option.per_instance = 1;
    
    cp_count: coverpoint model.COUNT.count.value {
      bins zero = {0};
      bins one = {1};
      bins low = {[2:7]};
      bins mid = {[8:14]};
      bins high = {[15:15]};
      bins max = {16};
    }
  endgroup
  
  function new(string name = "fifo_reg_coverage");
    super.new(name);
    cg_ctrl_reg = new();
    cg_status_reg = new();
    cg_count_reg = new();
  endfunction
  
  function void sample();
    cg_ctrl_reg.sample();
    cg_status_reg.sample();
    cg_count_reg.sample();
  endfunction
endclass

// ============================================================================
// Register Environment
// ============================================================================

class fifo_reg_env extends uvm_env;
  `uvm_component_utils(fifo_reg_env)
  
  fifo_reg_block model;
  fifo_reg_adapter adapter;
  fifo_reg_predictor predictor;
  fifo_reg_coverage coverage;
  
  function new(string name = "fifo_reg_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    // Create register model
    model = fifo_reg_block::type_id::create("model");
    model.build();
    
    // Create adapter
    adapter = fifo_reg_adapter::type_id::create("adapter");
    
    // Create predictor
    predictor = fifo_reg_predictor::type_id::create("predictor", this);
    
    // Create coverage
    coverage = fifo_reg_coverage::type_id::create("coverage");
    coverage.model = model;
  endfunction
  
  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    
    // Connect predictor to register model
    if (model.get_parent() == null) begin
      predictor.map = model.default_map;
      predictor.adapter = adapter;
    end
  endfunction
endclass

// ============================================================================
// Backdoor Access for Memory Array
// ============================================================================

class fifo_mem_backdoor extends uvm_reg_backdoor;
  `uvm_object_utils(fifo_mem_backdoor)
  
  string hdl_path;
  
  function new(string name = "fifo_mem_backdoor");
    super.new(name);
  endfunction
  
  virtual task write(uvm_reg_item rw);
    // Implement backdoor write to FIFO memory array
    // This would use hierarchical path to directly access RTL memory
    `uvm_info("BACKDOOR", $sformatf("Backdoor write to addr=0x%0h, data=0x%0h", 
                                     rw.offset, rw.value[0]), UVM_HIGH)
  endtask
  
  virtual task read(uvm_reg_item rw);
    // Implement backdoor read from FIFO memory array
    `uvm_info("BACKDOOR", $sformatf("Backdoor read from addr=0x%0h", rw.offset), UVM_HIGH)
  endtask
endclass