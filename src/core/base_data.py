'''
Classes de base (abstract base classes) pour les composants du système.
Ces classes définissent les interfaces et les comportements attendus.
'''

# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_template as tplm
from src.utils.mapping_columns import mapping_columns
from src.utils import coerce_series_to_type

# Module logger
logger = logging.getLogger(__name__)

class BaseImporter(ABC):
    '''
    Base class for data importers.
    All importers should use ECLOperationData as their primary data container.
    '''

    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize BaseImporter with ECLOperationData.
        
        Args:
            ecl_operation_data: Container with operation details and file paths
        """
        self.data = ecl_operation_data

    @abstractmethod
    def load_data(self, **kwargs) -> pd.DataFrame:
        '''
        Abstract method to import data.
        
        Returns:
            pd.DataFrame: The imported data
        '''
        pass

class BaseValidator(ABC):
    '''
    Base class for data validators.
    All validators should use ECLOperationData as their primary data container.
    '''
    
    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize BaseValidator with ECLOperationData.
        
        Args:
            ecl_operation_data: Container with operation details, data, and templates
        """
        self.data = ecl_operation_data

    def mapping_fields(self) -> pd.DataFrame:
        '''
        Méthode pour mapper les champs du DataFrame importé.
        :return: Un DataFrame pandas avec les champs mappés.
        '''
        
        # Handle empty DataFrame
        if self.data.df is None or self.data.df.empty:
            logger.warning("DataFrame is empty. Skipping field mapping.")
            raise ValueError("DataFrame is empty. Cannot perform field mapping.")

        try:
            logger.info(f"Mapping fields for {self.data.operation_type.value} - {self.data.operation_status.value} operations")
            # Get the template for mapping fields according to the operation type and the operation status
            template_name = cst.MAPPING_FIELDS_TEMPLATES_CONFIG.get((self.data.operation_type, self.data.operation_status))
            if not template_name:
                logger.error(f"No mapping template found for operation type {self.data.operation_type} and status {self.data.operation_status}")
                return self.data.df

            # Get the mapping dataset from the template
            mapping_dataset = self.data.template_data.get(template_name)
            if mapping_dataset is None or mapping_dataset.empty:
                logger.error(f"Mapping template '{template_name}' not found in the provided template data.")
                return self.data.df

            # Get the mapping dictionary from the mapping dataset
            mapping_dict = dict(zip(mapping_dataset['CALCULATOR_COLUMN_NAME'], mapping_dataset['SIMULATION_DATA_COLUMN_NAME']))

            # Map the fields using the mapping dictionary
            self.data.df = mapping_columns(input_df=self.data.df, field_mapping=mapping_dict)

            # Transform column names to uppercase
            self.data.df.columns = [col.strip().upper() for col in self.data.df.columns]

            # Columns formatting
            mapping_format = dict(zip(mapping_dataset['CALCULATOR_COLUMN_NAME'], 
                                      mapping_dataset['VALUE_TYPE']))
            for col, val_type in mapping_format.items():
                if col.strip().upper() in self.data.df.columns:
                    self.data.df[col.strip().upper()] = coerce_series_to_type(self.data.df[col.strip().upper()], 
                                                                              val_type)

        except Exception as e:
            logger.info(f"Error during field mapping: {e}")
            self.data.df.columns = self.data.df.columns.str.strip().str.upper()
            
    @abstractmethod
    def validate_data(self) -> cst.DataValidationResult :
        '''
        Méthode abstraite pour valider les données du DataFrame importé.
        A customiser selon le type de d'opération (Retail, Non Retail) et le statut (S1+S2 / S3)
        : return: a dictionary with the validation type and results.
        '''
        logger.info(f"Validating data for {self.data.operation_type.value} - {self.data.operation_status.value} operations")
        pass

    # Create rather a basic data validator (for all operation type & status) and a specific data validator

    @abstractmethod
    def get_external_data(self):
        '''
        Méthode abstraite pour obtenir des données externes nécessaires à la validation.
        
        pass

        Returns:
            Any: External data needed for validation
        '''



