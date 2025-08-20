import logging
import pandas as pd

# Local import
from src.core import constants as cst
from src.core import template_manager as tplm

logger = logging.getLogger(__name__)

# -----------------------------------------
# 1. Template Loader for Non Retail S1+S2
# -----------------------------------------

class NonRetailS1S2TemplateLoader(tplm.TemplateManager):
    def __init__(self, template_file_path:str):
        '''
        Initialize the template loader for Non Retail S1 + S2 operations
        '''
        super().__init__(
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING,
            template_file_path=template_file_path
        )

    def _perform_specific_validation(self, data: tplm.TemplateData) -> tplm.TemplateValidationResult:
        '''
        Validate template for Non Retail S1 + S2 operations
        Performs validation checks on the imported data.
        '''
        errors = [] # List to collect validation errors
        warnings = [] # List to collect validation warnings

        logger.info("Performing specific validation checks...")

        # Validate each sheet based on its specific requirements
        for sheet_name, df in data.template.items():
            sheet_required_fields = cst.TEMPLATE_REQUIRED_FIELDS_CONFIG.get(sheet_name, [])
            
            # Check sheet F2-Mapping time steps
            if sheet_name == "F2-Mapping time steps":
                # Check data sheet have numeric data in all minimum required columns
                numeric_columns = df.select_dtypes(include=['number']).columns
                non_numeric_required = set(sheet_required_fields) - set(numeric_columns)
                if non_numeric_required:
                    # Check if these columns contain numeric data but are stored as object type
                    for col in non_numeric_required:
                        if col in df.columns:
                            try:
                                pd.to_numeric(df[col], errors='raise')
                            except (ValueError, TypeError):
                                errors.append(f"Column '{col}' in sheet '{sheet_name}' should contain numeric data.")

                # Get the number of time steps in F6-PD S1S2 Non Retail sheet
                f6_sheet_name = "F6-PD S1S2 Non Retail"
                if f6_sheet_name in data.template:
                    f6_df = data.template[f6_sheet_name]
                    f6_pd_time_steps = sum(1 for col in f6_df.columns if col.lower().startswith('time_step'))
                else:
                    f6_pd_time_steps = 0
                    errors.append(f"Required sheet '{f6_sheet_name}' not found for time step validation.")
                    
                # Check if number of time steps matches
                if df.shape[0] != f6_pd_time_steps:
                    errors.append(f"Number of time steps in '{sheet_name}' does not match 'F6-PD S1S2 Non Retail'.")
                    logger.info(f"Number of time steps in '{sheet_name}': {df.shape[0]}")
                    logger.info(f"Number of time steps in 'F6-PD S1S2 Non Retail': {f6_pd_time_steps}")
            
            # Check sheets F4-Histo PD Multi Non Retail, F6-PD S1S2 Non Retail
            if sheet_name in ["F4-Histo PD Multi Non Retail", "F6-PD S1S2 Non Retail"]:
                pass
        
        return errors, warnings


# -----------------------------------------
# 2. Template Loader for Retail S1+S2
# -----------------------------------------
class RetailS1S2TemplateLoader(tplm.TemplateManager):
    def __init__(self, template_file_path:str):
        '''
        Initialize the template loader for Retail S1 + S2 operations
        '''
        super().__init__(
            operation_type=cst.OperationType.RETAIL,
            operation_status=cst.OperationStatus.PERFORMING,
            template_file_path=template_file_path
        )

    def _perform_specific_validation(self, data: tplm.TemplateData) -> tuple[list[str], list[str]]:
        '''
        Perform specific validation checks for Retail S1 + S2 operations.
        '''
        errors = []
        warnings = []
        
        # Add specific validation logic for Retail S1S2
        
        return errors, warnings

# -----------------------------------------
# 3. Template Loader for Retail S3
# -----------------------------------------
class RetailS3TemplateLoader(tplm.TemplateManager):
    def __init__(self, template_file_path:str):
        '''
        Initialize the template loader for Retail S3 operations
        '''
        super().__init__(
            operation_type=cst.OperationType.RETAIL,
            operation_status=cst.OperationStatus.DEFAULTED,
            template_file_path=template_file_path
        )

    def _perform_specific_validation(self, data: tplm.TemplateData) -> tuple[list[str], list[str]]:
        '''
        Perform specific validation checks for Retail S3 operations.
        '''
        errors = []
        warnings = []
        
        # Add specific validation logic for Retail S3
        
        return errors, warnings

# ========================================
# Template Loader Factory
# ========================================

class TemplateLoaderFactory:
    """
    Factory class for creating appropriate template loaders based on operation type and status.
    """

    # Registry mapping operation type & status to template loader classes
    _registry_loader: dict[tuple[cst.OperationType, cst.OperationStatus], tplm.TemplateManager] = {
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): RetailS1S2TemplateLoader,
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): RetailS3TemplateLoader,
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NonRetailS1S2TemplateLoader
    }

    @classmethod
    def get_template_loader(cls, operation_type: cst.OperationType, operation_status: cst.OperationStatus, 
                            template_file_path: str) -> tplm.TemplateManager:
        """
            Get the appropriate template loader based on operation type and status
            
            Args:
                operation_type: The type of operation (NON_RETAIL, RETAIL)
                operation_status: The status of operation (PERFORMING, DEFAULTED)
                template_file_path: Path to the template file
                
            Returns:
                TemplateManager: The appropriate template loader instance
                
            Raises:
                ValueError: If no loader is found for the given operation type and status
        """
        # Get the key as combination of operation type and status
        key = (operation_type, operation_status)

        # Handle case where key is not found in registry
        if key not in cls._registry_loader:
            raise ValueError(f"No template loader found for {operation_type.value} - {operation_status.value}")

        # Get the loader class from the registry
        loader_class = cls._registry_loader[key]
        logger.info(f"Creating template loader for {operation_type.value} - {operation_status.value}")

        return loader_class(template_file_path)

# ==========================================
# ENTRY POINT FOR TEMPLATE LOADER
# ==========================================

def template_loader(operation_type: cst.OperationType,
                    operation_status: cst.OperationStatus,
                    template_file_path: str) -> tplm.TemplateManager:
    """
    Entry point function to get a template loader instance for importing & validating templates.

    Args:
        operation_type: The type of operation (NON_RETAIL, RETAIL)
        operation_status: The status of operation (PERFORMING, DEFAULTED)
        template_file_path: Path to the template file
        
    Returns:
        TemplateManager: The appropriate template loader instance
    """

    # Use the factory to get the appropriate template loader
    return TemplateLoaderFactory.get_template_loader(operation_type, operation_status, template_file_path)
