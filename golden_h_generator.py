import sys
import os
import re
from collections import namedtuple

# From cpp_generator.py
Field = namedtuple('Field', ['name', 'position', 'reset_value'])
Register = namedtuple('Register', ['name', 'offset', 'reset_value'])

def parse_bit_position(pos_str):
    "'[15:0]' 형식의 문자열에서 시작 비트(0)를 파싱합니다."
    match = re.search(r'\[(\d+):(\d+)\]', pos_str)
    if match:
        return int(match.group(2)) # Return the lower bit number
    match = re.search(r'\[(\d+)\]', pos_str)
    if match:
        return int(match.group(1))
    return 0

def calculate_reset_value(fields):
    "필드 목록에서 전체 레지스터의 리셋 값을 계산합니다."
    total_reset = 0
    for field in fields:
        start_bit = parse_bit_position(field.position)
        total_reset |= (field.reset_value << start_bit)
    return total_reset

def parse_reg_map_file(filepath):
    "레지스터 맵 파일을 파싱하여 레지스터 정보 리스트를 반환합니다."
    registers = []
    base_address = None
    current_fields = []
    current_reg_name = None
    current_reg_offset = None
    current_reg_raw_name = None

    with open(filepath, 'r') as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            
            is_new_register = len(parts) > 1 and parts[1].startswith('0x')

            try:
                if is_new_register:
                    if current_reg_name and current_fields:
                        reset_value = calculate_reset_value(current_fields)
                        registers.append(Register(current_reg_raw_name, current_reg_offset, reset_value))
                    
                    current_fields = []
                    
                    if len(parts) < 5:
                        current_reg_name = None
                        continue

                    reg_name, address_str, field_name, *rest = parts
                    position = rest[-2]
                    reset_str = rest[-1]

                    address = int(address_str, 16)
                    if base_address is None:
                        base_address = address & 0xFFFFF000
                    
                    current_reg_raw_name = reg_name
                    current_reg_name = reg_name.upper()
                    current_reg_offset = address - base_address
                    
                    reset_value = int(reset_str, 16)
                    current_fields.append(Field(field_name, position, reset_value))

                else: 
                    if not current_reg_name:
                        continue
                    
                    if len(parts) < 3:
                        continue

                    field_name, *rest = parts
                    position = rest[-2]
                    reset_str = rest[-1]
                        
                    reset_value = int(reset_str, 16)
                    current_fields.append(Field(field_name, position, reset_value))

            except (ValueError, IndexError) as e:
                continue

    if current_reg_name and current_fields:
        reset_value = calculate_reset_value(current_fields)
        registers.append(Register(current_reg_raw_name, current_reg_offset, reset_value))

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
        header_content += f"  {{0x{reg.offset:04x}, 0x{reg.reset_value:04x}}}, // {reg.name}\n"

    header_content += "};\n"
    
    return header_content

def camel_to_snake(name):
    """Converts a CamelCase string to snake_case."""
    if not name:
        return ''
    result = [name[0].lower()]
    for char in name[1:]:
        if char.isupper():
            result.append('_')
        result.append(char.lower())
    return "".join(result)

def main():
    """Main execution function"""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_filepath = sys.argv[1]
    if not os.path.exists(input_filepath):
        print(f"Error: File not found at {input_filepath}")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    snake_case_name = camel_to_snake(base_name)
    output_filename = f"{snake_case_name}_golden.h"

    try:
        registers = parse_reg_map_file(input_filepath)
        h_code = generate_golden_h_code(registers)
        
        with open(output_filename, 'w') as f:
            f.write(h_code)
            
        print(f"Successfully generated {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()