from src.core.librairies import *

from src.core import config as cst
from src.core import base_ecl_calculator as bcalc

from src.ecl_calculation.time_steps import maturity, nb_time_steps

logger = logging.getLogger(__name__)  

# ----------------------------------------
# 1. Non Retail Performing ECL Calculator
# ----------------------------------------

class NRS1S2ECLCalculator(bcalc.BaseECLCalculator):
    '''
    Custom class for Non Retail S1+S2 ECL calculation
    '''

    def get_time_steps(self):
        '''
        Get the number of time steps and maturity from the template data.
        '''

        # Get the data for mapping template
        template_name = cst.MAPPING_TIME_STEPS_TEMPLATES_CONFIG.get((self.data.operation_type, self.data.operation_status))

        template_df = self.data.template_data.get(template_name)

        # Residual maturity in months
        self.data.df["RESIDUAL_MATURITY_MONTHS"] =  maturity(self.data.df['EXPOSURE_END_DATE'], self.data.df['AS_OF_DATE'])

        # Number of steps
        #nb_steps, nb_months_list = nb_time_steps(self.data.df["RESIDUAL_MATURITY_MONTHS"], template_df)
        self.data.df["NB_TIME_STEPS"] = nb_time_steps(self.data.df["RESIDUAL_MATURITY_MONTHS"], template_df)
        # self.data.df["NB_MONTHS_LIST"] = nb_months_list

        # Update mapping step to fit the maximum maturity
        step_months = np.sort(template_df["NB_MONTHS"].to_numpy())
        max_maturity = self.data.df["RESIDUAL_MATURITY_MONTHS"].max()
        # Extend step_months to cover all contracts
        while step_months[-1] < max_maturity:
            nb_diff = step_months[-1] - step_months[-2] if len(step_months) > 1 else step_months[-1]
            step_months = np.append(step_months, step_months[-1] + nb_diff)
        self.data.step_months = step_months
# ----------------------------------------
# 2. Retail Performing ECL Calculator
# ----------------------------------------




# ========================================
# ECL Calculator Factory
# ========================================

class ECLCalculatorFactory:
    """
    Factory class for creating appropriate ECL calculators based on operation type and status.
    """

    # Registry mapping operation type & status to ECL calculator classes
    _registry_loader: dict[tuple[cst.OperationType, cst.OperationStatus], bcalc.BaseECLCalculator] = {
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): None,
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): None,
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NRS1S2ECLCalculator
    }

    @classmethod
    def get_ecl_calculator(cls, ecl_operation_data: cst.ECLOperationData) -> bcalc.BaseECLCalculator:
        """
        Get the appropriate ECL calculator based on operation type and status from ECLOperationData.

        Args:
            ecl_operation_data: Container with operation details and template file path
            
        Returns:
            BaseECLCalculator: The appropriate ECL calculator instance

        Raises:
            ValueError: If no loader is found for the given operation type and status
        """
        # Get the key as combination of operation type and status
        key = (ecl_operation_data.operation_type, ecl_operation_data.operation_status)

        # Handle case where key is not found in registry
        if key not in cls._registry_loader:
            raise ValueError(f"No template loader found for {ecl_operation_data.operation_type.value} - {ecl_operation_data.operation_status.value}")

        # Get the calculator class from the registry
        calculator_class = cls._registry_loader[key]
        logger.info(f"Creating ECL calculator for {ecl_operation_data.operation_type.value} - {ecl_operation_data.operation_status.value}")

        return calculator_class(ecl_operation_data)

# ==========================================
# ENTRY POINT TO CREATE ECL CALCULATOR
# ==========================================

def ecl_calculator(ecl_operation_data: cst.ECLOperationData) -> bcalc.BaseECLCalculator:
    """
    Entry point function to get a template loader instance for importing & validating templates.

    Args:
        operation_type: The type of operation (NON_RETAIL, RETAIL)
        operation_status: The status of operation (PERFORMING, DEFAULTED)
        template_file_path: Path to the template file
        
    Returns:
        BaseTemplate: The appropriate template loader instance
    """

    # Use the factory to get the appropriate ECL calculator
    return ECLCalculatorFactory.get_ecl_calculator(ecl_operation_data)