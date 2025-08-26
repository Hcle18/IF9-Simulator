# PD Segment Mapping Solution for IFRS9 ECL Calculations

## Overview

This solution provides a comprehensive framework for mapping PD (Probability of Default) segments from simulation data with PD segments in Excel template sheets to extract PD values for different time steps in IFRS9 Expected Credit Loss (ECL) calculations.

**🆕 NEW: Flexible Template Support** - The solution now supports flexible PD templates where **any column that doesn't start with "Time_step_"** can be considered as a driver for PD lookup. This means you're not limited to fixed columns like SEGMENT, SCENARIO, RATING anymore.

## Problem Statement

In IFRS9 ECL calculations, we need to:
1. Map PD segments from simulation data to corresponding segments in Excel templates
2. Extract PD values for specific time steps based on the mapping
3. Handle different economic scenarios (Base, Optimistic, Pessimistic)
4. Support flexible template structures with any number of driver columns
5. Create expanded datasets where each contract has multiple rows (one per time step)
6. Validate the mapping and handle edge cases

## Solution Architecture

### Core Components

1. **`get_terms.py`** - Main PD segment mapping module with flexible template support
2. **`ecl_calculator_with_pd.py`** - Enhanced ECL calculator with PD mapping
3. **Example files** - Comprehensive usage demonstrations

### Key Classes

#### 1. PDSegmentMapper (`get_terms.py`)

The core class responsible for flexible PD segment mapping.

**🆕 NEW Flexible Methods:**
- `get_driver_columns()` - Automatically detects all non-time-step columns as drivers
- `get_unique_values_for_driver()` - Gets unique values for any driver column
- `get_all_driver_combinations()` - Gets all unique combinations of driver values
- `map_pd_segments()` - Flexible mapping with custom driver mappings

**Legacy Methods (for backward compatibility):**
- `map_pd_segments_legacy()` - Original API with fixed SEGMENT, SCENARIO, RATING
- `get_available_segments()` - Legacy segment detection
- `get_available_scenarios()` - Legacy scenario detection

**Usage Examples:**

**New Flexible Approach:**
```python
# Create PD mapper
pd_mapper = create_pd_segment_mapper(ecl_operation_data)

# Let system auto-detect all drivers
pd_results = pd_mapper.map_pd_segments()

# Or specify custom driver mappings
driver_mappings = {
    'BUSINESS_LINE': 'PRODUCT_TYPE',
    'ECONOMIC_SCENARIO': 'SCENARIO_CODE', 
    'CREDIT_GRADE': 'INTERNAL_RATING',
    'GEOGRAPHY': 'REGION'
}
pd_results = pd_mapper.map_pd_segments(driver_mappings=driver_mappings)
```

**Legacy Approach (still supported):**
```python
pd_results = pd_mapper.map_pd_segments_legacy(
    segment_column='CALCULATION_RATING',
    scenario='BASE',
    default_segment='INVESTMENT_GRADE'
)
```

#### 2. ECLCalculatorWithPD (`ecl_calculator_with_pd.py`)

Enhanced ECL calculator that integrates PD mapping with time step calculations.

**Key Methods:**
- `get_time_steps()` - Calculates time steps for each contract
- `map_pd_segments()` - Maps PD segments using integrated mapper
- `create_expanded_dataset_with_pd()` - Creates expanded dataset with PD values
- `validate_pd_mapping()` - Validates PD mapping results
- `get_pd_statistics()` - Provides statistics about PD values

**Usage Example:**
```python
# Create enhanced ECL calculator
ecl_calculator = create_ecl_calculator_with_pd(ecl_operation_data)

# Calculate ECL with PD mapping
expanded_dataset = ecl_calculator.calculate_ecl_with_pd(
    segment_column='CALCULATION_RATING',
    scenario='BASE',
    default_segment='INVESTMENT_GRADE'
)
```

## Flexible Template Structure

### 🆕 NEW: Dynamic Driver Detection

The solution now automatically identifies driver columns in your PD template:

- **Driver Columns**: Any column that does NOT start with "Time_step_" (case insensitive)
- **Time Step Columns**: Any column that starts with "Time_step_"

### Example Flexible PD Template

| BUSINESS_LINE | ECONOMIC_SCENARIO | CREDIT_GRADE | GEOGRAPHY | Time_step_1 | Time_step_2 | Time_step_3 | ... |
|---------------|-------------------|--------------|-----------|-------------|-------------|-------------|-----|
| CORPORATE     | BASE             | IG           | EUR       | 0.001       | 0.0012      | 0.0015      | ... |
| CORPORATE     | OPTIMISTIC       | IG           | EUR       | 0.0008      | 0.001       | 0.0012      | ... |
| RETAIL        | BASE             | IG           | US        | 0.002       | 0.0025      | 0.003       | ... |
| SME           | PESSIMISTIC      | SIG          | ASIA      | 0.008       | 0.01        | 0.012       | ... |

In this example:
- **Driver Columns**: BUSINESS_LINE, ECONOMIC_SCENARIO, CREDIT_GRADE, GEOGRAPHY
- **Time Step Columns**: Time_step_1, Time_step_2, Time_step_3, ...

### Automatic Driver Mapping

The system can automatically map simulation data columns to template driver columns based on naming patterns:

```python
# Automatic detection based on column names
driver_mappings = {
    'BUSINESS_LINE': 'PRODUCT_CODE',      # Maps to simulation column
    'ECONOMIC_SCENARIO': 'SCENARIO',      # Maps to simulation column  
    'CREDIT_GRADE': 'RATING',            # Maps to simulation column
    'GEOGRAPHY': None                     # Uses default value
}
```

### Custom Driver Mappings

You can also specify exact mappings:

```python
custom_mappings = {
    'BUSINESS_LINE': 'BUSINESS_SEGMENT',
    'ECONOMIC_SCENARIO': 'MACRO_SCENARIO',
    'CREDIT_GRADE': 'INTERNAL_RATING',
    'GEOGRAPHY': 'COUNTRY_CODE'
}

default_values = {
    'ECONOMIC_SCENARIO': 'BASE',
    'GEOGRAPHY': 'GLOBAL'
}

pd_results = pd_mapper.map_pd_segments(
    driver_mappings=custom_mappings,
    default_values=default_values
)
```

```
Simulation Data + Template Data
         ↓
    PDSegmentMapper
         ↓
1. Extract available segments/scenarios from template
2. Map simulation segments to template segments
3. Look up PD values for each time step
4. Handle unmapped segments with defaults
         ↓
    PD Results DataFrame
         ↓
    ECLCalculatorWithPD
         ↓
1. Calculate time steps for each contract
2. Merge with PD values
3. Expand to one row per time step
4. Add time step information
         ↓
    Expanded Dataset for ECL Calculation
```

## Key Features

### 1. Flexible Segment Mapping

The solution includes a customizable segment mapping function:

```python
def _map_simulation_segment_to_template_segment(self, simulation_segment: str) -> str:
    # Example mapping logic
    if segment in ['A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-']:
        return 'INVESTMENT_GRADE'
    elif segment in ['BB+', 'BB', 'BB-', 'B+', 'B', 'B-']:
        return 'SUB_INVESTMENT_GRADE'
    # ... more mapping rules
```

### 2. Multi-Scenario Support

Supports different economic scenarios:
- **BASE** - Base case scenario
- **OPTIMISTIC** - Optimistic economic scenario  
- **PESSIMISTIC** - Pessimistic economic scenario

### 3. Time Step Integration

Integrates with existing time step calculations to create a complete dataset:

```python
# Each contract gets expanded to multiple rows
Contract_001, Time_Step_1, PD_Value_1, 3_months
Contract_001, Time_Step_2, PD_Value_2, 6_months
Contract_001, Time_Step_3, PD_Value_3, 12_months
...
```

### 4. Comprehensive Validation

Built-in validation checks for:
- Missing segments or ratings
- Invalid PD values (negative, > 1)
- Unmapped contracts
- Template data consistency

## Example Output Structure

### PD Mapping Results

| CONTRACT_ID | SEGMENT_ORIGINAL | SEGMENT_MAPPED | RATING | SCENARIO | PD_TIME_STEP_1 | PD_TIME_STEP_2 | ... |
|-------------|------------------|----------------|--------|----------|----------------|----------------|-----|
| C001 | AAA | INVESTMENT_GRADE | AAA | BASE | 0.001234 | 0.001456 | ... |
| C002 | BB+ | SUB_INVESTMENT_GRADE | BB+ | BASE | 0.012345 | 0.014567 | ... |

### Expanded Dataset for ECL

| CONTRACT_ID | TIME_STEP | TIME_STEP_MONTHS | PD_VALUE | SEGMENT_MAPPED | ... |
|-------------|-----------|------------------|----------|----------------|-----|
| C001 | 1 | 3 | 0.001234 | INVESTMENT_GRADE | ... |
| C001 | 2 | 6 | 0.001456 | INVESTMENT_GRADE | ... |
| C001 | 3 | 12 | 0.001678 | INVESTMENT_GRADE | ... |
| C002 | 1 | 3 | 0.012345 | SUB_INVESTMENT_GRADE | ... |

## Configuration

### Template Sheet Configuration

The solution uses configuration in `config.py` to define which template sheets contain PD data:

```python
pd_sheet_mapping = {
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F6-PD S1S2 Non Retail",
    (OperationType.RETAIL, OperationStatus.PERFORMING): "F6-PD S1S2 Retail",
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "F6-PD S3 Retail"
}
```

### Required Template Columns

- **SEGMENT** - PD segment identifier
- **SCENARIO** - Economic scenario (BASE, OPTIMISTIC, PESSIMISTIC)
- **RATING** - Credit rating
- **TIME_STEP_1, TIME_STEP_2, ...** - PD values for each time step

### Required Simulation Data Columns

- **CONTRACT_ID** - Unique contract identifier
- **CALCULATION_RATING** - Rating/segment for PD lookup
- **EXPOSURE_END_DATE** - Contract maturity date
- **AS_OF_DATE** - Calculation date

## Usage Examples

### Basic Usage

```python
from src.ecl_calculation.get_terms import get_pd_for_simulation_data

# Simple PD mapping
pd_results = get_pd_for_simulation_data(
    ecl_operation_data=ecl_data,
    segment_column='CALCULATION_RATING',
    scenario='BASE'
)
```

### Advanced Usage with ECL Calculator

```python
from src.ecl_calculation.ecl_calculator_with_pd import create_ecl_calculator_with_pd

# Create enhanced calculator
calculator = create_ecl_calculator_with_pd(ecl_data)

# Full ECL calculation with PD mapping
expanded_dataset = calculator.calculate_ecl_with_pd(
    segment_column='CALCULATION_RATING',
    scenario='BASE',
    default_segment='INVESTMENT_GRADE'
)
```

### Scenario Comparison

```python
scenarios = ['BASE', 'OPTIMISTIC', 'PESSIMISTIC']
scenario_results = {}

for scenario in scenarios:
    pd_results = pd_mapper.map_pd_segments(
        segment_column='CALCULATION_RATING',
        scenario=scenario
    )
    scenario_results[scenario] = pd_results
```

## Error Handling

The solution includes comprehensive error handling for:

1. **Missing Template Data**
   - Graceful handling when PD template sheets are missing
   - Clear error messages for debugging

2. **Unmapped Segments**
   - Support for default segments
   - Logging of unmapped segment-rating combinations

3. **Invalid PD Values**
   - Detection of negative or > 1 PD values
   - Validation warnings for unusual values

4. **Data Consistency**
   - Validation of required columns
   - Check for empty datasets

## Performance Considerations

1. **Efficient Lookups** - Uses dictionary-based mapping for fast PD lookups
2. **Vectorized Operations** - Uses pandas operations where possible
3. **Memory Management** - Processes data in chunks for large datasets
4. **Caching** - Caches template data to avoid repeated reads

## Integration with Existing System

The solution is designed to integrate seamlessly with the existing IFRS9 simulation system:

- **Uses existing ECLOperationData container**
- **Compatible with existing data loaders**
- **Extends existing ECL calculator base classes**
- **Follows established logging and error handling patterns**

## Testing and Validation

Example files provided for testing:

1. **`pd_segment_mapping_examples.py`** - Basic PD mapping demonstrations
2. **`complete_pd_mapping_workflow.py`** - Complete workflow example

Run examples to validate the solution:
```bash
python examples/complete_pd_mapping_workflow.py
```

## Customization

### Custom Segment Mapping

Override the `_map_simulation_segment_to_template_segment` method to implement custom business logic:

```python
class CustomPDSegmentMapper(PDSegmentMapper):
    def _map_simulation_segment_to_template_segment(self, simulation_segment: str) -> str:
        # Your custom mapping logic here
        return mapped_segment
```

### Custom Validation Rules

Extend the validation methods to add custom business rules:

```python
class CustomECLCalculator(ECLCalculatorWithPD):
    def validate_pd_mapping(self, **kwargs):
        # Call parent validation
        results = super().validate_pd_mapping(**kwargs)
        
        # Add custom validation rules
        # ...
        
        return results
```

## Conclusion

This solution provides a robust, flexible, and comprehensive framework for mapping PD segments between simulation data and Excel templates. It handles complex business requirements while maintaining integration with the existing IFRS9 simulation system.

The modular design allows for easy customization and extension, while the comprehensive validation and error handling ensure reliable operation in production environments.
