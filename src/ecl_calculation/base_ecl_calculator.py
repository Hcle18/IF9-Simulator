"""
Abstract base class for ECL calculation strategies.

This module defines the interface for ECL calculators that handle different combinations
of operation types (Retail/Non-Retail) and operation status (Performing/Defaulted).
"""

# Global import
from src.core.librairies import *

# Local imports
from core import config as cst

logger = logging.getLogger(__name__)

@dataclass
class ECLCalculationInputs:
    """
    Container for ECL calculation inputs.
    """
    simulation_data: pd.DataFrame
    template_data: Dict[str, pd.DataFrame]
    as_of_date: pd.Timestamp
    scenarios: List[str]
    operation_type: cst.OperationType
    operation_status: cst.OperationStatus

@dataclass  
class ECLCalculationResults:
    """
    Container for ECL calculation results.
    """
    ecl_by_exposure: pd.DataFrame
    ecl_summary: pd.DataFrame
    calculation_details: Dict[str, Any]
    residual_maturity: pd.DataFrame
    ead_amortization: pd.DataFrame
    pd_values: pd.DataFrame
    lgd_values: pd.DataFrame
    ccf_values: pd.DataFrame

class BaseECLCalculator(ABC):
    """
    Abstract base class for ECL calculation strategies.
    
    Each concrete implementation handles a specific combination of:
    - Operation type (Retail, Non-Retail)  
    - Operation status (Performing, Defaulted)
    """
    
    def __init__(self, operation_type: cst.OperationType, operation_status: cst.OperationStatus):
        self.operation_type = operation_type
        self.operation_status = operation_status
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_ecl(self, inputs: ECLCalculationInputs) -> ECLCalculationResults:
        """
        Main ECL calculation method that orchestrates the entire calculation process.
        
        This template method follows these steps:
        1. Validate inputs
        2. Calculate residual maturity
        3. Calculate EAD amortization
        4. Determine PD values
        5. Determine LGD values
        6. Determine CCF values
        7. Calculate final ECL
        
        Args:
            inputs: ECLCalculationInputs containing all required data
            
        Returns:
            ECLCalculationResults with all calculated values
        """
        self.logger.info(f"Starting ECL calculation for {self.operation_type.value} - {self.operation_status.value}")
        
        # Step 1: Validate inputs
        self._validate_inputs(inputs)
        
        # Step 2: Calculate residual maturity
        self.logger.info("Calculating residual maturity...")
        residual_maturity = self._calculate_residual_maturity(inputs)
        
        # Step 3: Calculate EAD amortization
        self.logger.info("Calculating EAD amortization...")
        ead_amortization = self._calculate_ead_amortization(inputs, residual_maturity)
        
        # Step 4: Determine PD values
        self.logger.info("Determining PD values...")
        pd_values = self._determine_pd_values(inputs, residual_maturity)
        
        # Step 5: Determine LGD values
        self.logger.info("Determining LGD values...")
        lgd_values = self._determine_lgd_values(inputs)
        
        # Step 6: Determine CCF values
        self.logger.info("Determining CCF values...")
        ccf_values = self._determine_ccf_values(inputs)
        
        # Step 7: Calculate final ECL
        self.logger.info("Calculating final ECL...")
        ecl_by_exposure, ecl_summary, calculation_details = self._calculate_final_ecl(
            inputs, residual_maturity, ead_amortization, pd_values, lgd_values, ccf_values
        )
        
        self.logger.info("ECL calculation completed successfully")
        
        return ECLCalculationResults(
            ecl_by_exposure=ecl_by_exposure,
            ecl_summary=ecl_summary,
            calculation_details=calculation_details,
            residual_maturity=residual_maturity,
            ead_amortization=ead_amortization,
            pd_values=pd_values,
            lgd_values=lgd_values,
            ccf_values=ccf_values
        )
    
    def _validate_inputs(self, inputs: ECLCalculationInputs) -> None:
        """
        Validate that all required inputs are present and valid.
        
        Args:
            inputs: ECLCalculationInputs to validate
            
        Raises:
            ValueError: If inputs are invalid
        """
        if inputs.simulation_data is None or inputs.simulation_data.empty:
            raise ValueError("Simulation data is required and cannot be empty")
            
        if not inputs.template_data:
            raise ValueError("Template data is required")
            
        if inputs.as_of_date is None:
            raise ValueError("As of date is required")
            
        if not inputs.scenarios:
            raise ValueError("At least one scenario is required")
        
        # Additional validation can be added by concrete classes
        self._perform_specific_input_validation(inputs)
    
    @abstractmethod
    def _perform_specific_input_validation(self, inputs: ECLCalculationInputs) -> None:
        """
        Perform validation specific to the operation type and status.
        
        Args:
            inputs: ECLCalculationInputs to validate
        """
        pass
    
    @abstractmethod
    def _calculate_residual_maturity(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Calculate residual maturity for each exposure.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            
        Returns:
            DataFrame with residual maturity calculations
        """
        pass
    
    @abstractmethod
    def _calculate_ead_amortization(self, inputs: ECLCalculationInputs, 
                                   residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EAD (Exposure at Default) amortization over time.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            residual_maturity: Previously calculated residual maturity
            
        Returns:
            DataFrame with EAD amortization schedule
        """
        pass
    
    @abstractmethod
    def _determine_pd_values(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Determine Probability of Default (PD) values.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            residual_maturity: Previously calculated residual maturity
            
        Returns:
            DataFrame with PD values by scenario and time period
        """
        pass
    
    @abstractmethod
    def _determine_lgd_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine Loss Given Default (LGD) values.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            
        Returns:
            DataFrame with LGD values by scenario
        """
        pass
    
    @abstractmethod
    def _determine_ccf_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine Credit Conversion Factor (CCF) values.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            
        Returns:
            DataFrame with CCF values by scenario
        """
        pass
    
    @abstractmethod
    def _calculate_final_ecl(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame,
                            ead_amortization: pd.DataFrame,
                            pd_values: pd.DataFrame,
                            lgd_values: pd.DataFrame,
                            ccf_values: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Calculate the final ECL using all previously calculated components.
        
        Args:
            inputs: ECLCalculationInputs containing required data
            residual_maturity: Residual maturity calculations
            ead_amortization: EAD amortization schedule
            pd_values: PD values
            lgd_values: LGD values  
            ccf_values: CCF values
            
        Returns:
            Tuple containing:
            - ECL by exposure DataFrame
            - ECL summary DataFrame  
            - Calculation details dictionary
        """
        pass
    
    def get_calculation_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this calculator.
        
        Returns:
            Dictionary with calculator metadata
        """
        return {
            "operation_type": self.operation_type.value,
            "operation_status": self.operation_status.value,
            "calculator_class": self.__class__.__name__,
            "description": f"ECL Calculator for {self.operation_type.value} {self.operation_status.value} operations"
        }
