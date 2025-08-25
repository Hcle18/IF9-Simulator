"""
Example usage of the ECL calculation system.

This script demonstrates how to use the new ECL calculation architecture
with different operation types and statuses.
"""

import pandas as pd
from pathlib import Path
import logging

# Local imports
from core import config as cst
from src.ecl_calculation import ECLCalculator
from src.utils.logging_config import setup_logging

# Setup logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)


def example_non_retail_performing():
    """
    Example ECL calculation for Non-Retail Performing operations.
    """
    logger.info("=" * 60)
    logger.info("Example: Non-Retail Performing ECL Calculation")
    logger.info("=" * 60)
    
    try:
        # Initialize ECL Calculator
        ecl_calculator = ECLCalculator(
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING
        )
        
        # Load template
        template_path = "sample/templates/Template_outil_V1.xlsx"
        if not ecl_calculator.load_template(template_path):
            logger.error("Failed to load template")
            return
        
        # Load simulation data
        data_path = "sample/data/sample_non_retail.zip"
        if not ecl_calculator.load_simulation_data(data_path):
            logger.error("Failed to load simulation data")
            return
        
        # Define calculation parameters
        as_of_date = pd.Timestamp('2024-12-31')
        scenarios = ['Base', 'Adverse', 'Severe']
        
        # Calculate ECL
        results = ecl_calculator.calculate_ecl(as_of_date, scenarios)
        
        # Print summary
        summary = ecl_calculator.get_calculation_summary()
        logger.info("Calculation Summary:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")
        
        # Export results
        ecl_calculator.export_results("output/non_retail_performing_ecl.xlsx", "excel")
        
        logger.info("Non-Retail Performing ECL calculation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in Non-Retail Performing example: {e}")


def example_retail_performing():
    """
    Example ECL calculation for Retail Performing operations.
    """
    logger.info("=" * 60)
    logger.info("Example: Retail Performing ECL Calculation")
    logger.info("=" * 60)
    
    try:
        # Initialize ECL Calculator
        ecl_calculator = ECLCalculator(
            operation_type=cst.OperationType.RETAIL,
            operation_status=cst.OperationStatus.PERFORMING
        )
        
        # Note: This would need retail-specific template and data files
        logger.info("Retail Performing calculator created successfully")
        logger.info("Implementation details to be completed based on retail requirements")
        
    except Exception as e:
        logger.error(f"Error in Retail Performing example: {e}")


def example_retail_defaulted():
    """
    Example ECL calculation for Retail Defaulted operations.
    """
    logger.info("=" * 60)
    logger.info("Example: Retail Defaulted ECL Calculation")
    logger.info("=" * 60)
    
    try:
        # Initialize ECL Calculator
        ecl_calculator = ECLCalculator(
            operation_type=cst.OperationType.RETAIL,
            operation_status=cst.OperationStatus.DEFAULTED
        )
        
        # Note: This would need retail S3-specific template and data files
        logger.info("Retail Defaulted calculator created successfully")
        logger.info("Implementation details to be completed based on retail S3 requirements")
        
    except Exception as e:
        logger.error(f"Error in Retail Defaulted example: {e}")


def demonstrate_factory_usage():
    """
    Demonstrate the factory pattern usage.
    """
    logger.info("=" * 60)
    logger.info("Demonstrating ECL Calculator Factory")
    logger.info("=" * 60)
    
    from src.ecl_calculation import ECLCalculatorFactory, create_ecl_calculator
    
    # Show available combinations
    available_combinations = ECLCalculatorFactory.get_available_combinations()
    logger.info("Available ECL calculator combinations:")
    for op_type, op_status in available_combinations:
        logger.info(f"  - {op_type.value} {op_status.value}")
    
    # Show calculator info
    calculator_info = ECLCalculatorFactory.get_calculator_info()
    logger.info("Calculator implementations:")
    for combination, calculator_class in calculator_info.items():
        logger.info(f"  - {combination}: {calculator_class}")
    
    # Create calculators using factory
    logger.info("Creating calculators using factory:")
    for op_type, op_status in available_combinations:
        calculator = create_ecl_calculator(op_type, op_status)
        metadata = calculator.get_calculation_metadata()
        logger.info(f"  Created: {metadata['calculator_class']} for {metadata['description']}")


if __name__ == "__main__":
    """
    Main execution - run all examples
    """
    logger.info("Starting ECL Calculation Examples")
    
    # Create output directory
    Path("output").mkdir(exist_ok=True)
    
    # Run examples
    demonstrate_factory_usage()
    example_non_retail_performing()
    example_retail_performing()
    example_retail_defaulted()
    
    logger.info("All examples completed!")
