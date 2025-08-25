"""
Factory for creating ECL calculators based on operation type and status.
"""

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.core.base_ecl_calculator import BaseECLCalculator
from src.ecl_calculation.ecl_calculators import (
    NonRetailPerformingECLCalculator,
    RetailPerformingECLCalculator,
    RetailDefaultedECLCalculator
)

logger = logging.getLogger(__name__)


class ECLCalculatorFactory:
    """
    Factory class for creating appropriate ECL calculators based on operation type and status.
    """
    
    # Registry mapping operation type & status to ECL calculator classes
    _registry: Dict[tuple[cst.OperationType, cst.OperationStatus], Type[BaseECLCalculator]] = {
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NonRetailPerformingECLCalculator,
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): RetailPerformingECLCalculator,
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): RetailDefaultedECLCalculator,
    }
    
    @classmethod
    def create_calculator(cls, operation_type: cst.OperationType, 
                         operation_status: cst.OperationStatus) -> BaseECLCalculator:
        """
        Create the appropriate ECL calculator based on operation type and status.
        
        Args:
            operation_type: The type of operation (NON_RETAIL, RETAIL)
            operation_status: The status of operation (PERFORMING, DEFAULTED)
            
        Returns:
            BaseECLCalculator: The appropriate ECL calculator instance
            
        Raises:
            ValueError: If no calculator is found for the given operation type and status
        """
        key = (operation_type, operation_status)
        
        if key not in cls._registry:
            available_combinations = [
                f"{op_type.value}-{op_status.value}" 
                for op_type, op_status in cls._registry.keys()
            ]
            raise ValueError(
                f"No ECL calculator found for {operation_type.value} - {operation_status.value}. "
                f"Available combinations: {', '.join(available_combinations)}"
            )
        
        calculator_class = cls._registry[key]
        logger.info(f"Creating ECL calculator for {operation_type.value} - {operation_status.value}")
        
        return calculator_class()
    
    @classmethod
    def register_calculator(cls, operation_type: cst.OperationType,
                           operation_status: cst.OperationStatus,
                           calculator_class: Type[BaseECLCalculator]) -> None:
        """
        Register a new ECL calculator for a specific operation type and status.
        
        Args:
            operation_type: The operation type
            operation_status: The operation status
            calculator_class: The calculator class to register
        """
        key = (operation_type, operation_status)
        cls._registry[key] = calculator_class
        logger.info(f"Registered ECL calculator {calculator_class.__name__} for {operation_type.value} - {operation_status.value}")
    
    @classmethod
    def get_available_combinations(cls) -> list[tuple[cst.OperationType, cst.OperationStatus]]:
        """
        Get all available operation type and status combinations.
        
        Returns:
            List of tuples containing available combinations
        """
        return list(cls._registry.keys())
    
    @classmethod
    def get_calculator_info(cls) -> Dict[str, str]:
        """
        Get information about all registered calculators.
        
        Returns:
            Dictionary mapping combination keys to calculator class names
        """
        return {
            f"{op_type.value}-{op_status.value}": calculator_class.__name__
            for (op_type, op_status), calculator_class in cls._registry.items()
        }


# Convenience function for easy access
def create_ecl_calculator(operation_type: cst.OperationType,
                         operation_status: cst.OperationStatus) -> BaseECLCalculator:
    """
    Convenience function to create an ECL calculator.
    
    Args:
        operation_type: The type of operation
        operation_status: The status of operation
        
    Returns:
        BaseECLCalculator: The appropriate ECL calculator instance
    """
    return ECLCalculatorFactory.create_calculator(operation_type, operation_status)
