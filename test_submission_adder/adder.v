// Simple 8-bit Adder DUT
// Single-file verification example

module adder (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire       cin,
    output wire [7:0] sum,
    output wire       cout
);

    wire [8:0] result;
    
    assign result = a + b + cin;
    assign sum = result[7:0];
    assign cout = result[8];

endmodule




