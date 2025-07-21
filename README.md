# C++ Register Map Class Generator

This Python script automatically generates a C++ class and register definitions from a plain text register map description. It's designed to reduce manual errors and streamline the process of updating memory-mapped register definitions in embedded projects.

The script parses a specially formatted text file, calculates register offsets from a base address, determines reset values from bitfield definitions, and generates a C++ file containing:
- `constexpr` for register offsets.
- A C++ class with a `reset` method to initialize the registers to their default values.

## Prerequisites

- Python 3

## Usage

Run the script from your terminal, providing the path to the input register map file.

```bash
python cpp_generator.py <input_file.txt>
```

The script will automatically create a C++ file named after the input file (e.g., `MyModule.txt` -> `my_module.cpp`).

## Example

### 1. Input File (`example_map.txt`)

Create a text file that describes the registers. The format is as follows:
- Each line for a new register must contain: `register_name address field_name RW [bit_range] reset_value`.
- Additional fields for the same register are listed on subsequent lines, indented with spaces.
- The base address is inferred from the first register's address.

```
# [Register Name] [Address] [Field Name] [RW] [Bit Range] [Reset Value]
# Indented lines are for additional fields in the register above.

SYS_CTRL_1 0x50001002  ENABLE_FEATURE_A RW [0:0]     0x1
  ENABLE_FEATURE_B RW [1:1]  0x0
  MODE_SELECT RW [7:4]  0x5

SYS_CTRL_2 0x50001004  ENABLE_CLK RW [15:0]     0xFFFF

DEV_STATUS 0x50001006 DEV_READY RW [0:0]                  0x0
  DEV_ERROR RW [1:1]  0x0

DEV_ID 0x500010a4 CHIP_VERSION RW [7:0]               0xA2
  CHIP_REVISION RW [15:8]  0x01
```

### 2. Running the Generator

```bash
python cpp_generator.py example_map.txt
```

### 3. Output File (`example_map.cpp`)

The script will generate the following C++ code in `example_map.cpp`:

```cpp
// EXAMPLE_MAP_APB_S BaseAddress : 0x50001000
constexpr size_t CNT_REG_END = 0xa4;
constexpr size_t REG_BYTE_WIDTH = 0x2;

constexpr size_t SYS_CTRL_1 = 0x002;
constexpr size_t SYS_CTRL_2 = 0x004;
constexpr size_t DEV_STATUS = 0x006;
constexpr size_t DEV_ID = 0x0a4;

class ExampleMap: public vp::Component {
  public:
    ExampleMap(const Config& conf);
    ~ExampleMap() override = default;

    void reset(bool active);
  private:
    uint16_t reg[CNT_REG_END / REG_BYTE_WIDTH + 1];
};

void ExampleMap::reset(bool active) {
  if (active) {
    reg[SYS_CTRL_1 / REG_BYTE_WIDTH] = 0x51;
    reg[SYS_CTRL_2 / REG_BYTE_WIDTH] = 0xffff;
    reg[DEV_STATUS / REG_BYTE_WIDTH] = 0x0;
    reg[DEV_ID / REG_BYTE_WIDTH] = 0x1a2;
  }
}
```

## Golden Header Generator

This Python script generates a C++ header file containing golden values for register reset states. It parses the same register map file and creates a `std::vector` of `RegInfo` structs, each holding a register's offset and its expected reset value. This is useful for verification and testing purposes.

### Usage

Run the script from your terminal, providing the path to the input register map file.

```bash
python golden_h_generator.py <input_file.txt>
```

The script will create a C++ header file named in snake_case based on the input file name (e.g., `MyModule.txt` -> `my_module_golden.h`).

### Example

#### 1. Input File (`example_map.txt`)

Using the same `example_map.txt` as before.

#### 2. Running the Generator

```bash
python golden_h_generator.py example_map.txt
```

#### 3. Output File (`example_map_golden.h`)

The script will generate the following C++ header file:

```cpp
#pragma once

#include <cstdint>
#include <vector>

struct RegInfo {
  uint32_t offset;
  uint16_t expected_value;
};

std::vector<RegInfo> golden_regs = {
  {0x0002, 0x0051}, // SYS_CTRL_1
  {0x0004, 0xffff}, // SYS_CTRL_2
  {0x0006, 0x0000}, // DEV_STATUS
  {0x00a4, 0x01a2}, // DEV_ID
};
```
