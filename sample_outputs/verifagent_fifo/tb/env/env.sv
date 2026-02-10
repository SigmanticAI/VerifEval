// Auto-added UVM imports
import uvm_pkg::*;
`include "uvm_macros.svh"

I'll generate a complete UVM environment for the sync_fifo design. Here's the SystemVerilog code:

## 1. sync_fifo_if.sv - Interface
```systemverilog
interface sync_fifo_if #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH)
)(
    input logic clk,
    input logic rst_n
);

    // Write interface signals
    logic wr_en;
    logic [DATA_WIDTH-1:0] wr_data;
    
    // Read interface signals
    logic rd_en;
    logic [DATA_WIDTH-1:0] rd_data;
    
    // Status interface signals
    logic full;
    logic empty;
    logic almost_full;
    logic almost_empty;
    logic [ADDR_WIDTH:0] count;
    logic error;

    // Clocking blocks for driver and monitor
    clocking driver_cb @(posedge clk);
        default input #1step output #1step;
        output wr_en, wr_data, rd_en;
        input rd_data, full, empty, almost_full, almost_empty, count, error;
    endclocking

    clocking monitor_cb @(posedge clk);
        default input #1step;
        input wr_en, wr_data, rd_en, rd_data, full, empty, almost_full, almost_empty, count, error;
    endclocking

    // Modports
    modport driver_mp(clocking driver_cb, input rst_n);
    modport monitor_mp(clocking monitor_cb, input rst_n);
    modport dut_mp(input wr_en, wr_data, rd_en, output rd_data, full, empty, almost_full, almost_empty, count, error);

endinterface
```

## 2. sync_fifo_transaction.sv - Transaction Class
```systemverilog
class sync_fifo_transaction #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_sequence_item;
    
    // Transaction fields
    rand bit wr_en;
    rand bit rd_en;
    rand bit [DATA_WIDTH-1:0] wr_data;
    
    // Response fields
    bit [DATA_WIDTH-1:0] rd_data;
    bit full;
    bit empty;
    bit almost_full;
    bit almost_empty;
    bit [ADDR_WIDTH:0] count;
    bit error;
    
    // Transaction type
    typedef enum {WRITE, READ, WRITE_READ, IDLE} trans_type_e;
    rand trans_type_e trans_type;
    
    // Constraints
    constraint c_trans_type {
        trans_type dist {
            WRITE := 30,
            READ := 30,
            WRITE_READ := 20,
            IDLE := 20
        };
    }
    
    constraint c_enables {
        if (trans_type == WRITE) {
            wr_en == 1'b1;
            rd_en == 1'b0;
        }
        else if (trans_type == READ) {
            wr_en == 1'b0;
            rd_en == 1'b1;
        }
        else if (trans_type == WRITE_READ) {
            wr_en == 1'b1;
            rd_en == 1'b1;
        }
        else { // IDLE
            wr_en == 1'b0;
            rd_en == 1'b0;
        }
    }
    
    `uvm_object_param_utils_begin(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH))
        `uvm_field_int(wr_en, UVM_ALL_ON)
        `uvm_field_int(rd_en, UVM_ALL_ON)
        `uvm_field_int(wr_data, UVM_ALL_ON)
        `uvm_field_int(rd_data, UVM_ALL_ON)
        `uvm_field_int(full, UVM_ALL_ON)
        `uvm_field_int(empty, UVM_ALL_ON)
        `uvm_field_int(almost_full, UVM_ALL_ON)
        `uvm_field_int(almost_empty, UVM_ALL_ON)
        `uvm_field_int(count, UVM_ALL_ON)
        `uvm_field_int(error, UVM_ALL_ON)
        `uvm_field_enum(trans_type_e, trans_type, UVM_ALL_ON)
    `uvm_object_utils_end
    
    function new(string name = "sync_fifo_transaction");
        super.new(name);
    endfunction
    
endclass
```

## 3. sync_fifo_driver.sv - Driver Class
```systemverilog
class sync_fifo_driver #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_driver #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH));
    
    virtual sync_fifo_if #(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH) vif;
    
    `uvm_component_param_utils(sync_fifo_driver #(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual sync_fifo_if #(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH))::get(this, "", "vif", vif)) begin
            `uvm_fatal("DRIVER", "Virtual interface not found")
        end
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans;
        
        // Initialize signals
        vif.driver_cb.wr_en <= 1'b0;
        vif.driver_cb.rd_en <= 1'b0;
        vif.driver_cb.wr_data <= '0;
        
        // Wait for reset deassertion
        wait(vif.rst_n);
        @(vif.driver_cb);
        
        forever begin
            seq_item_port.get_next_item(trans);
            drive_transaction(trans);
            seq_item_port.item_done();
        end
    endtask
    
    virtual task drive_transaction(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans);
        @(vif.driver_cb);
        vif.driver_cb.wr_en <= trans.wr_en;
        vif.driver_cb.rd_en <= trans.rd_en;
        vif.driver_cb.wr_data <= trans.wr_data;
        
        `uvm_info("DRIVER", $sformatf("Driving: wr_en=%0b, rd_en=%0b, wr_data=0x%0h", 
                  trans.wr_en, trans.rd_en, trans.wr_data), UVM_HIGH)
    endtask
    
endclass
```

## 4. sync_fifo_monitor.sv - Monitor Class
```systemverilog
class sync_fifo_monitor #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_monitor;
    
    virtual sync_fifo_if #(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH) vif;
    uvm_analysis_port #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH)) ap;
    
    `uvm_component_param_utils(sync_fifo_monitor #(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_monitor", uvm_component parent = null);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual sync_fifo_if #(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH))::get(this, "", "vif", vif)) begin
            `uvm_fatal("MONITOR", "Virtual interface not found")
        end
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans;
        
        wait(vif.rst_n);
        
        forever begin
            @(vif.monitor_cb);
            trans = sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH)::type_id::create("trans");
            
            // Capture all signals
            trans.wr_en = vif.monitor_cb.wr_en;
            trans.rd_en = vif.monitor_cb.rd_en;
            trans.wr_data = vif.monitor_cb.wr_data;
            trans.rd_data = vif.monitor_cb.rd_data;
            trans.full = vif.monitor_cb.full;
            trans.empty = vif.monitor_cb.empty;
            trans.almost_full = vif.monitor_cb.almost_full;
            trans.almost_empty = vif.monitor_cb.almost_empty;
            trans.count = vif.monitor_cb.count;
            trans.error = vif.monitor_cb.error;
            
            // Determine transaction type
            if (trans.wr_en && trans.rd_en)
                trans.trans_type = sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::WRITE_READ;
            else if (trans.wr_en)
                trans.trans_type = sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::WRITE;
            else if (trans.rd_en)
                trans.trans_type = sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::READ;
            else
                trans.trans_type = sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::IDLE;
            
            ap.write(trans);
            
            `uvm_info("MONITOR", $sformatf("Monitored: wr_en=%0b, rd_en=%0b, wr_data=0x%0h, rd_data=0x%0h, count=%0d, full=%0b, empty=%0b, error=%0b", 
                      trans.wr_en, trans.rd_en, trans.wr_data, trans.rd_data, trans.count, trans.full, trans.empty, trans.error), UVM_HIGH)
        end
    endtask
    
endclass
```

## 5. sync_fifo_agent.sv - Agent Class
```systemverilog
class sync_fifo_agent #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_agent;
    
    sync_fifo_driver #(DATA_WIDTH, ADDR_WIDTH) driver;
    sync_fifo_monitor #(DATA_WIDTH, ADDR_WIDTH) monitor;
    uvm_sequencer #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH)) sequencer;
    
    `uvm_component_param_utils(sync_fifo_agent #(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        monitor = sync_fifo_monitor #(DATA_WIDTH, ADDR_WIDTH)::type_id::create("monitor", this);
        
        if (get_is_active() == UVM_ACTIVE) begin
            driver = sync_fifo_driver #(DATA_WIDTH, ADDR_WIDTH)::type_id::create("driver", this);
            sequencer = uvm_sequencer #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH))::type_id::create("sequencer", this);
        end
    endfunction
    
    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        if (get_is_active() == UVM_ACTIVE) begin
            driver.seq_item_port.connect(sequencer.seq_item_export);
        end
    endfunction
    
endclass
```

## 6. sync_fifo_scoreboard.sv - Scoreboard Class
```systemverilog
class sync_fifo_scoreboard #(parameter DATA_WIDTH = 8, parameter DEPTH = 16, parameter ADDR_WIDTH = 4) extends uvm_scoreboard;
    
    uvm_analysis_imp #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH), sync_fifo_scoreboard #(DATA_WIDTH, DEPTH, ADDR_WIDTH)) ap_imp;
    
    // Reference model
    bit [DATA_WIDTH-1:0] ref_memory [$];
    int ref_count;
    bit ref_full, ref_empty, ref_almost_full, ref_almost_empty;
    bit ref_error;
    
    // Thresholds
    int ALMOST_FULL_THRESHOLD;
    int ALMOST_EMPTY_THRESHOLD;
    
    // Statistics
    int write_count, read_count, error_count;
    
    `uvm_component_param_utils(sync_fifo_scoreboard #(DATA_WIDTH, DEPTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_scoreboard", uvm_component parent = null);
        super.new(name, parent);
        ap_imp = new("ap_imp", this);
        
        // Calculate thresholds
        ALMOST_FULL_THRESHOLD = (3 * DEPTH) / 4;
        ALMOST_EMPTY_THRESHOLD = DEPTH / 4;
        
        // Initialize reference model
        ref_count = 0;
        ref_error = 0;
        update_flags();
    endfunction
    
    virtual function void write(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans);
        // Update reference model
        update_reference_model(trans);
        
        // Check against DUT
        check_transaction(trans);
    endfunction
    
    virtual function void update_reference_model(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans);
        bit write_op = trans.wr_en && !ref_full;
        bit read_op = trans.rd_en && !ref_empty;
        bit overflow = trans.wr_en && ref_full && !trans.rd_en;
        bit underflow = trans.rd_en && ref_empty && !trans.wr_en;
        
        // Handle simultaneous operations
        if (trans.wr_en && trans.rd_en) begin
            if (!ref_empty && !ref_full) begin
                // Normal simultaneous operation
                ref_memory.push_back(trans.wr_data);
                void'(ref_memory.pop_front());
            end else if (ref_empty) begin
                // Write to empty FIFO with simultaneous read
                ref_memory.push_back(trans.wr_data);
                ref_count++;
            end else if (ref_full) begin
                // Read from full FIFO with simultaneous write
                void'(ref_memory.pop_front());
                ref_memory.push_back(trans.wr_data);
            end
        end else begin
            // Single operations
            if (write_op) begin
                ref_memory.push_back(trans.wr_data);
                ref_count++;
                write_count++;
            end
            
            if (read_op) begin
                void'(ref_memory.pop_front());
                ref_count--;
                read_count++;
            end
        end
        
        // Update error flag (sticky)
        if (overflow || underflow) begin
            ref_error = 1;
            error_count++;
        end
        
        // Update count
        ref_count = ref_memory.size();
        
        // Update flags
        update_flags();
    endfunction
    
    virtual function void update_flags();
        ref_empty = (ref_count == 0);
        ref_full = (ref_count == DEPTH);
        ref_almost_empty = (ref_count <= ALMOST_EMPTY_THRESHOLD);
        ref_almost_full = (ref_count >= ALMOST_FULL_THRESHOLD);
    endfunction
    
    virtual function void check_transaction(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans);
        // Check count
        if (trans.count != ref_count) begin
            `uvm_error("SCB", $sformatf("Count mismatch: Expected=%0d, Actual=%0d", ref_count, trans.count))
        end
        
        // Check flags
        if (trans.empty != ref_empty) begin
            `uvm_error("SCB", $sformatf("Empty flag mismatch: Expected=%0b, Actual=%0b", ref_empty, trans.empty))
        end
        
        if (trans.full != ref_full) begin
            `uvm_error("SCB", $sformatf("Full flag mismatch: Expected=%0b, Actual=%0b", ref_full, trans.full))
        end
        
        if (trans.almost_empty != ref_almost_empty) begin
            `uvm_error("SCB", $sformatf("Almost empty flag mismatch: Expected=%0b, Actual=%0b", ref_almost_empty, trans.almost_empty))
        end
        
        if (trans.almost_full != ref_almost_full) begin
            `uvm_error("SCB", $sformatf("Almost full flag mismatch: Expected=%0b, Actual=%0b", ref_almost_full, trans.almost_full))
        end
        
        if (trans.error != ref_error) begin
            `uvm_error("SCB", $sformatf("Error flag mismatch: Expected=%0b, Actual=%0b", ref_error, trans.error))
        end
        
        // Check read data
        if (trans.rd_en && !ref_empty && ref_memory.size() > 0) begin
            bit [DATA_WIDTH-1:0] expected_data = ref_memory[0];
            if (trans.rd_data != expected_data) begin
                `uvm_error("SCB", $sformatf("Read data mismatch: Expected=0x%0h, Actual=0x%0h", expected_data, trans.rd_data))
            end
        end
        
        // Check for conflicting flags
        if (trans.full && trans.empty) begin
            `uvm_error("SCB", "Conflicting flags: Both full and empty are asserted")
        end
        
        // Check count bounds
        if (trans.count > DEPTH) begin
            `uvm_error("SCB", $sformatf("Count exceeds DEPTH: count=%0d, DEPTH=%0d", trans.count, DEPTH))
        end
    endfunction
    
    virtual function void report_phase(uvm_phase phase);
        super.report_phase(phase);
        `uvm_info("SCB", $sformatf("Scoreboard Statistics:"), UVM_LOW)
        `uvm_info("SCB", $sformatf("  Writes: %0d", write_count), UVM_LOW)
        `uvm_info("SCB", $sformatf("  Reads: %0d", read_count), UVM_LOW)
        `uvm_info("SCB", $sformatf("  Errors: %0d", error_count), UVM_LOW)
        `uvm_info("SCB", $sformatf("  Final Count: %0d", ref_count), UVM_LOW)
    endfunction
    
endclass
```

## 7. sync_fifo_coverage.sv - Coverage Collector
```systemverilog
class sync_fifo_coverage #(parameter DATA_WIDTH = 8, parameter DEPTH = 16, parameter ADDR_WIDTH = 4) extends uvm_subscriber #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH));
    
    sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) trans;
    
    // Coverage groups
    covergroup fifo_operations_cg;
        option.per_instance = 1;
        
        wr_en_cp: coverpoint trans.wr_en {
            bins write_enabled = {1};
            bins write_disabled = {0};
        }
        
        rd_en_cp: coverpoint trans.rd_en {
            bins read_enabled = {1};
            bins read_disabled = {0};
        }
        
        operation_type_cp: coverpoint trans.trans_type {
            bins write_only = {sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::WRITE};
            bins read_only = {sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::READ};
            bins write_read = {sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::WRITE_READ};
            bins idle = {sync_fifo_transaction#(DATA_WIDTH, ADDR_WIDTH)::IDLE};
        }
        
        wr_rd_cross: cross wr_en_cp, rd_en_cp {
            bins simultaneous_wr_rd = binsof(wr_en_cp.write_enabled) && binsof(rd_en_cp.read_enabled);
            bins write_only = binsof(wr_en_cp.write_enabled) && binsof(rd_en_cp.read_disabled);
            bins read_only = binsof(wr_en_cp.write_disabled) && binsof(rd_en_cp.read_enabled);
            bins idle = binsof(wr_en_cp.write_disabled) && binsof(rd_en_cp.read_disabled);
        }
    endgroup
    
    covergroup fifo_status_cg;
        option.per_instance = 1;
        
        count_cp: coverpoint trans.count {
            bins empty = {0};
            bins low = {[1:DEPTH/4]};
            bins medium = {[DEPTH/4+1:3*DEPTH/4-1]};
            bins high = {[3*DEPTH/4:DEPTH-1]};
            bins full = {DEPTH};
        }
        
        flags_cp: coverpoint {trans.full, trans.empty, trans.almost_full, trans.almost_empty} {
            bins empty_state = {4'b0101};  // empty=1, almost_empty=1
            bins low_state = {4'b0001};    // almost_empty=1
            bins normal_state = {4'b0000}; // no flags
            bins high_state = {4'b0010};   // almost_full=1
            bins full_state = {4'b1010};   // full=1, almost_full=1
            illegal_bins conflicting = {4'b11??}; // full and empty together
        }
        
        error_cp: coverpoint trans.error {
            bins no_error = {0};
            bins error_occurred = {1};
        }
    endgroup
    
    covergroup fifo_data_cg;
        option.per_instance = 1;
        
        wr_data_cp: coverpoint trans.wr_data {
            bins zero = {0};
            bins all_ones = {{DATA_WIDTH{1'b1}}};
            bins low_values = {[1:255]} iff (DATA_WIDTH >= 8);
            bins high_values = {[256:511]} iff (DATA_WIDTH >= 9);
        }
        
        rd_data_cp: coverpoint trans.rd_data {
            bins zero = {0};
            bins all_ones = {{DATA_WIDTH{1'b1}}};
            bins low_values = {[1:255]} iff (DATA_WIDTH >= 8);
            bins high_values = {[256:511]} iff (DATA_WIDTH >= 9);
        }
    endgroup
    
    covergroup fifo_transitions_cg;
        option.per_instance = 1;
        
        count_transitions_cp: coverpoint trans.count {
            bins empty_to_one = (0 => 1);
            bins one_to_empty = (1 => 0);
            bins almost_empty_boundary = (DEPTH/4 => DEPTH/4+1), (DEPTH/4+1 => DEPTH/4);
            bins almost_full_boundary = (3*DEPTH/4-1 => 3*DEPTH/4), (3*DEPTH/4 => 3*DEPTH/4-1);
            bins full_to_almost_full = (DEPTH => DEPTH-1);
            bins almost_full_to_full = (DEPTH-1 => DEPTH);
        }
        
        flag_transitions_cp: coverpoint {trans.full, trans.empty} {
            bins empty_to_not_empty = (2'b01 => 2'b00);
            bins not_empty_to_empty = (2'b00 => 2'b01);
            bins not_full_to_full = (2'b00 => 2'b10);
            bins full_to_not_full = (2'b10 => 2'b00);
        }
    endgroup
    
    covergroup corner_cases_cg;
        option.per_instance = 1;
        
        // Corner case: Write to full FIFO
        write_to_full_cp: coverpoint {trans.wr_en, trans.full, trans.rd_en} {
            bins overflow_attempt = {3'b110}; // wr_en=1, full=1, rd_en=0
            bins simultaneous_full = {3'b111}; // wr_en=1, full=1, rd_en=1
        }
        
        // Corner case: Read from empty FIFO
        read_from_empty_cp: coverpoint {trans.rd_en, trans.empty, trans.wr_en} {
            bins underflow_attempt = {3'b110}; // rd_en=1, empty=1, wr_en=0
            bins simultaneous_empty = {3'b111}; // rd_en=1, empty=1, wr_en=1
        }
        
        // Threshold boundaries
        threshold_boundaries_cp: coverpoint trans.count {
            bins almost_empty_threshold = {DEPTH/4};
            bins almost_full_threshold = {3*DEPTH/4};
            bins depth_minus_one = {DEPTH-1};
            bins depth = {DEPTH};
        }
    endgroup
    
    `uvm_component_param_utils(sync_fifo_coverage #(DATA_WIDTH, DEPTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_coverage", uvm_component parent = null);
        super.new(name, parent);
        fifo_operations_cg = new();
        fifo_status_cg = new();
        fifo_data_cg = new();
        fifo_transitions_cg = new();
        corner_cases_cg = new();
    endfunction
    
    virtual function void write(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH) t);
        trans = t;
        fifo_operations_cg.sample();
        fifo_status_cg.sample();
        fifo_data_cg.sample();
        fifo_transitions_cg.sample();
        corner_cases_cg.sample();
    endfunction
    
    virtual function void report_phase(uvm_phase phase);
        super.report_phase(phase);
        `uvm_info("COV", $sformatf("Coverage Report:"), UVM_LOW)
        `uvm_info("COV", $sformatf("  Operations: %0.2f%%", fifo_operations_cg.get_coverage()), UVM_LOW)
        `uvm_info("COV", $sformatf("  Status: %0.2f%%", fifo_status_cg.get_coverage()), UVM_LOW)
        `uvm_info("COV", $sformatf("  Data: %0.2f%%", fifo_data_cg.get_coverage()), UVM_LOW)
        `uvm_info("COV", $sformatf("  Transitions: %0.2f%%", fifo_transitions_cg.get_coverage()), UVM_LOW)
        `uvm_info("COV", $sformatf("  Corner Cases: %0.2f%%", corner_cases_cg.get_coverage()), UVM_LOW)
    endfunction
    
endclass
```

## 8. sync_fifo_virtual_sequencer.sv - Virtual Sequencer
```systemverilog
class sync_fifo_virtual_sequencer #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_sequencer;
    
    uvm_sequencer #(sync_fifo_transaction #(DATA_WIDTH, ADDR_WIDTH)) fifo_sequencer;
    
    `uvm_component_param_utils(sync_fifo_virtual_sequencer #(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_virtual_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
endclass
```

## 9. sync_fifo_env.sv - Environment Class
```systemverilog
class sync_fifo_env #(parameter DATA_WIDTH = 8, parameter DEPTH = 16, parameter ADDR_WIDTH = 4) extends uvm_env;
    
    sync_fifo_agent #(DATA_WIDTH, ADDR_WIDTH) agent;
    sync_fifo_scoreboard #(DATA_WIDTH, DEPTH, ADDR_WIDTH) scoreboard;
    sync_fifo_coverage #(DATA_WIDTH, DEPTH, ADDR_WIDTH) coverage;
    sync_fifo_virtual_sequencer #(DATA_WIDTH, ADDR_WIDTH) virtual_sequencer;
    
    `uvm_component_param_utils(sync_fifo_env #(DATA_WIDTH, DEPTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_env", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        agent = sync_fifo_agent #(DATA_WIDTH, ADDR_WIDTH)::type_id::create("agent", this);
        scoreboard = sync_fifo_scoreboard #(DATA_WIDTH, DEPTH, ADDR_WIDTH)::type_id::create("scoreboard", this);
        coverage = sync_fifo_coverage #(DATA_WIDTH, DEPTH, ADDR_WIDTH)::type_id::create("coverage", this);
        virtual_sequencer = sync_fifo_virtual_sequencer #(DATA_WIDTH, ADDR_WIDTH)::type_id::create("virtual_sequencer", this);
    endfunction
    
    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        
        // Connect agent monitor to scoreboard and coverage
        agent.monitor.ap.connect(scoreboard.ap_imp);
        agent.monitor.ap.connect(coverage.analysis_export);
        
        // Connect virtual sequencer
        virtual_sequencer.fifo_sequencer = agent.sequencer;
    endfunction
    
    virtual function void end_of_elaboration_phase(uvm_phase phase);
        super.end_of_elaboration_phase(phase);
        `uvm_info("ENV", $sformatf("FIFO Environment created with DATA_WIDTH=%0d, DEPTH=%0d", DATA_WIDTH, DEPTH), UVM_LOW)
    endfunction
    
endclass
```

## 10. sync_fifo_pkg.sv - Package
```systemverilog
package sync_fifo_pkg;
    import uvm