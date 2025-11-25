# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst

# Module logger
logger = logging.getLogger(__name__)


# @dataclass
# class TemplateValidationResult:
#     '''
#     Generic container for template validation results
#     '''
#     is_valid: bool
#     errors: List[str]
#     warnings: List[str]
#     template_name: Optional[str] = None


class BaseTemplate(ABC):
    '''
    Classe de base pour la gestion des templates.
    Définit l'interface pour les classes de gestion de templates.
    '''

    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize BaseTemplate with ECLOperationData.
        
        Args:
            ecl_operation_data: Container with operation details and file paths
        """
        self.data = ecl_operation_data

    @property
    def required_sheets(self) -> List[str]:
        required_sheets = self._get_required_sheets()
        return required_sheets
    
    def import_template(self) -> Dict[str, pd.DataFrame]:
        '''
        Import templates and update the ECLOperationData container.
        Supports both single template file (legacy) and multiple template files by type.
        Returns TemplateData containing DataFrames for all required sheets
        '''
        # Warning if no sheets are configured for operation type & status
        if not self.required_sheets:
            logger.warning(f"No sheets configured for {self.data.operation_type.value} {self.data.operation_status.value} operations.")
            self.data.template_data = {}
        else:
            # Check if template_file_path is a dict (multiple mode) or single file (legacy mode)
            if isinstance(self.data.template_file_path, dict):
                # Multiple template files mode
                logger.info("Importing templates from multiple files (by type)")
                self.data.template_data = self._import_multiple_template_files()
            else:
                # Single template file mode (legacy)
                logger.info("Importing templates from single file")
                template_dict = self._read_excel_file(self.data.template_file_path, sheets=self.required_sheets)
                self.data.template_data = template_dict

        # Add default template sheet if required but missing
        default_template_path_suffix = cst.CONFIG_DEFAULT_TEMPLATES.get((self.data.operation_type, self.data.operation_status), None)
        default_template_path = Path(__file__).resolve().parents[2] / str(default_template_path_suffix) if default_template_path_suffix else None
        missing_sheets = set(self.required_sheets) - set(self.data.template_data.keys())

        if default_template_path.exists():
            for sheet in missing_sheets:
                logger.info(f"Adding default template sheet '{sheet}' from {default_template_path}")
                # Read the default template sheet
                default_template_dict = self._read_excel_file(default_template_path, sheets=[sheet])
                if sheet in default_template_dict:
                    self.data.template_data[sheet] = default_template_dict[sheet]
        logger.info(f"Template data updated in ECLOperationData container with {len(self.data.template_data)} sheets")

    def validate_template(self) -> cst.TemplateValidationResult:
        '''
        Template method that performs basic validation and delegates specific validation to child classes.
        '''
        data = self.data.template_data

        errors = []
        warnings = []

        logger.info(f"Validating template for {self.data.operation_type.value} {self.data.operation_status.value} operations.")

        # Return early if no sheets are present
        if not data:
            logger.warning(f"No sheets found for {self.data.operation_type.value} {self.data.operation_status.value} operations.")
            self.data.template_validation_results = cst.TemplateValidationResult(
                is_valid=True,
                errors=[],
                warnings=["No template sheets found"],
                template_name=f"{self.data.operation_type.value} {self.data.operation_status.value} Template"
            )

        # Basic validation (common to all templates)
        basic_errors, basic_warnings = self._perform_basic_validation()
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)

        # Specific validation (implemented by child classes through _perform_specific_validation)
        specific_errors, specific_warnings = self._perform_specific_validation()
        errors.extend(specific_errors)
        warnings.extend(specific_warnings)
        
        is_valid = len(errors) == 0

        logger.info(f"Validation completed for {self.data.operation_type.value} {self.data.operation_status.value} operations.")
        logger.info(f"Validation result: {'Passed' if is_valid else 'Failed'}")
        
        self.data.template_validation_results = cst.TemplateValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            template_name=f"{self.data.operation_type.value} {self.data.operation_status.value} Template"
        )
    
    def _perform_basic_validation(self) -> tuple[List[str], List[str]]:
        '''
        Perform basic validation checks common to all templates.
        '''
        data = self.data.template_data

        errors = []
        warnings = []
        
        logger.info("Performing basic validation checks...")
        
        # Check if all expected sheets are present
        missing_sheets = set(self.required_sheets) - set(data.keys())
        if missing_sheets:
            errors.append(f"Missing required sheets for {self.data.operation_type.value} {self.data.operation_status.value}: {', '.join(missing_sheets)}")

        # Check if any sheets are empty
        for sheet_name, df in data.items():
            if df.empty:
                warnings.append(f"Sheet '{sheet_name}' is empty.")
            elif df.shape[0] == 0:
                warnings.append(f"Sheet '{sheet_name}' has no data rows.")
        
        # Validate each sheet's required columns
        for sheet_name, df in data.items():
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
        
        return errors, warnings
    
    @abstractmethod
    def _perform_specific_validation(self) -> tuple[List[str], List[str]]:
        '''
        Abstract method for performing operation-specific validation checks.
        Must be implemented by child classes.
        Returns tuple of (errors, warnings).
        '''
        pass

    def _import_multiple_template_files(self) -> Dict[str, pd.DataFrame]:
        '''
        Import and merge multiple template files organized by type (PD, LGD, CCF, etc.).
        
        :return: Dictionary with sheet names as keys and merged DataFrames as values
        '''
        all_dataframes = {}
        
        # Iterate through template types (PD, LGD, CCF, Staging, Segmentation)
        for template_type, file_paths in self.data.template_file_path.items():
            if not file_paths or len(file_paths) == 0:
                logger.info(f"No files provided for template type: {template_type}")
                continue
            
            logger.info(f"Processing {len(file_paths)} file(s) for template type: {template_type}")
            
            # Process each file for this template type
            for file_path in file_paths:
                # Convert to string if it's a Path-like object
                file_path_str = str(file_path) if hasattr(file_path, '__str__') else file_path
                
                # Read the file with all required sheets
                template_dict = self._read_excel_file(file_path_str, sheets=self.required_sheets)
                
                # Merge DataFrames from this file into the global dict
                for sheet_name, df in template_dict.items():
                    if sheet_name in all_dataframes:
                        # Sheet already exists, concatenate DataFrames
                        logger.info(f"Concatenating sheet '{sheet_name}' from {template_type} file")
                        all_dataframes[sheet_name] = pd.concat(
                            [all_dataframes[sheet_name], df], 
                            ignore_index=True
                        )
                    else:
                        # First occurrence of this sheet
                        all_dataframes[sheet_name] = df
        
        logger.info(f"Successfully merged templates from multiple files. Total sheets: {len(all_dataframes)}")
        return all_dataframes

    def _get_required_sheets(self) -> List[str]:
        '''
        Get required sheet names for this operation type and status from configuration.
        :return: List of sheet names to import
        '''
        key = (self.data.operation_type, self.data.operation_status)
        return cst.TEMPLATE_SHEETS_CONFIG.get(key, [])

    def _read_excel_file(self, file_path:str, sheets: List[str]) -> Dict[str, pd.DataFrame]:
        '''
        Méthode pour lire un fichier Excel et retourner les DataFrames des feuilles spécifiées.
        :param file_path: Le chemin du fichier Excel à lire.
        :param sheets: Le nom de la feuille ou une liste de noms de feuilles à lire. 
                      Si None, toutes les feuilles seront lues.
        :return: Un dictionnaire avec les noms des feuilles comme clés et les DataFrames comme valeurs.
        '''

        # Convert file_path to string if needed
        file_path_str = str(file_path)
        
        # Handle not excel file: not endswith ('xls', 'xlsx') (case-insensitive)
        if not file_path_str.lower().endswith(('.xls', '.xlsx')):
            logger.error(f"File '{file_path_str}' is not an Excel file.")
            return {}

        try:
            logger.info(f"Reading Excel templates from file: {file_path_str}")
            df_dict = {}
            default_skip_row = cst.SHEET_START_ROW_CONFIG.get("default", 0) # Default skip row if not declared

            for sheet_name in sheets:
                # Check if sheet_name exists in the Excel file, otherwise continue
                if sheet_name not in pd.ExcelFile(file_path_str).sheet_names:
                    logger.warning(f"Sheet '{sheet_name}' not found in Excel file '{file_path_str}'. Skipping.")
                    continue
                skip_row = cst.SHEET_START_ROW_CONFIG.get(sheet_name, default_skip_row)
                df_dict[sheet_name] = pd.read_excel(file_path_str, sheet_name=sheet_name, skiprows=skip_row)
            logger.info(f"Successfully read Excel file: {file_path_str}. List of sheet names: {', '.join(df_dict.keys())}")

            return df_dict
        
        # Handle not found file path
        except FileNotFoundError:
            logger.error(f"Excel file '{file_path_str}' not found.")
            raise FileNotFoundError(f"Excel file '{file_path_str}' not found.")
        except OSError as e:
            logger.error(f"OS error when accessing Excel file '{file_path_str}': {e}")
            raise OSError(f"OS error when accessing Excel file '{file_path_str}': {e}")
        except Exception as e:
            logger.error(f"Error reading Excel file '{file_path_str}': {e}")
            raise RuntimeError(f"Error reading Excel file '{file_path_str}': {e}")