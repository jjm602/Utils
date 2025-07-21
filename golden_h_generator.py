import sys
import os
import re

def parse_reg_map_for_golden(filepath):
    """
    Parses the register map file to extract registers with their address and reset value,
    focusing on lines that define a new register.
    """
    registers = []
    base_address = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            # A line is considered a new register definition if the second part is a hex address.
            if len(parts) > 1 and parts[1].startswith('0x'):
                try:
                    reg_name = parts[0]
                    address = int(parts[1], 16)
                    reset_value_str = parts[-1]
                    reset_value = int(reset_value_str, 16)

                    if base_address is None:
                        # Assuming the first address sets the base
                        base_address = address & 0xFFFFF000  # e.g., 0x40007000

                    offset = address - base_address
                    registers.append({'name': reg_name, 'offset': offset, 'reset': reset_value})
                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not parse register line: '{line}'. Error: {e}")
    
    return registers

def generate_golden_h_code(registers):
    """
    Generates the C++ header content for the golden values header.
    """
    if not registers:
        return "// No registers found or parsed."

    header_content = """#pragma once

#include <cstdint>
#include <vector>

struct RegInfo {
  uint32_t offset;
  uint16_t expected_value;
};

std::vector<RegInfo> golden_regs = {
"""
    
    for reg in registers:
        header_content += f"  {{0x{reg['offset']:04x}, 0x{reg['reset']:04x}}}, // {reg['name']}\n"

    header_content += "};\n"
    
    return header_content

def main():
    """Main execution function"""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_filepath = sys.argv[1]
    if not os.path.exists(input_filepath):
        print(f"Error: File not found at {input_filepath}")
        sys.exit(1)

    # Generate output filename from input filename
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    # Convert CamelCase to snake_case and append _golden.h
    snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', base_name).lower()
    output_filename = f"{snake_case_name}_golden.h"

    try:
        registers = parse_reg_map_for_golden(input_filepath)
        h_code = generate_golden_h_code(registers)
        
        with open(output_filename, 'w') as f:
            f.write(h_code)
            
        print(f"Successfully generated {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
