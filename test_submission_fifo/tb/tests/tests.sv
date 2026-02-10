I'll generate comprehensive UVM test classes for the sync_fifo design based on the verification plan. Here's the complete SystemVerilog code:

```systemverilog
//==============================================================================
// Base Test Class
//==============================================================================
class sync_fifo_base_test extends uvm_test;
    `uvm_component_utils(sync_fifo_base_test)
    
    // Environment and configuration
    sync_fifo_env env;
    sync_fifo_config cfg;
    
    function new(string name = "sync_fifo_base_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        // Create configuration
        cfg = sync_fifo_config::type_id::create("cfg");
        if (!uvm_config_db#(virtual sync_fifo_if)::get(this, "", "vif", cfg.vif))
            `uvm_fatal("CONFIG", "Cannot get virtual interface from config DB")
        
        // Configure parameters
        if (!$value$plusargs("DEPTH=%d", cfg.depth))
            cfg.depth = 16; // Default depth
        if (!$value$plusargs("DATA_WIDTH=%d", cfg.data_width))
            cfg.data_width = 32; // Default data width
            
        uvm_config_db#(sync_fifo_config)::set(this, "*", "cfg", cfg);
        
        // Create environment
        env = sync_fifo_env::type_id::create("env", this);
    endfunction
    
    virtual function void end_of_elaboration_phase(uvm_phase phase);
        super.end_of_elaboration_phase(phase);
        uvm_top.print_topology();
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        `uvm_info("TEST", $sformatf("Starting %s", get_name()), UVM_LOW)
        
        // Wait for reset deassertion
        wait(cfg.vif.rst_n === 1'b1);
        repeat(5) @(posedge cfg.vif.clk);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Basic Functionality Tests
//==============================================================================

// Test Reset
class test_reset extends sync_fifo_base_test;
    `uvm_component_utils(test_reset)
    
    function new(string name = "test_reset", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        reset_sequence seq;
        
        phase.raise_objection(this);
        `uvm_info("TEST", "Starting reset test", UVM_LOW)
        
        seq = reset_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Single Write Read
class test_single_write_read extends sync_fifo_base_test;
    `uvm_component_utils(test_single_write_read)
    
    function new(string name = "test_single_write_read", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        single_write_read_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = single_write_read_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Basic FIFO Order
class test_basic_fifo_order extends sync_fifo_base_test;
    `uvm_component_utils(test_basic_fifo_order)
    
    function new(string name = "test_basic_fifo_order", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        basic_fifo_order_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = basic_fifo_order_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Empty Flag
class test_empty_flag extends sync_fifo_base_test;
    `uvm_component_utils(test_empty_flag)
    
    function new(string name = "test_empty_flag", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        empty_flag_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = empty_flag_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Full Flag
class test_full_flag extends sync_fifo_base_test;
    `uvm_component_utils(test_full_flag)
    
    function new(string name = "test_full_flag", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        full_flag_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = full_flag_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Status Flags Tests
//==============================================================================

// Test Almost Full Threshold
class test_almost_full_threshold extends sync_fifo_base_test;
    `uvm_component_utils(test_almost_full_threshold)
    
    function new(string name = "test_almost_full_threshold", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        almost_full_threshold_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = almost_full_threshold_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Almost Empty Threshold
class test_almost_empty_threshold extends sync_fifo_base_test;
    `uvm_component_utils(test_almost_empty_threshold)
    
    function new(string name = "test_almost_empty_threshold", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        almost_empty_threshold_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = almost_empty_threshold_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Count Accuracy
class test_count_accuracy extends sync_fifo_base_test;
    `uvm_component_utils(test_count_accuracy)
    
    function new(string name = "test_count_accuracy", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        count_accuracy_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = count_accuracy_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Flag Transitions
class test_flag_transitions extends sync_fifo_base_test;
    `uvm_component_utils(test_flag_transitions)
    
    function new(string name = "test_flag_transitions", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        flag_transitions_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = flag_transitions_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Conflicting Flags
class test_conflicting_flags extends sync_fifo_base_test;
    `uvm_component_utils(test_conflicting_flags)
    
    function new(string name = "test_conflicting_flags", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        conflicting_flags_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = conflicting_flags_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Error Conditions Tests
//==============================================================================

// Test Overflow
class test_overflow extends sync_fifo_base_test;
    `uvm_component_utils(test_overflow)
    
    function new(string name = "test_overflow", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        overflow_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = overflow_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Underflow
class test_underflow extends sync_fifo_base_test;
    `uvm_component_utils(test_underflow)
    
    function new(string name = "test_underflow", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        underflow_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = underflow_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Error Sticky
class test_error_sticky extends sync_fifo_base_test;
    `uvm_component_utils(test_error_sticky)
    
    function new(string name = "test_error_sticky", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        error_sticky_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = error_sticky_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Error Reset Only
class test_error_reset_only extends sync_fifo_base_test;
    `uvm_component_utils(test_error_reset_only)
    
    function new(string name = "test_error_reset_only", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        error_reset_only_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = error_reset_only_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Simultaneous Operations Tests
//==============================================================================

// Test Simultaneous R/W Full
class test_simul_rw_full extends sync_fifo_base_test;
    `uvm_component_utils(test_simul_rw_full)
    
    function new(string name = "test_simul_rw_full", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        simul_rw_full_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = simul_rw_full_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Simultaneous R/W Empty
class test_simul_rw_empty extends sync_fifo_base_test;
    `uvm_component_utils(test_simul_rw_empty)
    
    function new(string name = "test_simul_rw_empty", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        simul_rw_empty_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = simul_rw_empty_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Simultaneous R/W Normal
class test_simul_rw_normal extends sync_fifo_base_test;
    `uvm_component_utils(test_simul_rw_normal)
    
    function new(string name = "test_simul_rw_normal", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        simul_rw_normal_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = simul_rw_normal_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Back to Back Operations
class test_back_to_back_ops extends sync_fifo_base_test;
    `uvm_component_utils(test_back_to_back_ops)
    
    function new(string name = "test_back_to_back_ops", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        back_to_back_ops_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = back_to_back_ops_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Boundary Conditions Tests
//==============================================================================

// Test Pointer Wraparound
class test_pointer_wraparound extends sync_fifo_base_test;
    `uvm_component_utils(test_pointer_wraparound)
    
    function new(string name = "test_pointer_wraparound", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        pointer_wraparound_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = pointer_wraparound_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Threshold Boundaries
class test_threshold_boundaries extends sync_fifo_base_test;
    `uvm_component_utils(test_threshold_boundaries)
    
    function new(string name = "test_threshold_boundaries", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        threshold_boundaries_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = threshold_boundaries_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Max Min Data
class test_max_min_data extends sync_fifo_base_test;
    `uvm_component_utils(test_max_min_data)
    
    function new(string name = "test_max_min_data", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        max_min_data_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = max_min_data_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Rapid Fill Empty
class test_rapid_fill_empty extends sync_fifo_base_test;
    `uvm_component_utils(test_rapid_fill_empty)
    
    function new(string name = "test_rapid_fill_empty", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        rapid_fill_empty_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = rapid_fill_empty_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Timing and Reset Tests
//==============================================================================

// Test Reset During Write
class test_reset_during_write extends sync_fifo_base_test;
    `uvm_component_utils(test_reset_during_write)
    
    function new(string name = "test_reset_during_write", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        reset_during_write_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = reset_during_write_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Reset During Read
class test_reset_during_read extends sync_fifo_base_test;
    `uvm_component_utils(test_reset_during_read)
    
    function new(string name = "test_reset_during_read", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        reset_during_read_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = reset_during_read_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Reset Timing
class test_reset_timing extends sync_fifo_base_test;
    `uvm_component_utils(test_reset_timing)
    
    function new(string name = "test_reset_timing", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        reset_timing_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = reset_timing_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Combinational Read
class test_combinational_read extends sync_fifo_base_test;
    `uvm_component_utils(test_combinational_read)
    
    function new(string name = "test_combinational_read", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        combinational_read_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = combinational_read_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Parameterization Tests
//==============================================================================

// Test Min Depth
class test_min_depth extends sync_fifo_base_test;
    `uvm_component_utils(test_min_depth)
    
    function new(string name = "test_min_depth", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        cfg.depth = 1; // Override to minimum depth
        uvm_config_db#(sync_fifo_config)::set(this, "*", "cfg", cfg);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        min_depth_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = min_depth_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Power of 2 Depths
class test_power_of_2_depths extends sync_fifo_base_test;
    `uvm_component_utils(test_power_of_2_depths)
    
    function new(string name = "test_power_of_2_depths", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        power_of_2_depths_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = power_of_2_depths_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Non-Power of 2 Depths
class test_non_power_of_2_depths extends sync_fifo_base_test;
    `uvm_component_utils(test_non_power_of_2_depths)
    
    function new(string name = "test_non_power_of_2_depths", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        non_power_of_2_depths_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = non_power_of_2_depths_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Various Data Widths
class test_various_data_widths extends sync_fifo_base_test;
    `uvm_component_utils(test_various_data_widths)
    
    function new(string name = "test_various_data_widths", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        various_data_widths_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = various_data_widths_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Stress Testing Tests
//==============================================================================

// Test Random Operations
class test_random_operations extends sync_fifo_base_test;
    `uvm_component_utils(test_random_operations)
    
    function new(string name = "test_random_operations", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        random_operations_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = random_operations_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Burst Operations
class test_burst_operations extends sync_fifo_base_test;
    `uvm_component_utils(test_burst_operations)
    
    function new(string name = "test_burst_operations", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        burst_operations_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = burst_operations_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Mixed Patterns
class test_mixed_patterns extends sync_fifo_base_test;
    `uvm_component_utils(test_mixed_patterns)
    
    function new(string name = "test_mixed_patterns", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        mixed_patterns_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = mixed_patterns_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

// Test Long Sequences
class test_long_sequences extends sync_fifo_base_test;
    `uvm_component_utils(test_long_sequences)
    
    function new(string name = "test_long_sequences", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        long_sequences_sequence seq;
        
        phase.raise_objection(this);
        super.run_phase(phase);
        
        seq = long_sequences_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
endclass

//==============================================================================
// Sequence Definitions
//==============================================================================

// Reset Sequence
class reset_sequence extends uvm_sequence#(sync_fifo_transaction);
    `uvm_object_utils(reset_sequence)
    
    function new(string name = "reset_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_transaction req;
        
        `uvm_info("SEQ", "Starting reset sequence", UVM_LOW)
        
        // Apply reset
        req = sync_fifo_transaction::type_id::create("req");
        start_item(req);
        req.reset = 1;
        req.wr_en = 0;
        req.rd_en = 0;
        finish_item(req);
        
        repeat(5) begin
            req = sync_fifo_transaction::type_id::create("req");
            start_item(req);
            req.reset = 1;
            req.wr_en = 0;
            req.rd_en = 0;
            finish_item(req);
        end
        
        // Release reset
        req = sync_fifo_transaction::type_id::create("req");
        start_item(req);
        req.reset = 0;
        req.wr_en = 0;
        req.rd_en = 0;
        finish_item(req);
        
        // Wait a few cycles
        repeat(3) begin
            req = sync_fifo_transaction::type_id::create("req");
            start_item(req);
            req.reset = 0;
            req.wr_en = 0;
            req.rd_en = 0;
            finish_item(req);
        end
        
        `uvm_info("SEQ", "Reset sequence completed", UVM_LOW)
    endtask
endclass

// Single Write Read Sequence
class single_write_read_sequence extends uvm_sequence#(sync_fifo_transaction);
    `uvm_object_utils(single_write_read_sequence)
    
    function new(string name = "single_write_read_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_transaction req;
        bit [31:0] test_data = 32'hDEADBEEF;
        
        `uvm_info("SEQ", "Starting single write read sequence", UVM_LOW)
        
        // Single write
        req = sync_fifo_transaction::type_id::create("req");
        start_item(req);
        req.reset = 0;
        req.wr_en = 1;
        req.rd_en = 0;
        req.wr_data = test_data;
        finish_item(req);
        
        // Wait cycle
        req = sync_fifo_transaction::type_id::create("req");
        start_item(req);
        req.reset = 0;
        req.wr_en = 0;
        req.rd_en = 0;
        finish_item(req);
        
        // Single read
        req = sync_fifo_transaction::type_id::create("req");
        start_item(req);
        req.reset = 0;
        req.wr_en = 0;
        req.rd_en = 1;
        finish_item(req);
        
        `uvm_info("SEQ", "Single write read sequence completed", UVM_LOW)
    endtask
endclass

// Basic FIFO Order Sequence
class basic_fifo_order_sequence extends uvm_sequence#(sync_fifo_transaction);
    `uvm_object_utils(basic_fifo_order_sequence)
    
    function new(string name = "basic_fifo_order_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_transaction req;
        bit [31:0] test_data[4] = '{32'h11111111, 32'