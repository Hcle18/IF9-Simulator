"""
Abstract base class for ECL calculation strategies.

This module defines the interface for ECL calculators that handle different combinations
of operation types (Retail/Non-Retail) and operation status (Performing/Defaulted).
"""

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.core import base_data as bcls
from src.core import base_template as tplm

logger = logging.getLogger(__name__)

class BaseECLCalculator(ABC):
    """
    Abstract base class for ECL calculation strategies.
    
    Each concrete implementation handles a specific combination of:
    - Operation type (Retail, Non-Retail)  
    - Operation status (Performing, Defaulted)
    """

    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize BaseECLCalculator with ECLOperationData.
        
        Args:
            ecl_operation_data: Container with all necessary data for ECL calculation
        """
        self.data = ecl_operation_data
        # self.df = ecl_operation_data.df
        # self.operation_type = ecl_operation_data.operation_type
        # self.status = ecl_operation_data.operation_status
        # self.template_data = ecl_operation_data.template_data

    @abstractmethod
    def get_time_steps(self):
        pass

