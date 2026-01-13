//==============================================================================
// File: fifo_coverage.sv
// Description: Functional Coverage for Synchronous FIFO Verification
//==============================================================================

class fifo_coverage #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
);

    //==========================================================================
    // Coverage Variables
    //==========================================================================
    
    // Transaction-level signals
    logic                  wr_en;
    logic                  rd_en;
    logic [DATA_WIDTH-1:0] wr_data;
    logic [DATA_WIDTH-1:0] rd_data;
    logic                  full;
    logic                  empty;
    logic                  almost_full;
    logic                  almost_empty;
    logic [ADDR_WIDTH:0]   count;
    
    // Derived signals for coverage
    logic                  wr_en_int;
    logic                  rd_en_int;
    logic [ADDR_WIDTH:0]   prev_count;
    logic                  prev_full;
    logic                  prev_empty;
    
    //==========================================================================
    // Covergroup Definitions
    //==========================================================================
    
    //--------------------------------------------------------------------------
    // FIFO State Coverage
    //--------------------------------------------------------------------------
    covergroup cg_fifo_state @(posedge wr_en or posedge rd_en or negedge wr_en or negedge rd_en);
        option.per_instance = 1;
        option.name = "FIFO_State_Coverage";
        
        // FIFO fill level states
        cp_fifo_level: coverpoint count {
            bins empty_state     = {0};
            bins almost_empty    = {1};
            bins low_fill        = {[2:DEPTH/4-1]};
            bins mid_fill        = {[DEPTH/4:3*DEPTH/4]};
            bins high_fill       = {[3*DEPTH/4+1:DEPTH-2]};
            bins almost_full     = {DEPTH-1};
            bins full_state      = {DEPTH};
        }
        
        // Status flag states
        cp_empty_flag: coverpoint empty {
            bins asserted   = {1};
            bins deasserted = {0};
        }
        
        cp_full_flag: coverpoint full {
            bins asserted   = {1};
            bins deasserted = {0};
        }
        
        cp_almost_empty_flag: coverpoint almost_empty {
            bins asserted   = {1};
            bins deasserted = {0};
        }
        
        cp_almost_full_flag: coverpoint almost_full {
            bins asserted   = {1};
            bins deasserted = {0};
        }
        
    endgroup : cg_fifo_state

    //--------------------------------------------------------------------------
    // Operation Coverage
    //--------------------------------------------------------------------------
    covergroup cg_operations @(posedge wr_en or posedge rd_en or negedge wr_en or negedge rd_en);
        option.per_instance = 1;
        option.name = "Operation_Coverage";
        
        // Write enable coverage
        cp_wr_en: coverpoint wr_en {
            bins write_active   = {1};
            bins write_inactive = {0};
        }
        
        // Read enable coverage
        cp_rd_en: coverpoint rd_en {
            bins read_active   = {1};
            bins read_inactive = {0};
        }
        
        // Combined operation types
        cp_operation_type: coverpoint {wr_en, rd_en} {
            bins no_op         = {2'b00};
            bins write_only    = {2'b10};
            bins read_only     = {2'b01};
            bins simultaneous  = {2'b11};
        }
        
        // Effective write (internal)
        cp_wr_en_int: coverpoint wr_en_int {
            bins effective_write   = {1};
            bins blocked_write     = {0};
        }
        
        // Effective read (internal)
        cp_rd_en_int: coverpoint rd_en_int {
            bins effective_read    = {1};
            bins blocked_read      = {0};
        }
        
        // Cross coverage: Operation vs FIFO level
        cx_op_vs_level: cross cp_operation_type, cp_fifo_level {
            // Key scenarios to cover
            bins write_when_empty      = binsof(cp_operation_type.write_only) && 
                                         binsof(cp_fifo_level.empty_state);
            bins write_when_full       = binsof(cp_operation_type.write_only) && 
                                         binsof(cp_fifo_level.full_state);
            bins read_when_empty       = binsof(cp_operation_type.read_only) && 
                                         binsof(cp_fifo_level.empty_state);
            bins read_when_full        = binsof(cp_operation_type.read_only) && 
                                         binsof(cp_fifo_level.full_state);
            bins simul_when_empty      = binsof(cp_operation_type.simultaneous) && 
                                         binsof(cp_fifo_level.empty_state);
            bins simul_when_full       = binsof(cp_operation_type.simultaneous) && 
                                         binsof(cp_fifo_level.full_state);
        }
        
        // Local copy of count for cross coverage
        cp_fifo_level: coverpoint count {
            bins empty_state     = {0};
            bins almost_empty    = {1};
            bins low_fill        = {[2:DEPTH/4-1]};
            bins mid_fill        = {[DEPTH/4:3*DEPTH/4]};
            bins high_fill       = {[3*DEPTH/4+1:DEPTH-2]};
            bins almost_full     = {DEPTH-1};
            bins full_state      = {DEPTH};
        }
        
    endgroup : cg_operations

    //--------------------------------------------------------------------------
    // Data Pattern Coverage
    //--------------------------------------------------------------------------
    covergroup cg_data_patterns @(posedge wr_en);
        option.per_instance = 1;
        option.name = "Data_Pattern_Coverage";
        
        // Write data patterns
        cp_wr_data: coverpoint wr_data {
            bins all_zeros     = {'0};
            bins all_ones      = {{DATA_WIDTH{1'b1}}};
            bins low_values    = {[1:15]};
            bins mid_values    = {[16:239]};
            bins high_values   = {[240:254]};
            // Walking ones (for 8-bit)
            bins walk_1_bit0   = {8'h01};
            bins walk_1_bit1   = {8'h02};
            bins walk_1_bit2   = {8'h04};
            bins walk_1_bit3   = {8'h08};
            bins walk_1_bit4   = {8'h10};
            bins walk_1_bit5   = {8'h20};
            bins walk_1_bit6   = {8'h40};
            bins walk_1_bit7   = {8'h80};
            // Walking zeros (for 8-bit)
            bins walk_0_bit0   = {8'hFE};
            bins walk_0_bit1   = {8'hFD};
            bins walk_0_bit2   = {8'hFB};
            bins walk_0_bit3   = {8'hF7};
            bins walk_0_bit4   = {8'hEF};
            bins walk_0_bit5   = {8'hDF};
            bins walk_0_bit6   = {8'hBF};
            bins walk_0_bit7   = {8'h7F};
            // Alternating patterns
            bins alternating_01 = {8'h55};
            bins alternating_10 = {8'hAA};
        }
        
        // Read data patterns
        cp_rd_data: coverpoint rd_data {
            bins all_zeros     = {'0};
            bins all_ones      = {{DATA_WIDTH{1'b1}}};
            bins other_values  = default;
        }
        
    endgroup : cg_data_patterns

    //--------------------------------------------------------------------------
    // State Transition Coverage
    //--------------------------------------------------------------------------
    covergroup cg_transitions @(posedge wr_en or posedge rd_en);
        option.per_instance = 1;
        option.name = "Transition_Coverage";
        
        // Empty flag transitions
        cp_empty_transition: coverpoint {prev_empty, empty} {
            bins stay_empty       = {2'b11};
            bins empty_to_filled  = {2'b10};
            bins filled_to_empty  = {2'b01};
            bins stay_filled      = {2'b00};
        }
        
        // Full flag transitions
        cp_full_transition: coverpoint {prev_full, full} {
            bins stay_not_full    = {2'b00};
            bins become_full      = {2'b01};
            bins become_not_full  = {2'b10};
            bins stay_full        = {2'b11};
        }
        
        // Count transitions
        cp_count_change: coverpoint (count - prev_count) {
            bins decrement = {-1};
            bins no_change = {0};
            bins increment = {1};
            illegal_bins illegal_change = default;
        }
        
    endgroup : cg_transitions

    //--------------------------------------------------------------------------
    // Boundary Condition Coverage
    //--------------------------------------------------------------------------
    covergroup cg_boundary @(posedge wr_en or posedge rd_en);
        option.per_instance = 1;
        option.name = "Boundary_Coverage";
        
        // Write at boundary conditions
        cp_write_boundary: coverpoint {wr_en, full, almost_full} iff (wr_en) {
            bins write_normal       = {3'b100};
            bins write_almost_full  = {3'b101};
            bins write_full         = {3'b110, 3'b111};
        }
        
        // Read at boundary conditions
        cp_read_boundary: coverpoint {rd_en, empty, almost_empty} iff (rd_en) {
            bins read_normal        = {3'b100};
            bins read_almost_empty  = {3'b101};
            bins read_empty         = {3'b110, 3'b111};
        }
        
        // Simultaneous operations at boundaries
        cp_simul_boundary: coverpoint {wr_en, rd_en, full, empty} iff (wr_en && rd_en) {
            bins simul_normal      = {4'b1100};
            bins simul_when_full   = {4'b1110};
            bins simul_when_empty  = {4'b1101};
        }
        
        // Count at all possible values
        cp_all_counts: coverpoint count {
            bins count_values[] = {[0:DEPTH]};
        }
        
    endgroup : cg_boundary

    //--------------------------------------------------------------------------
    // Corner Case Coverage
    //--------------------------------------------------------------------------
    covergroup cg_corner_cases @(posedge wr_en or posedge rd_en);
        option.per_instance = 1;
        option.name = "Corner_Case_Coverage";
        
        // Back-to-back operations
        cp_back_to_back: coverpoint {wr_en, rd_en} {
            bins consecutive_writes = (2'b10 [*3]);
            bins consecutive_reads  = (2'b01 [*3]);
            bins alternating_wr_rd  = (2'b10 => 2'b01 [*2]);
            bins alternating_rd_wr  = (2'b01 => 2'b10 [*2]);
        }
        
        // Fill and drain sequences
        cp_fill_drain: coverpoint count {
            bins fill_sequence   = (0 => [1:DEPTH-1] => DEPTH);
            bins drain_sequence  = (DEPTH => [DEPTH-1:1] => 0);
        }
        
        // Blocked operations
        cp_blocked_write: coverpoint {wr_en, full, rd_en} {
            bins blocked_write_attempt = {3'b110};  // wr_en && full && !rd_en
        }
        
        cp_blocked_read: coverpoint {rd_en, empty, wr_en} {
            bins blocked_read_attempt = {3'b110};   // rd_en && empty && !wr_en
        }
        
    endgroup : cg_corner_cases

    //==========================================================================
    // Constructor
    //==========================================================================
    
    function new(string name = "fifo_coverage");
        cg_fifo_state   = new();
        cg_operations   = new();
        cg_data_patterns = new();
        cg_transitions  = new();
        cg_boundary     = new();
        cg_corner_cases = new();
        
        // Set covergroup names
        cg_fifo_state.set_inst_name({name, ".fifo_state"});
        cg_operations.set_inst_name({name, ".operations"});
        cg_data_patterns.set_inst_name({name, ".data_patterns"});
        cg_transitions.set_inst_name({name, ".transitions"});
        cg_boundary.set_inst_name({name, ".boundary"});
        cg_corner_cases.set_inst_name({name, ".corner_cases"});
    endfunction

    //==========================================================================
    // Sample Method
    //==========================================================================
    
    function void sample(
        input logic                  i_wr_en,
        input logic                  i_rd_en,
        input logic [DATA_WIDTH-1:0] i_wr_data,
        input logic [DATA_WIDTH-1:0] i_rd_data,
        input logic                  i_full,
        input logic                  i_empty,
        input logic                  i_almost_full,
        input logic                  i_almost_empty,
        input logic [ADDR_WIDTH:0]   i_count
    );
        // Store previous values
        prev_count = count;
        prev_full  = full;
        prev_empty = empty;
        
        // Update current values
        wr_en        = i_wr_en;
        rd_en        = i_rd_en;
        wr_data      = i_wr_data;
        rd_data      = i_rd_data;
        full         = i_full;
        empty        = i_empty;
        almost_full  = i_almost_full;
        almost_empty = i_almost_empty;
        count        = i_count;
        
        // Calculate internal signals
        wr_en_int = wr_en && (!full || rd_en);
        rd_en_int = rd_en && (!empty || wr_en);
        
        // Sample all covergroups
        cg_fifo_state.sample();
        cg_operations.sample();
        if (wr_en) cg_data_patterns.sample();
        cg_transitions.sample();
        cg_boundary.sample();
        cg_corner_cases.sample();
    endfunction

    //==========================================================================
    // Coverage Report Methods
    //==========================================================================
    
    function void report_coverage();
        $display("============================================================");
        $display("FIFO Coverage Report");
        $display("============================================================");
        $display("FIFO State Coverage:    %0.2f%%", cg_fifo_state.get_coverage());
        $display("Operations Coverage:    %0.2f%%", cg_operations.get_coverage());
        $display("Data Patterns Coverage: %0.2f%%", cg_data_patterns.get_coverage());
        $display("Transitions Coverage:   %0.2f%%", cg_transitions.get_coverage());
        $display("Boundary Coverage:      %0.2f%%", cg_boundary.get_coverage());
        $display("Corner Cases Coverage:  %0.2f%%", cg_corner_cases.get_coverage());
        $display("------------------------------------------------------------");
        $display("Overall Coverage:       %0.2f%%", get_overall_coverage());
        $display("============================================================");
    endfunction
    
    function real get_overall_coverage();
        return (cg_fifo_state.get_coverage() +
                cg_operations.get_coverage() +
                cg_data_patterns.get_coverage() +
                cg_transitions.get_coverage() +
                cg_boundary.get_coverage() +
                cg_corner_cases.get_coverage()) / 6.0;
    endfunction

endclass : fifo_coverage


//==============================================================================
// Module Wrapper for Coverage (for direct instantiation in testbench)
//==============================================================================
module fifo_coverage_module #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
) (
    input  logic                  clk,
    input  logic                  rst_n,
    input  logic                  wr_en,
    input  logic                  rd_en,
    input  logic [DATA_WIDTH-1:0] wr_data,
    input  logic [DATA_WIDTH-1:0] rd_data,
    input  logic                  full,
    input  logic                  empty,
    input  logic                  almost_full,
    input  logic                  almost_empty,
    input  logic [ADDR_WIDTH:0]   count
);

    // Coverage instance
    fifo_coverage #(DATA_WIDTH, DEPTH, ADDR_WIDTH) cov;
    
    initial begin
        cov = new("fifo_cov");
    end
    
    // Sample on every clock edge when not in reset
    always @(posedge clk) begin
        if (rst_n) begin
            cov.sample(wr_en, rd_en, wr_data, rd_data, 
                       full, empty, almost_full, almost_empty, count);
        end
    end
    
    // Report coverage at end of simulation
    final begin
        cov.report_coverage();
    end

endmodule : fifo_coverage_module

