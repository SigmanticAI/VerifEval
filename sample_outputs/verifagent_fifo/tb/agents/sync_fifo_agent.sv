I'll generate a complete UVM agent for the sync_fifo interface. Here's the complete SystemVerilog code:

## 1. Interface Definition

```systemverilog
// sync_fifo_if.sv
interface sync_fifo_if #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(DEPTH)
)(
    input logic clk,
    input logic rst_n
);

    // Input signals
    logic wr_en;
    logic [DATA_WIDTH-1:0] wr_data;
    logic rd_en;
    
    // Output signals
    logic [DATA_WIDTH-1:0] rd_data;
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
    modport driver_mp (clocking driver_cb, input rst_n);
    modport monitor_mp (clocking monitor_cb, input rst_n);
    modport dut_mp (
        input clk, rst_n, wr_en, wr_data, rd_en,
        output rd_data, full, empty, almost_full, almost_empty, count, error
    );

endinterface
```

## 2. Sequence Item

```systemverilog
// sync_fifo_seq_item.sv
class sync_fifo_seq_item #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_sequence_item;
    
    // Input fields
    rand bit wr_en;
    rand bit [DATA_WIDTH-1:0] wr_data;
    rand bit rd_en;
    
    // Output fields (for monitoring)
    bit [DATA_WIDTH-1:0] rd_data;
    bit full;
    bit empty;
    bit almost_full;
    bit almost_empty;
    bit [ADDR_WIDTH:0] count;
    bit error;
    
    // Constraints
    constraint c_valid_ops {
        // Reasonable distribution of operations
        wr_en dist {0 := 30, 1 := 70};
        rd_en dist {0 := 30, 1 := 70};
    }
    
    constraint c_data_range {
        wr_data inside {[0:(1<<DATA_WIDTH)-1]};
    }
    
    // UVM macros
    `uvm_object_param_utils_begin(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH))
        `uvm_field_int(wr_en, UVM_ALL_ON)
        `uvm_field_int(wr_data, UVM_ALL_ON)
        `uvm_field_int(rd_en, UVM_ALL_ON)
        `uvm_field_int(rd_data, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(full, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(empty, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(almost_full, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(almost_empty, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(count, UVM_ALL_ON | UVM_NOCOMPARE)
        `uvm_field_int(error, UVM_ALL_ON | UVM_NOCOMPARE)
    `uvm_object_utils_end
    
    function new(string name = "sync_fifo_seq_item");
        super.new(name);
    endfunction
    
    // Custom print method
    virtual function string convert2string();
        string s;
        s = $sformatf("wr_en=%0b, wr_data=0x%0h, rd_en=%0b, rd_data=0x%0h, full=%0b, empty=%0b, count=%0d, error=%0b",
                     wr_en, wr_data, rd_en, rd_data, full, empty, count, error);
        return s;
    endfunction
    
endclass
```

## 3. Sequencer

```systemverilog
// sync_fifo_sequencer.sv
class sync_fifo_sequencer #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) 
    extends uvm_sequencer #(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH));
    
    `uvm_component_param_utils(sync_fifo_sequencer#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
endclass
```

## 4. Driver

```systemverilog
// sync_fifo_driver.sv
class sync_fifo_driver #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_driver #(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH));
    
    virtual sync_fifo_if#(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH).driver_mp vif;
    
    `uvm_component_param_utils(sync_fifo_driver#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual sync_fifo_if#(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH).driver_mp)::get(this, "", "vif", vif)) begin
            `uvm_fatal("NOVIF", "Virtual interface not found")
        end
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item;
        
        // Initialize signals
        vif.driver_cb.wr_en <= 0;
        vif.driver_cb.wr_data <= 0;
        vif.driver_cb.rd_en <= 0;
        
        // Wait for reset deassertion
        wait(vif.rst_n);
        @(vif.driver_cb);
        
        forever begin
            seq_item_port.get_next_item(item);
            drive_item(item);
            seq_item_port.item_done();
        end
    endtask
    
    virtual task drive_item(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item);
        `uvm_info("DRIVER", $sformatf("Driving item: %s", item.convert2string()), UVM_HIGH)
        
        @(vif.driver_cb);
        vif.driver_cb.wr_en <= item.wr_en;
        vif.driver_cb.wr_data <= item.wr_data;
        vif.driver_cb.rd_en <= item.rd_en;
        
        // Capture response data
        @(vif.driver_cb);
        item.rd_data = vif.driver_cb.rd_data;
        item.full = vif.driver_cb.full;
        item.empty = vif.driver_cb.empty;
        item.almost_full = vif.driver_cb.almost_full;
        item.almost_empty = vif.driver_cb.almost_empty;
        item.count = vif.driver_cb.count;
        item.error = vif.driver_cb.error;
    endtask
    
endclass
```

## 5. Monitor

```systemverilog
// sync_fifo_monitor.sv
class sync_fifo_monitor #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_monitor;
    
    virtual sync_fifo_if#(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH).monitor_mp vif;
    uvm_analysis_port #(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)) ap;
    
    `uvm_component_param_utils(sync_fifo_monitor#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_monitor", uvm_component parent = null);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual sync_fifo_if#(DATA_WIDTH, 2**ADDR_WIDTH, ADDR_WIDTH).monitor_mp)::get(this, "", "vif", vif)) begin
            `uvm_fatal("NOVIF", "Virtual interface not found")
        end
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item;
        
        // Wait for reset deassertion
        wait(vif.rst_n);
        
        forever begin
            @(vif.monitor_cb);
            
            // Create and populate transaction
            item = sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("item");
            
            item.wr_en = vif.monitor_cb.wr_en;
            item.wr_data = vif.monitor_cb.wr_data;
            item.rd_en = vif.monitor_cb.rd_en;
            item.rd_data = vif.monitor_cb.rd_data;
            item.full = vif.monitor_cb.full;
            item.empty = vif.monitor_cb.empty;
            item.almost_full = vif.monitor_cb.almost_full;
            item.almost_empty = vif.monitor_cb.almost_empty;
            item.count = vif.monitor_cb.count;
            item.error = vif.monitor_cb.error;
            
            `uvm_info("MONITOR", $sformatf("Monitored transaction: %s", item.convert2string()), UVM_HIGH)
            
            // Send to analysis port
            ap.write(item);
        end
    endtask
    
endclass
```

## 6. Agent

```systemverilog
// sync_fifo_agent.sv
class sync_fifo_agent #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) extends uvm_agent;
    
    sync_fifo_driver#(DATA_WIDTH, ADDR_WIDTH) driver;
    sync_fifo_sequencer#(DATA_WIDTH, ADDR_WIDTH) sequencer;
    sync_fifo_monitor#(DATA_WIDTH, ADDR_WIDTH) monitor;
    
    uvm_analysis_port #(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)) ap;
    
    `uvm_component_param_utils(sync_fifo_agent#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        // Create monitor (always present)
        monitor = sync_fifo_monitor#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("monitor", this);
        
        // Create driver and sequencer only if agent is active
        if (get_is_active() == UVM_ACTIVE) begin
            driver = sync_fifo_driver#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("driver", this);
            sequencer = sync_fifo_sequencer#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("sequencer", this);
        end
    endfunction
    
    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        
        // Connect analysis port
        ap = monitor.ap;
        
        // Connect driver and sequencer if active
        if (get_is_active() == UVM_ACTIVE) begin
            driver.seq_item_port.connect(sequencer.seq_item_export);
        end
    endfunction
    
endclass
```

## 7. Package File

```systemverilog
// sync_fifo_agent_pkg.sv
package sync_fifo_agent_pkg;
    
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    
    // Include all agent files
    `include "sync_fifo_seq_item.sv"
    `include "sync_fifo_sequencer.sv"
    `include "sync_fifo_driver.sv"
    `include "sync_fifo_monitor.sv"
    `include "sync_fifo_agent.sv"
    
endpackage
```

## 8. Basic Sequences

```systemverilog
// sync_fifo_sequences.sv
class sync_fifo_base_seq #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) 
    extends uvm_sequence #(sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH));
    
    `uvm_object_param_utils(sync_fifo_base_seq#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_base_seq");
        super.new(name);
    endfunction
    
endclass

// Random sequence
class sync_fifo_random_seq #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) 
    extends sync_fifo_base_seq#(DATA_WIDTH, ADDR_WIDTH);
    
    rand int num_trans;
    constraint c_num_trans { num_trans inside {[10:50]}; }
    
    `uvm_object_param_utils(sync_fifo_random_seq#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_random_seq");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item;
        
        for (int i = 0; i < num_trans; i++) begin
            item = sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("item");
            start_item(item);
            if (!item.randomize()) begin
                `uvm_error("SEQ", "Randomization failed")
            end
            finish_item(item);
        end
    endtask
    
endclass

// Write-only sequence
class sync_fifo_write_seq #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) 
    extends sync_fifo_base_seq#(DATA_WIDTH, ADDR_WIDTH);
    
    rand int num_writes;
    constraint c_num_writes { num_writes inside {[5:20]}; }
    
    `uvm_object_param_utils(sync_fifo_write_seq#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_write_seq");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item;
        
        for (int i = 0; i < num_writes; i++) begin
            item = sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("item");
            start_item(item);
            if (!item.randomize() with {
                wr_en == 1;
                rd_en == 0;
            }) begin
                `uvm_error("SEQ", "Randomization failed")
            end
            finish_item(item);
        end
    endtask
    
endclass

// Read-only sequence
class sync_fifo_read_seq #(parameter DATA_WIDTH = 8, parameter ADDR_WIDTH = 4) 
    extends sync_fifo_base_seq#(DATA_WIDTH, ADDR_WIDTH);
    
    rand int num_reads;
    constraint c_num_reads { num_reads inside {[5:20]}; }
    
    `uvm_object_param_utils(sync_fifo_read_seq#(DATA_WIDTH, ADDR_WIDTH))
    
    function new(string name = "sync_fifo_read_seq");
        super.new(name);
    endfunction
    
    virtual task body();
        sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH) item;
        
        for (int i = 0; i < num_reads; i++) begin
            item = sync_fifo_seq_item#(DATA_WIDTH, ADDR_WIDTH)::type_id::create("item");
            start_item(item);
            if (!item.randomize() with {
                wr_en == 0;
                rd_en == 1;
            }) begin
                `uvm_error("SEQ", "Randomization failed")
            end
            finish_item(item);
        end
    endtask
    
endclass
```

This complete UVM agent provides:

1. **Parameterized design** - Supports configurable DATA_WIDTH and ADDR_WIDTH
2. **Proper interface** - With clocking blocks and modports
3. **Comprehensive sequence item** - With all FIFO signals and constraints
4. **Standard UVM components** - Driver, monitor, sequencer, and agent
5. **Analysis connectivity** - Monitor analysis port for scoreboard connection
6. **Basic sequences** - Random, write-only, and read-only sequences
7. **Proper UVM methodology** - Follows standard UVM practices

The agent can be easily integrated into a larger testbench environment and supports both active and passive modes of operation.