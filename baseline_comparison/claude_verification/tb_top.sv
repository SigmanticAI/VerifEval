//==============================================================================
// File: tb_top.sv
// Description: Top-level UVM Testbench for Synchronous FIFO
//==============================================================================

`timescale 1ns/1ps

// Include UVM package
`include "uvm_macros.svh"

module tb_top;
    
    import uvm_pkg::*;

    //==========================================================================
    // Parameters
    //==========================================================================
    parameter DATA_WIDTH = 8;
    parameter DEPTH      = 16;
    parameter ADDR_WIDTH = 4;
    parameter CLK_PERIOD = 10;  // 100MHz clock

    //==========================================================================
    // Clock and Reset Generation
    //==========================================================================
    logic clk;
    logic rst_n;

    // Clock generation
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Reset generation
    initial begin
        rst_n = 0;
        repeat(5) @(posedge clk);
        rst_n = 1;
    end

    //==========================================================================
    // Interface Instantiation
    //==========================================================================
    fifo_if #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) vif (
        .clk(clk),
        .rst_n(rst_n)
    );

    //==========================================================================
    // DUT Instantiation
    //==========================================================================
    sync_fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) dut (
        .clk         (clk),
        .rst_n       (rst_n),
        .wr_en       (vif.wr_en),
        .rd_en       (vif.rd_en),
        .wr_data     (vif.wr_data),
        .rd_data     (vif.rd_data),
        .full        (vif.full),
        .empty       (vif.empty),
        .almost_full (vif.almost_full),
        .almost_empty(vif.almost_empty),
        .count       (vif.count)
    );

    //==========================================================================
    // Assertions Module Instantiation
    //==========================================================================
    fifo_assertions #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) assertions (
        .clk         (clk),
        .rst_n       (rst_n),
        .wr_en       (vif.wr_en),
        .rd_en       (vif.rd_en),
        .wr_data     (vif.wr_data),
        .rd_data     (vif.rd_data),
        .full        (vif.full),
        .empty       (vif.empty),
        .almost_full (vif.almost_full),
        .almost_empty(vif.almost_empty),
        .count       (vif.count)
    );

    //==========================================================================
    // Coverage Module Instantiation
    //==========================================================================
    fifo_coverage_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) coverage_inst (
        .clk         (clk),
        .rst_n       (rst_n),
        .wr_en       (vif.wr_en),
        .rd_en       (vif.rd_en),
        .wr_data     (vif.wr_data),
        .rd_data     (vif.rd_data),
        .full        (vif.full),
        .empty       (vif.empty),
        .almost_full (vif.almost_full),
        .almost_empty(vif.almost_empty),
        .count       (vif.count)
    );

    //==========================================================================
    // Reference Model and Scoreboard
    //==========================================================================
    
    // Reference FIFO model for data checking
    logic [DATA_WIDTH-1:0] ref_fifo [$];
    logic [DATA_WIDTH-1:0] expected_rd_data;
    int error_count = 0;
    int transaction_count = 0;
    
    // Track write and read for scoreboard
    always @(posedge clk) begin
        if (rst_n) begin
            // Effective write/read signals (mirrors DUT logic)
            automatic logic wr_en_int = vif.wr_en && (!vif.full || vif.rd_en);
            automatic logic rd_en_int = vif.rd_en && (!vif.empty || vif.wr_en);
            
            // Handle write to reference model
            if (wr_en_int) begin
                ref_fifo.push_back(vif.wr_data);
                transaction_count++;
                `uvm_info("SCOREBOARD", $sformatf("Write: data=0x%02h, ref_size=%0d", 
                          vif.wr_data, ref_fifo.size()), UVM_HIGH)
            end
            
            // Handle read and check from reference model
            if (rd_en_int && ref_fifo.size() > 0) begin
                expected_rd_data = ref_fifo.pop_front();
            end
        end else begin
            ref_fifo.delete();
        end
    end
    
    // Data integrity check (delayed by 1 cycle due to registered output)
    logic rd_en_d1;
    logic check_enable;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_en_d1 <= 0;
            check_enable <= 0;
        end else begin
            rd_en_d1 <= vif.rd_en && (!vif.empty || vif.wr_en);
            check_enable <= rd_en_d1;
        end
    end
    
    always @(posedge clk) begin
        if (rst_n && check_enable) begin
            if (vif.rd_data !== expected_rd_data) begin
                error_count++;
                `uvm_error("SCOREBOARD", $sformatf(
                    "Data mismatch! Expected: 0x%02h, Got: 0x%02h",
                    expected_rd_data, vif.rd_data))
            end else begin
                `uvm_info("SCOREBOARD", $sformatf(
                    "Data match: 0x%02h", vif.rd_data), UVM_HIGH)
            end
        end
    end

    //==========================================================================
    // Test Stimulus
    //==========================================================================
    
    initial begin
        // Initialize interface
        vif.wr_en   = 0;
        vif.rd_en   = 0;
        vif.wr_data = 0;
        
        // Wait for reset to complete
        @(posedge rst_n);
        repeat(2) @(posedge clk);
        
        `uvm_info("TEST", "Starting FIFO Verification Tests", UVM_LOW)
        
        //----------------------------------------------------------------------
        // Test 1: Basic Write and Read
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 1: Basic Write and Read", UVM_LOW)
        
        // Write 5 items
        for (int i = 0; i < 5; i++) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.wr_data <= i + 1;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        
        // Read 5 items
        repeat(2) @(posedge clk);
        for (int i = 0; i < 5; i++) begin
            @(posedge clk);
            vif.rd_en <= 1;
        end
        @(posedge clk);
        vif.rd_en <= 0;
        
        repeat(5) @(posedge clk);
        
        //----------------------------------------------------------------------
        // Test 2: Fill FIFO to Full
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 2: Fill FIFO to Full", UVM_LOW)
        
        for (int i = 0; i < DEPTH; i++) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.wr_data <= 8'hA0 + i;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        
        // Verify full flag
        @(posedge clk);
        if (!vif.full)
            `uvm_error("TEST", "FIFO should be full!")
        else
            `uvm_info("TEST", "FIFO correctly indicates full", UVM_LOW)
        
        //----------------------------------------------------------------------
        // Test 3: Attempt Write When Full
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 3: Attempt Write When Full (should be blocked)", UVM_LOW)
        
        @(posedge clk);
        vif.wr_en   <= 1;
        vif.wr_data <= 8'hFF;
        @(posedge clk);
        vif.wr_en <= 0;
        
        repeat(2) @(posedge clk);
        
        //----------------------------------------------------------------------
        // Test 4: Drain FIFO to Empty
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 4: Drain FIFO to Empty", UVM_LOW)
        
        for (int i = 0; i < DEPTH; i++) begin
            @(posedge clk);
            vif.rd_en <= 1;
        end
        @(posedge clk);
        vif.rd_en <= 0;
        
        repeat(2) @(posedge clk);
        
        // Verify empty flag
        if (!vif.empty)
            `uvm_error("TEST", "FIFO should be empty!")
        else
            `uvm_info("TEST", "FIFO correctly indicates empty", UVM_LOW)
        
        //----------------------------------------------------------------------
        // Test 5: Attempt Read When Empty
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 5: Attempt Read When Empty (should be blocked)", UVM_LOW)
        
        @(posedge clk);
        vif.rd_en <= 1;
        @(posedge clk);
        vif.rd_en <= 0;
        
        repeat(2) @(posedge clk);
        
        //----------------------------------------------------------------------
        // Test 6: Simultaneous Read/Write
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 6: Simultaneous Read/Write", UVM_LOW)
        
        // First fill with some data
        for (int i = 0; i < 8; i++) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.wr_data <= 8'hB0 + i;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        
        // Simultaneous read and write
        repeat(2) @(posedge clk);
        for (int i = 0; i < 10; i++) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.rd_en   <= 1;
            vif.wr_data <= 8'hC0 + i;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        vif.rd_en <= 0;
        
        repeat(5) @(posedge clk);
        
        //----------------------------------------------------------------------
        // Test 7: Simultaneous R/W When Full
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 7: Simultaneous R/W When Full", UVM_LOW)
        
        // Fill to full
        while (!vif.full) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.wr_data <= $random;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        
        // Simultaneous R/W when full
        @(posedge clk);
        vif.wr_en   <= 1;
        vif.rd_en   <= 1;
        vif.wr_data <= 8'hDD;
        @(posedge clk);
        vif.wr_en <= 0;
        vif.rd_en <= 0;
        
        repeat(3) @(posedge clk);
        
        //----------------------------------------------------------------------
        // Test 8: Random Stimulus
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 8: Random Stimulus (1000 cycles)", UVM_LOW)
        
        // First drain FIFO
        while (!vif.empty) begin
            @(posedge clk);
            vif.rd_en <= 1;
        end
        @(posedge clk);
        vif.rd_en <= 0;
        
        // Random operations
        for (int i = 0; i < 1000; i++) begin
            @(posedge clk);
            vif.wr_en   <= $urandom_range(0, 1);
            vif.rd_en   <= $urandom_range(0, 1);
            vif.wr_data <= $urandom;
        end
        @(posedge clk);
        vif.wr_en <= 0;
        vif.rd_en <= 0;
        
        //----------------------------------------------------------------------
        // Test 9: Walking Ones Data Pattern
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 9: Walking Ones Data Pattern", UVM_LOW)
        
        // Drain FIFO first
        while (!vif.empty) begin
            @(posedge clk);
            vif.rd_en <= 1;
        end
        @(posedge clk);
        vif.rd_en <= 0;
        
        // Write walking ones
        for (int i = 0; i < DATA_WIDTH; i++) begin
            @(posedge clk);
            vif.wr_en   <= 1;
            vif.wr_data <= (1 << i);
        end
        @(posedge clk);
        vif.wr_en <= 0;
        
        // Read and verify
        repeat(2) @(posedge clk);
        for (int i = 0; i < DATA_WIDTH; i++) begin
            @(posedge clk);
            vif.rd_en <= 1;
        end
        @(posedge clk);
        vif.rd_en <= 0;
        
        //----------------------------------------------------------------------
        // Test 10: Rapid Fill/Drain Cycles
        //----------------------------------------------------------------------
        `uvm_info("TEST", "Test 10: Rapid Fill/Drain Cycles", UVM_LOW)
        
        repeat(5) @(posedge clk);
        
        for (int cycle = 0; cycle < 5; cycle++) begin
            // Fill
            for (int i = 0; i < DEPTH; i++) begin
                @(posedge clk);
                vif.wr_en   <= 1;
                vif.wr_data <= cycle * DEPTH + i;
            end
            @(posedge clk);
            vif.wr_en <= 0;
            
            // Drain
            for (int i = 0; i < DEPTH; i++) begin
                @(posedge clk);
                vif.rd_en <= 1;
            end
            @(posedge clk);
            vif.rd_en <= 0;
            
            repeat(2) @(posedge clk);
        end
        
        //----------------------------------------------------------------------
        // Test Complete
        //----------------------------------------------------------------------
        repeat(10) @(posedge clk);
        
        `uvm_info("TEST", "============================================", UVM_LOW)
        `uvm_info("TEST", "        TEST SUMMARY", UVM_LOW)
        `uvm_info("TEST", "============================================", UVM_LOW)
        `uvm_info("TEST", $sformatf("Total Transactions: %0d", transaction_count), UVM_LOW)
        `uvm_info("TEST", $sformatf("Total Errors: %0d", error_count), UVM_LOW)
        
        if (error_count == 0)
            `uvm_info("TEST", "*** ALL TESTS PASSED ***", UVM_LOW)
        else
            `uvm_error("TEST", "*** TESTS FAILED ***")
        
        `uvm_info("TEST", "============================================", UVM_LOW)
        
        // End simulation
        #100;
        $finish;
    end

    //==========================================================================
    // Timeout Watchdog
    //==========================================================================
    initial begin
        #100000;  // 100us timeout
        `uvm_fatal("TIMEOUT", "Simulation timeout!")
    end

    //==========================================================================
    // Waveform Dump
    //==========================================================================
    initial begin
        $dumpfile("fifo_tb.vcd");
        $dumpvars(0, tb_top);
    end

    //==========================================================================
    // UVM Configuration
    //==========================================================================
    initial begin
        // Set interface in config_db for UVM components (if using full UVM env)
        uvm_config_db#(virtual fifo_if#(DATA_WIDTH, DEPTH, ADDR_WIDTH))::set(
            null, "*", "vif", vif);
    end

endmodule : tb_top

