# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_data as bcls
from src.core import base_template as tplm
from src.data import data_loader as dl
from src.templates import template_loader as tpl

logger = logging.getLogger(__name__)


# ========================================
# 1. Non Retail S1+S2 data validation
# ========================================
class NRS1S2DataValidator(bcls.BaseValidator):
    '''
    Custom class for Non Retail S1+S2 data validation
    '''

    def validate_data(self):
        # Custom validation logic for Non Retail S1+S2
        logger.info(f"Starting data validation for {self.data.operation_type.value} {self.data.operation_status.value} operations.")
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["PROVISIONING_BASIS", "ECL_RUN_ID"]
        missing_fields = [field for field in required_fields if field not in self.data.df.columns]
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Check whether Number of ECL_RUN_ID is consistent with number of Jarvis files
        if self.data.list_jarvis_file_paths:
            unique_ecl_run_ids = self.data.df["ECL_RUN_ID"].nunique()
            if unique_ecl_run_ids != len(self.data.list_jarvis_file_paths):
                errors.append(f"Number of unique ECL_RUN_ID ({unique_ecl_run_ids}) does not match number of Jarvis files ({len(self.data.list_jarvis_file_paths)})")

        self.data.data_validation_results = cst.DataValidationResult(
            errors=errors,
            warnings=warnings
        )

# ========================================
# Data Validator Factory
# ========================================

class DataValidatorFactory:
    """
    Factory class for creating appropriate data validators based on operation type and status.
    """

    # Registry mapping operation type & status to data validator classes
    _registry_loader: dict[tuple[cst.OperationType, cst.OperationStatus], bcls.BaseValidator] = {
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): None,
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): None,
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NRS1S2DataValidator
    }

    @classmethod
    def get_data_validator(cls, ecl_operation_data: cst.ECLOperationData) -> bcls.BaseValidator:
        """
        Get the appropriate data validator based on operation type and status from ECLOperationData.

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

        # Get the validator class from the registry
        validator_class = cls._registry_loader[key]
        logger.info(f"Creating data validator for {ecl_operation_data.operation_type.value} - {ecl_operation_data.operation_status.value}")

        return validator_class(ecl_operation_data)

# ==========================================
# ENTRY POINT TO CREATE DATA VALIDATOR
# ==========================================

def data_validator(ecl_operation_data: cst.ECLOperationData) -> bcls.BaseValidator:
    """
    Entry point function to get a template loader instance for importing & validating templates.

    Args:
        operation_type: The type of operation (NON_RETAIL, RETAIL)
        operation_status: The status of operation (PERFORMING, DEFAULTED)
        template_file_path: Path to the template file
        
    Returns:
        BaseTemplate: The appropriate template loader instance
    """

    # Use the factory to get the appropriate data validator
    return DataValidatorFactory.get_data_validator(ecl_operation_data)




if __name__ == "__main__": 

    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING

    # Simulation data
    file_name = "sample_non_retail.zip"
    file_path = os.path.join("sample", "data", file_name)

    importer = dl.get_importer(file_path, operation_type, operation_status)
    #print(importer)
    
    # Templates
    template_path = r".\sample\templates\Template_outil_V1.xlsx"
    template_loader = tpl.template_loader(operation_type, operation_status, template_path)
    #print(template_loader.required_sheets)

    # Importing & validating templates
    NR_template_data = template_loader.template_importer()
    print(NR_template_data)
    template_validation = template_loader.validate_template(NR_template_data)

    # Data loader
    operation_nr_data = dl.data_loader(importer)
    print(f"Operation NR Data Columns: {operation_nr_data.data.columns}")
    # Data validation
    NR_data_validator = NRS1S2DataValidator(operation_nr_data, NR_template_data)
    df_mapped = NR_data_validator.mapping_fields()
    print(f"After mapping Data Columns: {df_mapped.columns}")
