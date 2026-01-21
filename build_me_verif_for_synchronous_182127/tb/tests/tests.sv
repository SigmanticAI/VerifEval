// Base Test Class
class synchronous_fifo_base_test extends uvm_test;
  `uvm_component_utils(synchronous_fifo_base_test)
  
  synchronous_fifo_env env;
  synchronous_fifo_config cfg;
  
  function new(string name = "synchronous_fifo_base_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    
    cfg = synchronous_fifo_config::type_id::create("cfg");
    if (!uvm_config_db#(virtual synchronous_fifo_if)::get(this, "", "vif", cfg.vif))
      `uvm_fatal(get_type_name(), "Virtual interface not found")
    
    uvm_config_db#(synchronous_fifo_config)::set(this, "*", "cfg", cfg);
    env = synchronous_fifo_env::type_id::create("env", this);
  endfunction
  
  virtual function void end_of_elaboration_phase(uvm_phase phase);
    super.end_of_elaboration_phase(phase);
    uvm_top.print_topology();
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    apply_reset();
    phase.drop_objection(this);
  endtask
  
  virtual task apply_reset();
    cfg.vif.rst_n  0) begin
      `uvm_info(get_type_name(), "TEST FAILED", UVM_NONE)
    end else begin
      `uvm_info(get_type_name(), "TEST PASSED", UVM_NONE)
    end
  endfunction
endclass

// Base Sequence
class synchronous_fifo_base_seq extends uvm_sequence#(synchronous_fifo_transaction);
  `uvm_object_utils(synchronous_fifo_base_seq)
  
  function new(string name = "synchronous_fifo_base_seq");
    super.new(name);
  endfunction
  
  virtual task pre_body();
    if (starting_phase != null)
      starting_phase.raise_objection(this);
  endtask
  
  virtual task post_body();
    if (starting_phase != null)
      starting_phase.drop_objection(this);
  endtask
endclass

// Reset Sequence
class reset_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(reset_seq)
  
  function new(string name = "reset_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    repeat(10) begin
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Reset
class test_reset extends synchronous_fifo_base_test;
  `uvm_component_utils(test_reset)
  
  function new(string name = "test_reset", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    reset_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = reset_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Basic Write Read Sequence
class basic_write_read_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(basic_write_read_seq)
  
  rand bit [31:0] write_data[4];
  
  function new(string name = "basic_write_read_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write 4 entries
    for (int i = 0; i < 4; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
        wr_data == write_data[i];
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read 4 entries
    for (int i = 0; i < 4; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Basic Write Read
class test_basic_write_read extends synchronous_fifo_base_test;
  `uvm_component_utils(test_basic_write_read)
  
  function new(string name = "test_basic_write_read", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    basic_write_read_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = basic_write_read_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Single Write Read Sequence
class single_write_read_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(single_write_read_seq)
  
  rand bit [31:0] test_data;
  
  function new(string name = "single_write_read_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write single entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
      wr_data == test_data;
    });
    finish_item(req);
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read single entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Single Write Read
class test_single_write_read extends synchronous_fifo_base_test;
  `uvm_component_utils(test_single_write_read)
  
  function new(string name = "test_single_write_read", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    single_write_read_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = single_write_read_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Fill FIFO Sequence
class fill_fifo_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(fill_fifo_seq)
  
  int depth;
  
  function new(string name = "fill_fifo_seq");
    super.new(name);
    depth = 16; // Default depth
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Full Flag Assertion
class test_full_flag_assertion extends synchronous_fifo_base_test;
  `uvm_component_utils(test_full_flag_assertion)
  
  function new(string name = "test_full_flag_assertion", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    fill_fifo_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = fill_fifo_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Full Flag Deassertion Sequence
class full_flag_deassertion_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(full_flag_deassertion_seq)
  
  int depth;
  
  function new(string name = "full_flag_deassertion_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read one entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Full Flag Deassertion
class test_full_flag_deassertion extends synchronous_fifo_base_test;
  `uvm_component_utils(test_full_flag_deassertion)
  
  function new(string name = "test_full_flag_deassertion", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    full_flag_deassertion_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = full_flag_deassertion_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Empty FIFO Sequence
class empty_fifo_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(empty_fifo_seq)
  
  int depth;
  
  function new(string name = "empty_fifo_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO first
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Empty FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Empty Flag Assertion
class test_empty_flag_assertion extends synchronous_fifo_base_test;
  `uvm_component_utils(test_empty_flag_assertion)
  
  function new(string name = "test_empty_flag_assertion", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    empty_fifo_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = empty_fifo_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Empty Flag Deassertion Sequence
class empty_flag_deassertion_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(empty_flag_deassertion_seq)
  
  function new(string name = "empty_flag_deassertion_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Write one entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
  endtask
endclass

// Test Empty Flag Deassertion
class test_empty_flag_deassertion extends synchronous_fifo_base_test;
  `uvm_component_utils(test_empty_flag_deassertion)
  
  function new(string name = "test_empty_flag_deassertion", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    empty_flag_deassertion_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = empty_flag_deassertion_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Almost Full Flag Sequence
class almost_full_flag_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(almost_full_flag_seq)
  
  int depth;
  
  function new(string name = "almost_full_flag_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill to DEPTH-1
    for (int i = 0; i < depth-1; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Write one more
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
  endtask
endclass

// Test Almost Full Flag
class test_almost_full_flag extends synchronous_fifo_base_test;
  `uvm_component_utils(test_almost_full_flag)
  
  function new(string name = "test_almost_full_flag", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    almost_full_flag_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = almost_full_flag_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Almost Empty Flag Sequence
class almost_empty_flag_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(almost_empty_flag_seq)
  
  function new(string name = "almost_empty_flag_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write 2 entries
    for (int i = 0; i < 2; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Read 1 entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read 1 more
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Almost Empty Flag
class test_almost_empty_flag extends synchronous_fifo_base_test;
  `uvm_component_utils(test_almost_empty_flag)
  
  function new(string name = "test_almost_empty_flag", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    almost_empty_flag_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = almost_empty_flag_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Random Operations Sequence
class random_operations_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(random_operations_seq)
  
  int num_operations;
  
  function new(string name = "random_operations_seq");
    super.new(name);
    num_operations = 100;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize());
      finish_item(req);
    end
  endtask
endclass

// Test Flag Mutual Exclusion
class test_flag_mutual_exclusion extends synchronous_fifo_base_test;
  `uvm_component_utils(test_flag_mutual_exclusion)
  
  function new(string name = "test_flag_mutual_exclusion", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 200;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Flag Coherency
class test_flag_coherency extends synchronous_fifo_base_test;
  `uvm_component_utils(test_flag_coherency)
  
  function new(string name = "test_flag_coherency", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 200;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Count Increment Sequence
class count_increment_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(count_increment_seq)
  
  int num_writes;
  
  function new(string name = "count_increment_seq");
    super.new(name);
    num_writes = 8;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_writes; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Count Increment
class test_count_increment extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_increment)
  
  function new(string name = "test_count_increment", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    count_increment_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = count_increment_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Count Decrement Sequence
class count_decrement_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(count_decrement_seq)
  
  int depth;
  int num_reads;
  
  function new(string name = "count_decrement_seq");
    super.new(name);
    depth = 16;
    num_reads = 8;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO first
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Read entries
    for (int i = 0; i < num_reads; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Count Decrement
class test_count_decrement extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_decrement)
  
  function new(string name = "test_count_decrement", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    count_decrement_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = count_decrement_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Count Stable Simultaneous RW Sequence
class count_stable_simul_rw_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(count_stable_simul_rw_seq)
  
  int num_operations;
  
  function new(string name = "count_stable_simul_rw_seq");
    super.new(name);
    num_operations = 10;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write some entries first
    for (int i = 0; i < 5; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Simultaneous R/W operations
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Count Stable Simultaneous RW
class test_count_stable_simul_rw extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_stable_simul_rw)
  
  function new(string name = "test_count_stable_simul_rw", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    count_stable_simul_rw_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = count_stable_simul_rw_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Count All Values Sequence
class count_all_values_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(count_all_values_seq)
  
  int depth;
  
  function new(string name = "count_all_values_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO to exercise all count values
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Empty FIFO to exercise all count values
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Count All Values
class test_count_all_values extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_all_values)
  
  function new(string name = "test_count_all_values", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    count_all_values_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = count_all_values_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Count Bounds
class test_count_bounds extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_bounds)
  
  function new(string name = "test_count_bounds", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 500;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Count Transitions
class test_count_transitions extends synchronous_fifo_base_test;
  `uvm_component_utils(test_count_transitions)
  
  function new(string name = "test_count_transitions", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 500;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Simultaneous RW When Empty Sequence
class simul_rw_when_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(simul_rw_when_empty_seq)
  
  function new(string name = "simul_rw_when_empty_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Simultaneous R/W when empty
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Simultaneous RW When Empty
class test_simul_rw_when_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_simul_rw_when_empty)
  
  function new(string name = "test_simul_rw_when_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    simul_rw_when_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = simul_rw_when_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Simultaneous RW When Full Sequence
class simul_rw_when_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(simul_rw_when_full_seq)
  
  int depth;
  
  function new(string name = "simul_rw_when_full_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Simultaneous R/W when full
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Simultaneous RW When Full
class test_simul_rw_when_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_simul_rw_when_full)
  
  function new(string name = "test_simul_rw_when_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    simul_rw_when_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = simul_rw_when_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Simultaneous RW Normal State Sequence
class simul_rw_normal_state_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(simul_rw_normal_state_seq)
  
  int num_operations;
  
  function new(string name = "simul_rw_normal_state_seq");
    super.new(name);
    num_operations = 10;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write some entries to get to normal state
    for (int i = 0; i < 5; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Simultaneous R/W in normal state
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Simultaneous RW Normal State
class test_simul_rw_normal_state extends synchronous_fifo_base_test;
  `uvm_component_utils(test_simul_rw_normal_state)
  
  function new(string name = "test_simul_rw_normal_state", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    simul_rw_normal_state_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = simul_rw_normal_state_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Simultaneous RW Almost Empty Sequence
class simul_rw_almost_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(simul_rw_almost_empty_seq)
  
  function new(string name = "simul_rw_almost_empty_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write one entry to get to almost empty state
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Simultaneous R/W when almost empty
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Simultaneous RW Almost Empty
class test_simul_rw_almost_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_simul_rw_almost_empty)
  
  function new(string name = "test_simul_rw_almost_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    simul_rw_almost_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = simul_rw_almost_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Simultaneous RW Almost Full Sequence
class simul_rw_almost_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(simul_rw_almost_full_seq)
  
  int depth;
  
  function new(string name = "simul_rw_almost_full_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill to DEPTH-1 to get to almost full state
    for (int i = 0; i < depth-1; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Simultaneous R/W when almost full
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Simultaneous RW Almost Full
class test_simul_rw_almost_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_simul_rw_almost_full)
  
  function new(string name = "test_simul_rw_almost_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    simul_rw_almost_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = simul_rw_almost_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Random Simultaneous RW
class test_random_simul_rw extends synchronous_fifo_base_test;
  `uvm_component_utils(test_random_simul_rw)
  
  function new(string name = "test_random_simul_rw", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 300;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Write When Full Sequence
class write_when_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(write_when_full_seq)
  
  int depth;
  int num_attempts;
  
  function new(string name = "write_when_full_seq");
    super.new(name);
    depth = 16;
    num_attempts = 10;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Attempt writes when full
    for (int i = 0; i < num_attempts; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Write When Full
class test_write_when_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_write_when_full)
  
  function new(string name = "test_write_when_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    write_when_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = write_when_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Read When Empty Sequence
class read_when_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(read_when_empty_seq)
  
  int num_attempts;
  
  function new(string name = "read_when_empty_seq");
    super.new(name);
    num_attempts = 10;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Attempt reads when empty
    for (int i = 0; i < num_attempts; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Read When Empty
class test_read_when_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_read_when_empty)
  
  function new(string name = "test_read_when_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    read_when_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = read_when_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Single Entry Operation Sequence
class single_entry_operation_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(single_entry_operation_seq)
  
  function new(string name = "single_entry_operation_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write one entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Try write when almost empty
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read one entry
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Try read when almost empty
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Simultaneous R/W when almost empty
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Single Entry Operation
class test_single_entry_operation extends synchronous_fifo_base_test;
  `uvm_component_utils(test_single_entry_operation)
  
  function new(string name = "test_single_entry_operation", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    single_entry_operation_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = single_entry_operation_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Almost Full Boundary Sequence
class almost_full_boundary_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(almost_full_boundary_seq)
  
  int depth;
  
  function new(string name = "almost_full_boundary_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill to DEPTH-2
    for (int i = 0; i < depth-2; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Write one more to reach DEPTH-1
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Write one more to reach DEPTH
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read one to go back to DEPTH-1
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Read one more to go to DEPTH-2
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Almost Full Boundary
class test_almost_full_boundary extends synchronous_fifo_base_test;
  `uvm_component_utils(test_almost_full_boundary)
  
  function new(string name = "test_almost_full_boundary", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    almost_full_boundary_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = almost_full_boundary_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Almost Empty Boundary Sequence
class almost_empty_boundary_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(almost_empty_boundary_seq)
  
  function new(string name = "almost_empty_boundary_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write 2 entries
    for (int i = 0; i < 2; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Read one to reach count=1
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Read one more to reach count=0
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    // Write one to go back to count=1
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    // Write one more to go to count=2
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
  endtask
endclass

// Test Almost Empty Boundary
class test_almost_empty_boundary extends synchronous_fifo_base_test;
  `uvm_component_utils(test_almost_empty_boundary)
  
  function new(string name = "test_almost_empty_boundary", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    almost_empty_boundary_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = almost_empty_boundary_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Sustained Full Sequence
class sustained_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(sustained_full_seq)
  
  int depth;
  int num_cycles;
  
  function new(string name = "sustained_full_seq");
    super.new(name);
    depth = 16;
    num_cycles = 100;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Hold full and attempt writes
    for (int i = 0; i < num_cycles; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Sustained Full
class test_sustained_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_sustained_full)
  
  function new(string name = "test_sustained_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    sustained_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = sustained_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Sustained Empty Sequence
class sustained_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(sustained_empty_seq)
  
  int num_cycles;
  
  function new(string name = "sustained_empty_seq");
    super.new(name);
    num_cycles = 100;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Hold empty and attempt reads
    for (int i = 0; i < num_cycles; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Sustained Empty
class test_sustained_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_sustained_empty)
  
  function new(string name = "test_sustained_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    sustained_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = sustained_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Write Pointer Wraparound Sequence
class write_pointer_wraparound_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(write_pointer_wraparound_seq)
  
  int depth;
  
  function new(string name = "write_pointer_wraparound_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write DEPTH entries to cause wraparound
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Read all entries
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
    
    // Write one more to verify wraparound
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
  endtask
endclass

// Test Write Pointer Wraparound
class test_write_pointer_wraparound extends synchronous_fifo_base_test;
  `uvm_component_utils(test_write_pointer_wraparound)
  
  function new(string name = "test_write_pointer_wraparound", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    write_pointer_wraparound_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = write_pointer_wraparound_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Read Pointer Wraparound Sequence
class read_pointer_wraparound_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(read_pointer_wraparound_seq)
  
  int depth;
  
  function new(string name = "read_pointer_wraparound_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Read DEPTH entries to cause wraparound
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
    
    // Write and read one more to verify wraparound
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Read Pointer Wraparound
class test_read_pointer_wraparound extends synchronous_fifo_base_test;
  `uvm_component_utils(test_read_pointer_wraparound)
  
  function new(string name = "test_read_pointer_wraparound", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    read_pointer_wraparound_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = read_pointer_wraparound_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Pointer Collision Empty Sequence
class pointer_collision_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(pointer_collision_empty_seq)
  
  function new(string name = "pointer_collision_empty_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset, pointers equal)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Write and read to verify behavior
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
    
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
  endtask
endclass

// Test Pointer Collision Empty
class test_pointer_collision_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_pointer_collision_empty)
  
  function new(string name = "test_pointer_collision_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    pointer_collision_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = pointer_collision_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Pointer Collision Full Sequence
class pointer_collision_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(pointer_collision_full_seq)
  
  int depth;
  
  function new(string name = "pointer_collision_full_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO (pointers will be equal when full)
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Wait a cycle
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Read and write to verify behavior
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 1;
    });
    finish_item(req);
    
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 1;
      rd_en == 0;
    });
    finish_item(req);
  endtask
endclass

// Test Pointer Collision Full
class test_pointer_collision_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_pointer_collision_full)
  
  function new(string name = "test_pointer_collision_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    pointer_collision_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = pointer_collision_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Multiple Wraparounds Sequence
class multiple_wraparounds_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(multiple_wraparounds_seq)
  
  int depth;
  int num_cycles;
  
  function new(string name = "multiple_wraparounds_seq");
    super.new(name);
    depth = 16;
    num_cycles = 3;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int cycle = 0; cycle < num_cycles; cycle++) begin
      // Fill FIFO
      for (int i = 0; i < depth; i++) begin
        req = synchronous_fifo_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
          wr_en == 1;
          rd_en == 0;
        });
        finish_item(req);
      end
      
      // Empty FIFO
      for (int i = 0; i < depth; i++) begin
        req = synchronous_fifo_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
          wr_en == 0;
          rd_en == 1;
        });
        finish_item(req);
      end
    end
  endtask
endclass

// Test Multiple Wraparounds
class test_multiple_wraparounds extends synchronous_fifo_base_test;
  `uvm_component_utils(test_multiple_wraparounds)
  
  function new(string name = "test_multiple_wraparounds", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    multiple_wraparounds_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = multiple_wraparounds_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Pointer Bounds
class test_pointer_bounds extends synchronous_fifo_base_test;
  `uvm_component_utils(test_pointer_bounds)
  
  function new(string name = "test_pointer_bounds", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 500;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// FIFO Ordering Sequence
class fifo_ordering_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(fifo_ordering_seq)
  
  rand bit [31:0] test_data[16];
  int depth;
  
  function new(string name = "fifo_ordering_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Write known sequence
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
        wr_data == test_data[i];
      });
      finish_item(req);
    end
    
    // Read back sequence
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test FIFO Ordering
class test_fifo_ordering extends synchronous_fifo_base_test;
  `uvm_component_utils(test_fifo_ordering)
  
  function new(string name = "test_fifo_ordering", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    fifo_ordering_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = fifo_ordering_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Data Pattern Sequence
class data_pattern_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(data_pattern_seq)
  
  typedef enum {ALL_ZEROS, ALL_ONES, ALTERNATING_01, ALTERNATING_10, WALKING_ONES, WALKING_ZEROS} pattern_t;
  pattern_t pattern;
  int depth;
  int data_width;
  
  function new(string name = "data_pattern_seq");
    super.new(name);
    depth = 16;
    data_width = 32;
    pattern = ALL_ZEROS;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    bit [31:0] data;
    
    // Write pattern
    for (int i = 0; i < depth; i++) begin
      case (pattern)
        ALL_ZEROS: data = 32'h00000000;
        ALL_ONES: data = 32'hFFFFFFFF;
        ALTERNATING_01: data = 32'h55555555;
        ALTERNATING_10: data = 32'hAAAAAAAA;
        WALKING_ONES: data = 32'h00000001 << (i % data_width);
        WALKING_ZEROS: data = ~(32'h00000001 << (i % data_width));
      endcase
      
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
        wr_data == data;
      });
      finish_item(req);
    end
    
    // Read back pattern
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Data Pattern All Zeros
class test_data_pattern_all_zeros extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_pattern_all_zeros)
  
  function new(string name = "test_data_pattern_all_zeros", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_pattern_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_pattern_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.data_width = cfg.DATA_WIDTH;
    seq.pattern = data_pattern_seq::ALL_ZEROS;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Data Pattern All Ones
class test_data_pattern_all_ones extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_pattern_all_ones)
  
  function new(string name = "test_data_pattern_all_ones", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_pattern_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_pattern_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.data_width = cfg.DATA_WIDTH;
    seq.pattern = data_pattern_seq::ALL_ONES;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Data Pattern Alternating
class test_data_pattern_alternating extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_pattern_alternating)
  
  function new(string name = "test_data_pattern_alternating", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_pattern_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_pattern_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.data_width = cfg.DATA_WIDTH;
    seq.pattern = data_pattern_seq::ALTERNATING_01;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Data Pattern Walking Ones
class test_data_pattern_walking_ones extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_pattern_walking_ones)
  
  function new(string name = "test_data_pattern_walking_ones", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_pattern_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_pattern_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.data_width = cfg.DATA_WIDTH;
    seq.pattern = data_pattern_seq::WALKING_ONES;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Data Pattern Walking Zeros
class test_data_pattern_walking_zeros extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_pattern_walking_zeros)
  
  function new(string name = "test_data_pattern_walking_zeros", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_pattern_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_pattern_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.data_width = cfg.DATA_WIDTH;
    seq.pattern = data_pattern_seq::WALKING_ZEROS;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Random Data Integrity
class test_random_data_integrity extends synchronous_fifo_base_test;
  `uvm_component_utils(test_random_data_integrity)
  
  function new(string name = "test_random_data_integrity", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 500;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Data Across Wraparound Sequence
class data_across_wraparound_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(data_across_wraparound_seq)
  
  rand bit [31:0] test_data[32];
  int depth;
  
  function new(string name = "data_across_wraparound_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
        wr_data == test_data[i];
      });
      finish_item(req);
    end
    
    // Read half
    for (int i = 0; i < depth/2; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
    
    // Write more to cause wraparound
    for (int i = depth; i < depth + depth/2; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
        wr_data == test_data[i];
      });
      finish_item(req);
    end
    
    // Read all remaining
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Data Across Wraparound
class test_data_across_wraparound extends synchronous_fifo_base_test;
  `uvm_component_utils(test_data_across_wraparound)
  
  function new(string name = "test_data_across_wraparound", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    data_across_wraparound_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = data_across_wraparound_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Reset When Empty Sequence
class reset_when_empty_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(reset_when_empty_seq)
  
  function new(string name = "reset_when_empty_seq");
    super.new(name);
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Wait a cycle (FIFO is empty after reset)
    req = synchronous_fifo_transaction::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      wr_en == 0;
      rd_en == 0;
    });
    finish_item(req);
    
    // Perform some operations after reset
    for (int i = 0; i < 5; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Reset When Empty
class test_reset_when_empty extends synchronous_fifo_base_test;
  `uvm_component_utils(test_reset_when_empty)
  
  function new(string name = "test_reset_when_empty", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    reset_when_empty_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = reset_when_empty_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Reset When Full Sequence
class reset_when_full_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(reset_when_full_seq)
  
  int depth;
  
  function new(string name = "reset_when_full_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Reset When Full
class test_reset_when_full extends synchronous_fifo_base_test;
  `uvm_component_utils(test_reset_when_full)
  
  function new(string name = "test_reset_when_full", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    reset_when_full_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = reset_when_full_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    apply_reset();
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Back to Back Writes Sequence
class back_to_back_writes_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(back_to_back_writes_seq)
  
  int depth;
  
  function new(string name = "back_to_back_writes_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Consecutive writes
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Back to Back Writes
class test_back_to_back_writes extends synchronous_fifo_base_test;
  `uvm_component_utils(test_back_to_back_writes)
  
  function new(string name = "test_back_to_back_writes", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    back_to_back_writes_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = back_to_back_writes_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Back to Back Reads Sequence
class back_to_back_reads_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(back_to_back_reads_seq)
  
  int depth;
  
  function new(string name = "back_to_back_reads_seq");
    super.new(name);
    depth = 16;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    // Fill FIFO first
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
    end
    
    // Consecutive reads
    for (int i = 0; i < depth; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Back to Back Reads
class test_back_to_back_reads extends synchronous_fifo_base_test;
  `uvm_component_utils(test_back_to_back_reads)
  
  function new(string name = "test_back_to_back_reads", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    back_to_back_reads_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = back_to_back_reads_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Continuous Write Stream Sequence
class continuous_write_stream_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(continuous_write_stream_seq)
  
  int num_operations;
  
  function new(string name = "continuous_write_stream_seq");
    super.new(name);
    num_operations = 1000;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en dist {1 := 90, 0 := 10};
        rd_en dist {1 := 20, 0 := 80};
      });
      finish_item(req);
    end
  endtask
endclass

// Test Continuous Write Stream
class test_continuous_write_stream extends synchronous_fifo_base_test;
  `uvm_component_utils(test_continuous_write_stream)
  
  function new(string name = "test_continuous_write_stream", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    continuous_write_stream_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = continuous_write_stream_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Continuous Read Stream Sequence
class continuous_read_stream_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(continuous_read_stream_seq)
  
  int num_operations;
  
  function new(string name = "continuous_read_stream_seq");
    super.new(name);
    num_operations = 1000;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en dist {1 := 20, 0 := 80};
        rd_en dist {1 := 90, 0 := 10};
      });
      finish_item(req);
    end
  endtask
endclass

// Test Continuous Read Stream
class test_continuous_read_stream extends synchronous_fifo_base_test;
  `uvm_component_utils(test_continuous_read_stream)
  
  function new(string name = "test_continuous_read_stream", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    continuous_read_stream_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = continuous_read_stream_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Alternating Single RW Sequence
class alternating_single_rw_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(alternating_single_rw_seq)
  
  int num_cycles;
  
  function new(string name = "alternating_single_rw_seq");
    super.new(name);
    num_cycles = 50;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_cycles; i++) begin
      // Write
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 1;
        rd_en == 0;
      });
      finish_item(req);
      
      // Read
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        wr_en == 0;
        rd_en == 1;
      });
      finish_item(req);
    end
  endtask
endclass

// Test Alternating Single RW
class test_alternating_single_rw extends synchronous_fifo_base_test;
  `uvm_component_utils(test_alternating_single_rw)
  
  function new(string name = "test_alternating_single_rw", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    alternating_single_rw_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = alternating_single_rw_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Random Operations Short
class test_random_operations_short extends synchronous_fifo_base_test;
  `uvm_component_utils(test_random_operations_short)
  
  function new(string name = "test_random_operations_short", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 1000;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Random Operations Long
class test_random_operations_long extends synchronous_fifo_base_test;
  `uvm_component_utils(test_random_operations_long)
  
  function new(string name = "test_random_operations_long", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 10000;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Rapid Fill Empty Cycles Sequence
class rapid_fill_empty_cycles_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(rapid_fill_empty_cycles_seq)
  
  int depth;
  int num_cycles;
  
  function new(string name = "rapid_fill_empty_cycles_seq");
    super.new(name);
    depth = 16;
    num_cycles = 10;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int cycle = 0; cycle < num_cycles; cycle++) begin
      // Fill
      for (int i = 0; i < depth; i++) begin
        req = synchronous_fifo_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
          wr_en == 1;
          rd_en == 0;
        });
        finish_item(req);
      end
      
      // Empty
      for (int i = 0; i < depth; i++) begin
        req = synchronous_fifo_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
          wr_en == 0;
          rd_en == 1;
        });
        finish_item(req);
      end
    end
  endtask
endclass

// Test Rapid Fill Empty Cycles
class test_rapid_fill_empty_cycles extends synchronous_fifo_base_test;
  `uvm_component_utils(test_rapid_fill_empty_cycles)
  
  function new(string name = "test_rapid_fill_empty_cycles", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    rapid_fill_empty_cycles_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = rapid_fill_empty_cycles_seq::type_id::create("seq");
    seq.depth = cfg.DEPTH;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Random Simultaneous RW Heavy Sequence
class random_simul_rw_heavy_seq extends synchronous_fifo_base_seq;
  `uvm_object_utils(random_simul_rw_heavy_seq)
  
  int num_operations;
  
  function new(string name = "random_simul_rw_heavy_seq");
    super.new(name);
    num_operations = 500;
  endfunction
  
  virtual task body();
    synchronous_fifo_transaction req;
    
    for (int i = 0; i < num_operations; i++) begin
      req = synchronous_fifo_transaction::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        (wr_en && rd_en) dist {1 := 60, 0 := 40};
      });
      finish_item(req);
    end
  endtask
endclass

// Test Random Simultaneous RW Heavy
class test_random_simul_rw_heavy extends synchronous_fifo_base_test;
  `uvm_component_utils(test_random_simul_rw_heavy)
  
  function new(string name = "test_random_simul_rw_heavy", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_simul_rw_heavy_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_simul_rw_heavy_seq::type_id::create("seq");
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass

// Test Corner Case Stress
class test_corner_case_stress extends synchronous_fifo_base_test;
  `uvm_component_utils(test_corner_case_stress)
  
  function new(string name = "test_corner_case_stress", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  
  virtual task run_phase(uvm_phase phase);
    random_operations_seq seq;
    phase.raise_objection(this);
    apply_reset();
    seq = random_operations_seq::type_id::create("seq");
    seq.num_operations = 1000;
    seq.start(env.agent.sequencer);
    #100;
    phase.drop_objection(this);
  endtask
endclass