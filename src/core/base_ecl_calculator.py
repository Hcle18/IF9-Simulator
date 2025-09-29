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
from src.ecl_calculation.get_terms import get_list_scenarios

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

    
    def get_scenarios(self):

        key = (self.data.operation_type, self.data.operation_status)
        list_scenarios_pd = get_list_scenarios(cst.PD_SHEET_MAPPING_CONFIG, key, self.data.template_data)
        list_scenarios_lgd = get_list_scenarios(cst.LGD_SHEET_MAPPING_CONFIG, key, self.data.template_data)
        list_scenarios_ccf = get_list_scenarios(cst.CCF_SHEET_MAPPING_CONFIG, key, self.data.template_data)

        self.data.list_scenarios = list(set(list_scenarios_pd + list_scenarios_lgd + list_scenarios_ccf))

    @abstractmethod
    def get_amortization_type(self):
        pass
    
    @abstractmethod
    def get_discount_factor(self):
        pass

    @abstractmethod
    def calcul_ecl(self):
        pass

    def calcul_ecl_multi(self):
        pass

