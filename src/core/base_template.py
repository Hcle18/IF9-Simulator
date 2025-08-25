# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst

# Module logger
logger = logging.getLogger(__name__)

@dataclass
class TemplateData:
    '''
    Generic container for Excel template data
    '''
    template: Dict[str, pd.DataFrame]

@dataclass
class TemplateValidationResult:
    '''
    Generic container for template validation results
    '''
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    template_name: Optional[str] = None

class BaseTemplate(ABC):
    '''
    Classe de base pour la gestion des templates.
    Définit l'interface pour les classes de gestion de templates.
    '''

    def __init__(self, operation_type: cst.OperationType, operation_status: cst.OperationStatus, template_file_path:str):
        self.operation_type = operation_type
        self.status = operation_status
        self.template_file_path = template_file_path

    @property
    def required_sheets(self) -> List[str]:
        required_sheets = self._get_required_sheets()
        return required_sheets
    
    def template_importer(self) -> TemplateData:
        '''
        Import templates
        Returns TemplateData containing DataFrames for all required sheets
        '''
        # Get required sheets for this operation type and status
        #sheets_to_import = self._get_required_sheets()

        # Warning if no sheets are configured for operation type & status
        if not self.required_sheets:
            logger.warning(f"No sheets configured for {self.operation_type.value} {self.status.value} operations.")
            return TemplateData(template={})
        
        # Read excel file with specific sheets and store as a dict
        template_dict = self._read_excel_file(self.template_file_path, sheets=self.required_sheets)
        return TemplateData(template=template_dict)

    def validate_template(self, data: TemplateData) -> TemplateValidationResult:
        '''
        Template method that performs basic validation and delegates specific validation to child classes.
        '''
        errors = []
        warnings = []
        
        logger.info(f"Validating template for {self.operation_type.value} {self.status.value} operations.")

        # Return early if no sheets are present
        if not data.template:
            logger.warning(f"No sheets found for {self.operation_type.value} {self.status.value} operations.")
            return TemplateValidationResult(
                is_valid=True,
                errors=[],
                warnings=["No template sheets found"],
                template_name=f"{self.operation_type.value} {self.status.value} Template"
            )

        # Basic validation (common to all templates)
        basic_errors, basic_warnings = self._perform_basic_validation(data)
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)

        # Specific validation (implemented by child classes through _perform_specific_validation)
        specific_errors, specific_warnings = self._perform_specific_validation(data)
        errors.extend(specific_errors)
        warnings.extend(specific_warnings)
        
        is_valid = len(errors) == 0
        
        logger.info(f"Validation completed for {self.operation_type.value} {self.status.value} operations.")
        logger.info(f"Validation result: {'Passed' if is_valid else 'Failed'}")
        
        return TemplateValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            template_name=f"{self.operation_type.value} {self.status.value} Template"
        )
    
    def _perform_basic_validation(self, data: TemplateData) -> tuple[List[str], List[str]]:
        '''
        Perform basic validation checks common to all templates.
        '''
        errors = []
        warnings = []
        
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
        
        # Validate each sheet's required columns
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
        
        return errors, warnings
    
    @abstractmethod
    def _perform_specific_validation(self, data: TemplateData) -> tuple[List[str], List[str]]:
        '''
        Abstract method for performing operation-specific validation checks.
        Must be implemented by child classes.
        Returns tuple of (errors, warnings).
        '''
        pass

    def _get_required_sheets(self) -> List[str]:
        '''
        Get required sheet names for this operation type and status from configuration.
        :return: List of sheet names to import
        '''
        key = (self.operation_type, self.status)
        return cst.TEMPLATE_SHEETS_CONFIG.get(key, [])

    def _read_excel_file(self, file_path:str, sheets: List[str]) -> Dict[str, pd.DataFrame]:
        '''
        Méthode pour lire un fichier Excel et retourner les DataFrames des feuilles spécifiées.
        :param file_path: Le chemin du fichier Excel à lire.
        :param sheets: Le nom de la feuille ou une liste de noms de feuilles à lire. 
                      Si None, toutes les feuilles seront lues.
        :return: Un dictionnaire avec les noms des feuilles comme clés et les DataFrames comme valeurs.
        '''

        # Handle not excel file: not endswith ('xls', 'xlsx') (case-insensitive)
        if not file_path.lower().endswith(('.xls', '.xlsx')):
            logger.error(f"File '{file_path}' is not an Excel file.")
            return {}

        try:
            logger.info(f"Reading Excel templates from file: {file_path}")
            df_dict = {}
            default_skip_row = cst.SHEET_START_ROW_CONFIG.get("default", 0) # Default skip row if not declared

            for sheet_name in sheets:
                skip_row = cst.SHEET_START_ROW_CONFIG.get(sheet_name, default_skip_row)
                df_dict[sheet_name] = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_row)
            logger.info(f"Successfully read Excel file: {file_path}. List of sheet names: {', '.join(df_dict.keys())}")

            return df_dict
        
        # Handle not found file path
        except FileNotFoundError:
            logger.error(f"Excel file '{file_path}' not found.")
            return {}
        except OSError as e:
            logger.error(f"OS error when accessing Excel file '{file_path}': {e}")
            return {}
        except Exception as e:
            logger.error(f"Error reading Excel file '{file_path}': {e}")
            return {}