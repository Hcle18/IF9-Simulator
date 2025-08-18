import logging
import pandas as pd

# Local import
from src.core import constants as cst
from src.core import template_manager as tplm

logger = logging.getLogger(__name__)

# ========================================
# 1. Template Loader for Non Retail S1+S2
# ========================================
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

    @property
    def required_sheets(self):
        required_sheets = self._get_required_sheets()
        return required_sheets

    def template_importer(self) -> tplm.TemplateData:
        '''
        Import templates for Non Retail S1 + S2 operations
        Returns TemplateData containing DataFrames for all required sheets
        '''
        # Get required sheets for this operation type and status
        #sheets_to_import = self._get_required_sheets()

        # Warning if no sheets are configured for operation type & status
        if not self.required_sheets:
            logger.warning(f"No sheets configured for {self.operation_type.value} {self.status.value} operations.")
            return tplm.TemplateData(template={})
        
        # Read excel file with specific sheets and store as a dict
        template_dict = self.read_excel_file(self.template_file_path, sheets=self.required_sheets)
        return tplm.TemplateData(template=template_dict)
    
    def validate_template(self, data: tplm.TemplateData) -> tplm.TemplateValidationResult:
        '''
        Validate template for Non Retail S1 + S2 operations
        Performs validation checks on the imported data.
        '''
        errors = [] # List to collect validation errors
        warnings = [] # List to collect validation warnings

        # List of sheets to be validated
        #expected_sheets = self._get_required_sheets()

        logger.info(f"Validating template for {self.operation_type.value} {self.status.value} operations.")

        # -----------------------------
        # 1.Basic validation checks
        # -----------------------------
    
        logger.info("Performing basic validation checks...")

        # Check if all expected sheets are present
        missing_sheets = set(self.required_sheets) - set(data.template.keys())
        if missing_sheets:
            errors.append(f"Missing required sheets for {self.operation_type.value} {self.status.value}: {', '.join(missing_sheets)}")

        # Check if any sheets are empty
        for sheet_name, df in data.template.items():
            if df.empty:
                warnings.append(f"Sheet '{sheet_name}' is empty.")
            elif df.shape[0] == 0:
                warnings.append(f"Sheet '{sheet_name}' has no data rows.")

        # ------------------------------
        # 2.Specific validation checks
        # ------------------------------

        logger.info("Performing specific validation checks...")

        # Validate each sheet based on its expected structure
        for sheet_name, df in data.template.items():
            logger.info(f"Validating sheet: {sheet_name}")
            sheet_required_fields = cst.TEMPLATE_REQUIRED_FIELDS_CONFIG.get(sheet_name, [])
            missing_columns = set(sheet_required_fields) - set(df.columns)

            # Check if minimum required columns exist
            if missing_columns:
                errors.append(f"Missing columns in '{sheet_name}': {', '.join(missing_columns)}")
            
            # Check if required columns have non-null data
            for col in sheet_required_fields:
                if col in df.columns:
                    if df[col].isnull().all():
                        errors.append(f"Column '{col}' in sheet '{sheet_name}' contains only null values.")

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


                # Get the number of time steps in F6-PD S1S2 Non Retail sheet, i.e. number of column name begin with time_step (case insensitive)
                f6_sheet_name = "F6-PD S1S2 Non Retail"
                if f6_sheet_name in data.template:
                    f6_df = data.template[f6_sheet_name]
                    f6_pd_time_steps = sum(1 for col in f6_df.columns if col.lower().startswith('time_step'))
                else:
                    f6_pd_time_steps = 0
                    errors.append(f"Required sheet '{f6_sheet_name}' not found for time step validation.")
                    
                # Check if number of time steps is the same as in F2-Mapping time steps sheet
                if df.shape[0] != f6_pd_time_steps:
                    errors.append(f"Number of time steps in '{sheet_name}' does not match 'F6-PD S1S2 Non Retail'.")
                    logger.info(f"Number of time steps in '{sheet_name}': {df.shape[0]}")
                    logger.info(f"Number of time steps in 'F6-PD S1S2 Non Retail': {f6_pd_time_steps}")
            
            # Check sheets F4-Histo PD Multi Non Retail, F6-PD S1S2 Non Retail

        # ------------------------------
        # 3.Specific validation checks
        # ------------------------------

        logger.info("Performing specific validation checks...")

        # Validate each sheet based on its expected structure
        for sheet_name, df in data.template.items():
            logger.info(f"Validating sheet: {sheet_name}")
            sheet_required_fields = cst.TEMPLATE_REQUIRED_FIELDS_CONFIG.get(sheet_name, [])
            missing_columns = set(sheet_required_fields) - set(df.columns)

            # Check if minimum required columns exist
            if missing_columns:
                errors.append(f"Missing columns in '{sheet_name}': {', '.join(missing_columns)}")

            # Check if required columns have non-null data
            for col in sheet_required_fields:
                if col in df.columns:
                    if df[col].isnull().all():
                        errors.append(f"Column '{col}' in sheet '{sheet_name}' contains only null values.")

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

                # Get the number of time steps in F6-PD S1S2 Non Retail sheet, i.e. number of column name begin with time_step (case insensitive)
                f6_sheet_name = "F6-PD S1S2 Non Retail"
                if f6_sheet_name in data.template:
                    f6_df = data.template[f6_sheet_name]
                    f6_pd_time_steps = sum(1 for col in f6_df.columns if col.lower().startswith('time_step'))
                else:
                    f6_pd_time_steps = 0
                    errors.append(f"Required sheet '{f6_sheet_name}' not found for time step validation.")

                # Check if number of time steps is the same as in F2-Mapping time steps sheet
                if df.shape[0] != f6_pd_time_steps:
                    errors.append(f"Number of time steps in '{sheet_name}' does not match 'F6-PD S1S2 Non Retail'.")
                    logger.info(f"Number of time steps in '{sheet_name}': {df.shape[0]}")
                    logger.info(f"Number of time steps in 'F6-PD S1S2 Non Retail': {f6_pd_time_steps}")

            # Check sheets F4-Histo PD Multi Non Retail, F6-PD S1S2 Non Retail

        # --------------------------------
        # 4.Summary of validation errors
        # --------------------------------
        is_valid = len(errors) == 0

        logger.info(f"Validation completed for {self.operation_type.value} {self.status.value} operations.")
        logger.info(f"Validation result: {'Passed' if is_valid else 'Failed'}")

        return tplm.TemplateValidationResult(
            is_valid=is_valid, 
            errors=errors, 
            warnings=warnings, 
            template_name=f"{self.operation_type.value} {self.status.value} Template",
            )

