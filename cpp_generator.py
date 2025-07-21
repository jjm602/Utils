

import sys
import os
import re
from collections import namedtuple

Field = namedtuple('Field', ['name', 'position', 'reset_value'])
Register = namedtuple('Register', ['name', 'offset', 'reset_value'])

def parse_bit_position(pos_str):
    "'[15:0]' 형식의 문자열에서 시작 비트(0)를 파싱합니다."
    match = re.search(r':(\d+)', pos_str)
    return int(match.group(1)) if match else 0

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

    with open(filepath, 'r') as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            
            # 두 번째 요소가 '0x'로 시작하면 주소로 간주하여 새 레지스터 라인으로 처리
            is_new_register = len(parts) > 1 and parts[1].startswith('0x')

            try:
                if is_new_register:
                    # 이전 레지스터 정보가 있다면 저장
                    if current_reg_name and current_fields:
                        reset_value = calculate_reset_value(current_fields)
                        registers.append(Register(current_reg_name, current_reg_offset, reset_value))
                    
                    # 새 레지스터 파싱 시작
                    current_fields = []
                    
                    # 포맷: reg_name address field_name [permission] position reset_val
                    if len(parts) < 5:
                        print(f"Warning: L{line_num}: Skipping malformed register line. Not enough parts. ('{line}')")
                        current_reg_name = None
                        continue

                    reg_name, address_str, field_name, *rest = parts
                    position = rest[-2]
                    reset_str = rest[-1]

                    address = int(address_str, 16)
                    if base_address is None:
                        base_address = address & 0xFFFFF000 # e.g., 0x40007000
                    
                    current_reg_name = reg_name.upper()
                    current_reg_offset = address - base_address
                    
                    reset_value = int(reset_str, 16)
                    current_fields.append(Field(field_name, position, reset_value))

                else: # 필드 라인으로 처리
                    if not current_reg_name:
                        print(f"Warning: L{line_num}: Skipping field line with no active register ('{line}')")
                        continue
                    
                    # 포맷: field_name [permission] position reset_val
                    if len(parts) < 3:
                        print(f"Warning: L{line_num}: Skipping malformed field line. Not enough parts. ('{line}')")
                        continue

                    field_name, *rest = parts
                    position = rest[-2]
                    reset_str = rest[-1]
                        
                    reset_value = int(reset_str, 16)
                    current_fields.append(Field(field_name, position, reset_value))

            except (ValueError, IndexError) as e:
                print(f"Warning: L{line_num}: Could not parse line '{line}'. Error: {e}")
                continue

    # 파일 끝에 도달했을 때 마지막 레지스터 정보 저장
    if current_reg_name and current_fields:
        reset_value = calculate_reset_value(current_fields)
        registers.append(Register(current_reg_name, current_reg_offset, reset_value))

    return registers, base_address


def generate_cpp_code(registers, base_address, class_name):
    "파싱된 레지스터 정보로 C++ 코드를 생성합니다."
    
    max_offset = 0
    if registers:
        max_offset = max(r.offset for r in registers)

    # 1. 헤더 및 상수 정의
    cpp = f"// {class_name.upper()}_APB_S BaseAddress : {hex(base_address)}\n"
    cpp += f"constexpr size_t CNT_REG_END = 0x{max_offset:x};\n"
    cpp += "constexpr size_t REG_BYTE_WIDTH = 0x2;\n\n"

    # 2. 레지스터 오프셋 정의
    for reg in registers:
        cpp += f"constexpr size_t {reg.name} = 0x{reg.offset:03x};\n"
    cpp += "\n"

    # 3. 클래스 정의
    cpp += f"class {class_name}: public vp::Component {{\n"
    cpp += "  public:\n"
    cpp += f"    {class_name}(const Config& conf);\n"
    cpp += f"    ~{class_name}() override = default;\n\n"
    cpp += "    void reset(bool active);\n"
    cpp += "  private:\n"
    cpp += "    uint16_t reg[CNT_REG_END / REG_BYTE_WIDTH + 1];\n"
    cpp += "};\n\n"

    # 4. 리셋 함수 구현
    cpp += f"void {class_name}::reset(bool active) {{\n"
    cpp += "  if (active) {\n"
    for reg in registers:
        cpp += f"    reg[{reg.name} / REG_BYTE_WIDTH] = 0x{reg.reset_value:x};\n"
    cpp += "  }\n"
    cpp += "}\n"

    return cpp

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
    """메인 실행 함수"""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_filepath = sys.argv[1]
    if not os.path.exists(input_filepath):
        print(f"Error: File not found at {input_filepath}")
        sys.exit(1)

    # 클래스 및 파일명 생성
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    class_name = base_name
    # Convert CamelCase class name to snake_case for the filename
    snake_case_name = camel_to_snake(base_name)
    output_filename = snake_case_name + ".cpp"

    try:
        registers, base_address = parse_reg_map_file(input_filepath)
        cpp_code = generate_cpp_code(registers, base_address, class_name)
        
        with open(output_filename, 'w') as f:
            f.write(cpp_code)
            
        print(f"Successfully generated {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

