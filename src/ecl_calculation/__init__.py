"""
ECL Calculation module.

This module provides ECL calculation functionality through:
- BaseECLCalculator: Abstract base class defining the calculation interface
- Concrete calculators for different operation types and statuses
- ECLCalculatorFactory: Factory for creating appropriate calculators
- ECLCalculator: Main orchestrator class
"""

from ..core.base_ecl_calculator import BaseECLCalculator, ECLCalculationInputs, ECLCalculationResults
from .ecl_calculators import (
    NonRetailPerformingECLCalculator,
    RetailPerformingECLCalculator, 
    RetailDefaultedECLCalculator
)
from .ecl_calculator_factory import ECLCalculatorFactory, create_ecl_calculator
from .ecl_calculator import ECLCalculator

__all__ = [
    'BaseECLCalculator',
    'ECLCalculationInputs',
    'ECLCalculationResults',
    'NonRetailPerformingECLCalculator',
    'RetailPerformingECLCalculator',
    'RetailDefaultedECLCalculator', 
    'ECLCalculatorFactory',
    'create_ecl_calculator',
    'ECLCalculator'
]
