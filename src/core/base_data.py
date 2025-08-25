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

@dataclass 
class OperationData:
    '''
    
    '''
    data: pd.DataFrame
    operation_type: cst.OperationType
    operation_status: cst.OperationStatus


class BaseImporter(ABC):
    '''
    Basis class for data importers.
    '''

    def __init__(self,
                 file_path: str,
                 operation_type: cst.OperationType=None, 
                 operation_status: cst.OperationStatus=None
                 ):
        self.operation_type = operation_type
        self.status = operation_status
        self.file_path = file_path

    @abstractmethod
    def load_data(self) -> OperationData:
        '''
        Méthode abstraite pour importer des données.
        :return: Une classe contenant les données importées.
        '''
        pass

class BaseValidator(ABC):
    '''
    Basis class for data validators.
    '''
    def __init__(self, simu_data: OperationData, template_data: tplm.TemplateData):
        self.df = simu_data.data
        self.operation_type = simu_data.operation_type
        self.operation_status = simu_data.operation_status
        self.template_data = template_data

    def mapping_fields(self) -> pd.DataFrame:
        '''
        Méthode pour mapper les champs du DataFrame importé.
        :return: Un DataFrame pandas avec les champs mappés.
        '''
        # Get the template for mapping fields according to the operation type and the operation status
        template_name = cst.MAPPING_FIELDS_TEMPLATES_CONFIG.get((self.operation_type, self.operation_status))
        if not template_name:
            logger.error(f"No mapping template found for operation type {self.operation_type} and status {self.operation_status}")
            return self.df

        # Get the mapping dataset from the template
        mapping_dataset = self.template_data.template.get(template_name)
        if mapping_dataset is None or mapping_dataset.empty:
            logger.error(f"Mapping template '{template_name}' not found in the provided template data.")
            return self.df

        # Get the mapping dictionary from the mapping dataset
        mapping_dict = dict(zip(mapping_dataset['CALCULATOR_COLUMN_NAME'], mapping_dataset['SIMULATION_DATA_COLUMN_NAME']))

        # Map the fields using the mapping dictionary
        self.df = mapping_columns(input_df=self.df, field_mapping=mapping_dict)

        return self.df

    @abstractmethod
    def data_validator(self) :
        '''
        Méthode abstraite pour valider les données du DataFrame importé.
        A customiser selon le type de d'opération (Retail, Non Retail) et le statut (S1+S2 / S3)
        : return: a dictionary with the validation type and results.
        '''
        pass

    # Create rather a basic data validator (for all operation type & status) and a specific data validator







