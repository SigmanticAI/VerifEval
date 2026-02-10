module fifo_assertions #(
    parameter DEPTH = 16,
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = $clog2(DEPTH)
) (
    input logic clk,
    input logic rst_n,
    input logic wr_en,
    input logic rd_en,
    input logic [DATA_WIDTH-1:0] wr_data,
    input logic [DATA_WIDTH-1:0] rd_data,
    input logic full,
    input logic empty,
    input logic [ADDR_WIDTH:0] count,
    input logic overflow,
    input logic underflow
);

    // Internal tracking variables
    logic [ADDR_WIDTH:0] exp_count;
    logic [DATA_WIDTH-1:0] fifo_model [0:DEPTH-1];
    logic [ADDR_WIDTH-1:0] wr_ptr, rd_ptr;
    logic [ADDR_WIDTH-1:0] exp_wr_ptr, exp_rd_ptr;

    // Count tracking
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            exp_count <= '0;
            exp_wr_ptr <= '0;
            exp_rd_ptr <= '0;
        end else begin
            case ({wr_en & ~full, rd_en & ~empty})
                2'b00: exp_count <= exp_count;
                2'b01: exp_count <= exp_count - 1;
                2'b10: exp_count <= exp_count + 1;
                2'b11: exp_count <= exp_count;
            endcase
            
            if (wr_en & ~full) begin
                exp_wr_ptr <= (exp_wr_ptr == DEPTH-1) ? '0 : exp_wr_ptr + 1;
                fifo_model[exp_wr_ptr] <= wr_data;
            end
            
            if (rd_en & ~empty) begin
                exp_rd_ptr <= (exp_rd_ptr == DEPTH-1) ? '0 : exp_rd_ptr + 1;
            end
        end
    end

    // Reset behavior assertions
    property reset_behavior;
        @(posedge clk) !rst_n |=> (empty && !full && count == 0);
    endproperty
    assert_reset_behavior: assert property(reset_behavior);

    property reset_no_overflow_underflow;
        @(posedge clk) !rst_n |=> (!overflow && !underflow);
    endproperty
    assert_reset_no_overflow_underflow: assert property(reset_no_overflow_underflow);

    // Full flag correctness
    property full_flag_set;
        @(posedge clk) disable iff(!rst_n)
        count == DEPTH |-> full;
    endproperty
    assert_full_flag_set: assert property(full_flag_set);

    property full_flag_clear;
        @(posedge clk) disable iff(!rst_n)
        count < DEPTH |-> !full;
    endproperty
    assert_full_flag_clear: assert property(full_flag_clear);

    // Empty flag correctness
    property empty_flag_set;
        @(posedge clk) disable iff(!rst_n)
        count == 0 |-> empty;
    endproperty
    assert_empty_flag_set: assert property(empty_flag_set);

    property empty_flag_clear;
        @(posedge clk) disable iff(!rst_n)
        count > 0 |-> !empty;
    endproperty
    assert_empty_flag_clear: assert property(empty_flag_clear);

    // Count bounds
    property count_bounds;
        @(posedge clk) disable iff(!rst_n)
        count <= DEPTH;
    endproperty
    assert_count_bounds: assert property(count_bounds);

    property count_consistency;
        @(posedge clk) disable iff(!rst_n)
        count == exp_count;
    endproperty
    assert_count_consistency: assert property(count_consistency);

    // No overflow without error
    property no_overflow_when_not_full;
        @(posedge clk) disable iff(!rst_n)
        wr_en && !full |=> !overflow;
    endproperty
    assert_no_overflow_when_not_full: assert property(no_overflow_when_not_full);

    property overflow_on_write_when_full;
        @(posedge clk) disable iff(!rst_n)
        wr_en && full |=> overflow;
    endproperty
    assert_overflow_on_write_when_full: assert property(overflow_on_write_when_full);

    // No underflow without error
    property no_underflow_when_not_empty;
        @(posedge clk) disable iff(!rst_n)
        rd_en && !empty |=> !underflow;
    endproperty
    assert_no_underflow_when_not_empty: assert property(no_underflow_when_not_empty);

    property underflow_on_read_when_empty;
        @(posedge clk) disable iff(!rst_n)
        rd_en && empty |=> underflow;
    endproperty
    assert_underflow_on_read_when_empty: assert property(underflow_on_read_when_empty);

    // FIFO ordering (first-in-first-out)
    property fifo_ordering;
        @(posedge clk) disable iff(!rst_n)
        rd_en && !empty |-> rd_data == fifo_model[exp_rd_ptr];
    endproperty
    assert_fifo_ordering: assert property(fifo_ordering);

    // Count increment on write (not full)
    property count_increment_on_write;
        @(posedge clk) disable iff(!rst_n)
        wr_en && !full && (!rd_en || empty) |=> count == $past(count) + 1;
    endproperty
    assert_count_increment_on_write: assert property(count_increment_on_write);

    // Count decrement on read (not empty)
    property count_decrement_on_read;
        @(posedge clk) disable iff(!rst_n)
        rd_en && !empty && (!wr_en || full) |=> count == $past(count) - 1;
    endproperty
    assert_count_decrement_on_read: assert property(count_decrement_on_read);

    // Count stable on simultaneous read/write
    property count_stable_on_simultaneous_rw;
        @(posedge clk) disable iff(!rst_n)
        wr_en && !full && rd_en && !empty |=> count == $past(count);
    endproperty
    assert_count_stable_on_simultaneous_rw: assert property(count_stable_on_simultaneous_rw);

    // Mutual exclusivity of full and empty (except when DEPTH=0)
    property full_empty_mutual_exclusive;
        @(posedge clk) disable iff(!rst_n)
        DEPTH > 0 |-> !(full && empty);
    endproperty
    assert_full_empty_mutual_exclusive: assert property(full_empty_mutual_exclusive);

    // Stability of flags when no operation
    property flag_stability_no_op;
        @(posedge clk) disable iff(!rst_n)
        !wr_en && !rd_en |=> $stable(full) && $stable(empty) && $stable(count);
    endproperty
    assert_flag_stability_no_op: assert property(flag_stability_no_op);

    // Error flag pulse behavior
    property overflow_pulse;
        @(posedge clk) disable iff(!rst_n)
        overflow |=> !overflow;
    endproperty
    assert_overflow_pulse: assert property(overflow_pulse);

    property underflow_pulse;
        @(posedge clk) disable iff(!rst_n)
        underflow |=> !underflow;
    endproperty
    assert_underflow_pulse: assert property(underflow_pulse);

endmodule