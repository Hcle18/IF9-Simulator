# ECL Calculation Architecture

## Overview

This document describes the new ECL (Expected Credit Loss) calculation architecture implemented using the Strategy Pattern with Abstract Base Classes. The design allows for flexible ECL calculations based on different combinations of operation types and statuses while maintaining a consistent interface.

## Architecture Components

### 1. Base Abstract Class (`BaseECLCalculator`)

The `BaseECLCalculator` defines the common interface and workflow for all ECL calculations:

```python
from src.ecl_calculation import BaseECLCalculator

# All concrete calculators inherit from this base class
class BaseECLCalculator(ABC):
    # Template method that orchestrates the calculation process
    def calculate_ecl(self, inputs: ECLCalculationInputs) -> ECLCalculationResults
    
    # Abstract methods that must be implemented by concrete classes
    @abstractmethod
    def _calculate_residual_maturity(self, inputs: ECLCalculationInputs) -> pd.DataFrame
    
    @abstractmethod  
    def _calculate_ead_amortization(self, inputs, residual_maturity) -> pd.DataFrame
    
    @abstractmethod
    def _determine_pd_values(self, inputs, residual_maturity) -> pd.DataFrame
    
    @abstractmethod
    def _determine_lgd_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame
    
    @abstractmethod
    def _determine_ccf_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame
    
    @abstractmethod
    def _calculate_final_ecl(self, inputs, ...) -> tuple[pd.DataFrame, pd.DataFrame, Dict]
```

### 2. Concrete Calculator Implementations

Each combination of operation type and status has its own specialized calculator:

#### Non-Retail Performing (`NonRetailPerformingECLCalculator`)
- Handles complex multi-scenario PD calculations
- Uses time-stepped EAD amortization
- Implements segment-based risk parameters
- **Status**: ✅ Fully implemented

#### Retail Performing (`RetailPerformingECLCalculator`) 
- Specialized for retail performing operations
- **Status**: 🚧 Placeholder implementation (to be customized)

#### Retail Defaulted (`RetailDefaultedECLCalculator`)
- Handles defaulted retail exposures
- Different logic for PD (typically 1.0), EAD, and CCF
- **Status**: 🚧 Placeholder implementation (to be customized)

### 3. Factory Pattern (`ECLCalculatorFactory`)

The factory creates the appropriate calculator based on operation type and status:

```python
from src.ecl_calculation import create_ecl_calculator
from src.core.constants import OperationType, OperationStatus

# Create calculator for Non-Retail Performing
calculator = create_ecl_calculator(
    OperationType.NON_RETAIL, 
    OperationStatus.PERFORMING
)

# The factory automatically selects NonRetailPerformingECLCalculator
```

### 4. Main Orchestrator (`ECLCalculator`)

The main class that coordinates the entire ECL calculation process:

```python
from src.ecl_calculation import ECLCalculator

# Initialize for specific operation type/status
ecl_calc = ECLCalculator(OperationType.NON_RETAIL, OperationStatus.PERFORMING)

# Load template and data
ecl_calc.load_template("path/to/template.xlsx")
ecl_calc.load_simulation_data("path/to/data.zip")

# Calculate ECL
results = ecl_calc.calculate_ecl(as_of_date, scenarios)
```

## Data Flow

```
1. Template Loading & Validation
   ├── Uses TemplateLoader (existing)
   └── Validates required sheets and fields

2. Simulation Data Loading  
   ├── Uses DataLoader (existing)
   └── Imports from Excel/ZIP files

3. ECL Calculation Strategy Selection
   ├── Factory creates appropriate calculator
   └── Based on OperationType + OperationStatus

4. ECL Calculation Process
   ├── Input validation
   ├── Residual maturity calculation
   ├── EAD amortization calculation
   ├── PD determination
   ├── LGD determination
   ├── CCF determination
   └── Final ECL calculation

5. Results Export
   ├── Excel format (multiple sheets)
   └── CSV format (separate files)
```

## Usage Examples

### Basic Usage

```python
import pandas as pd
from src.core.constants import OperationType, OperationStatus
from src.ecl_calculation import ECLCalculator

# Initialize calculator
calc = ECLCalculator(OperationType.NON_RETAIL, OperationStatus.PERFORMING)

# Load data
calc.load_template("template.xlsx")
calc.load_simulation_data("data.zip")

# Calculate ECL
as_of_date = pd.Timestamp('2024-12-31')
scenarios = ['Base', 'Adverse', 'Severe']
results = calc.calculate_ecl(as_of_date, scenarios)

# Export results
calc.export_results("ecl_results.xlsx")
```

### Factory Usage

```python
from src.ecl_calculation import ECLCalculatorFactory

# Get available combinations
combinations = ECLCalculatorFactory.get_available_combinations()
print("Available:", combinations)

# Create specific calculator
calculator = ECLCalculatorFactory.create_calculator(
    OperationType.RETAIL, 
    OperationStatus.PERFORMING
)
```

## Extending the Architecture

### Adding New Calculator

To add support for new operation combinations (e.g., Non-Retail Defaulted):

1. **Create new calculator class**:
```python
class NonRetailDefaultedECLCalculator(BaseECLCalculator):
    def __init__(self):
        super().__init__(OperationType.NON_RETAIL, OperationStatus.DEFAULTED)
    
    # Implement all abstract methods
    def _calculate_residual_maturity(self, inputs):
        # Custom implementation for Non-Retail Defaulted
        pass
    
    # ... other methods
```

2. **Register with factory**:
```python
ECLCalculatorFactory.register_calculator(
    OperationType.NON_RETAIL,
    OperationStatus.DEFAULTED,
    NonRetailDefaultedECLCalculator
)
```

### Customizing Existing Calculators

Each calculator can be customized by overriding specific methods:

```python
class CustomNonRetailCalculator(NonRetailPerformingECLCalculator):
    def _calculate_ead_amortization(self, inputs, residual_maturity):
        # Custom EAD calculation logic
        return super()._calculate_ead_amortization(inputs, residual_maturity)
```

## Benefits of This Architecture

1. **🔄 Flexibility**: Easy to add new operation types/statuses
2. **🔧 Maintainability**: Each combination has its own isolated implementation  
3. **🧪 Testability**: Each calculator can be tested independently
4. **♻️ Reusability**: Common functionality in base class, specific logic in concrete classes
5. **📖 Clarity**: Clear separation of concerns and well-defined interfaces
6. **🏗️ Extensibility**: Factory pattern allows easy registration of new calculators

## File Structure

```
src/ecl_calculation/
├── __init__.py                     # Module exports
├── base_ecl_calculator.py          # Abstract base class & data containers
├── ecl_calculators.py              # Concrete calculator implementations  
├── ecl_calculator_factory.py       # Factory for creating calculators
└── ecl_calculator.py               # Main orchestrator class

examples/
└── ecl_calculation_examples.py     # Usage examples
```

## Integration with Existing Code

This new architecture integrates seamlessly with your existing codebase:

- ✅ Uses existing `TemplateLoader` and `DataLoader` components
- ✅ Maintains the same `OperationType` and `OperationStatus` enums
- ✅ Leverages existing `ecl_param_timesteps` utility functions
- ✅ Follows the same logging and error handling patterns

## Next Steps

1. **Complete Retail implementations**: Implement the placeholder methods in `RetailPerformingECLCalculator` and `RetailDefaultedECLCalculator`
2. **Add Non-Retail Defaulted**: Create calculator for Non-Retail S3 operations  
3. **Enhanced validation**: Add more sophisticated input validation for each calculator type
4. **Performance optimization**: Add caching and parallel processing for large datasets
5. **Unit testing**: Create comprehensive test suites for each calculator

This architecture provides a robust foundation for ECL calculations while maintaining flexibility for future requirements and enhancements.
