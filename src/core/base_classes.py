'''
Classes de base (abstract base classes) pour les composants du système.
Ces classes définissent les interfaces et les comportements attendus.
'''

from abc import ABC, abstractmethod
import pandas as pd

# Local import
from src.core import constants as cst


class BaseImporter(ABC):
    '''
    Classe de base pour les importateurs de données.
    Définit l'interface pour les classes d'importation.
    '''

    def __init__(self,
                 file_path: str,
                 operation_type:cst.OperationType=None, 
                 operation_status:cst.OperationStatus=None
                 ):
        self.operation_type = operation_type
        self.status = operation_status
        self.file_path = file_path

    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        '''
        Méthode abstraite pour importer des données.
        :return: Un DataFrame pandas contenant les données importées.
        '''
        pass

class BaseValidator(ABC):
    '''
    Classe de base pour la validation des données importées de la base provisionnable 
    '''
    def __init__(self, imported_df: pd.DataFrame):
        self.df = imported_df

    @abstractmethod
    def mapping_fields(self) -> pd.DataFrame:
        '''
        Méthode abstraite pour mapper les champs du DataFrame importé.
        :return: Un DataFrame pandas avec les champs mappés.
        '''
        pass

    @abstractmethod
    def data_validator(self):
        '''
        Méthode abstraite pour valider les données du DataFrame importé.
        A customiser selon le type de d'opération (Retail, Non Retail) et le statut (S1+S2 / S3)
        : return: a dictionary with the validation type and results.
        '''
        pass







