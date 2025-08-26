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
        # self.operation_type = ecl_operation_data.operation_type
        # self.operation_status = ecl_operation_data.operation_status
        # self.data_file_path = ecl_operation_data.data_file_path

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
        # self.operation_type = ecl_operation_data.operation_type
        # self.operation_status = ecl_operation_data.operation_status
        # self.df = ecl_operation_data.df
        # self.template_data = ecl_operation_data.template_data

    def mapping_fields(self) -> pd.DataFrame:
        '''
        Méthode pour mapper les champs du DataFrame importé.
        :return: Un DataFrame pandas avec les champs mappés.
        '''
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

    @abstractmethod
    def validate_data(self) :
        '''
        Méthode abstraite pour valider les données du DataFrame importé.
        A customiser selon le type de d'opération (Retail, Non Retail) et le statut (S1+S2 / S3)
        : return: a dictionary with the validation type and results.
        '''
        logger.info(f"Validating data for {self.data.operation_type.value} - {self.data.operation_status.value} operations")
        pass

    # Create rather a basic data validator (for all operation type & status) and a specific data validator







