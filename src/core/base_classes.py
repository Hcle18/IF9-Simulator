'''
Classes de base (abstract base classes) pour les composants du système.
Ces classes définissent les interfaces et les comportements attendus.
'''

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import logging
from enum import Enum
from pathlib import Path

# Module-level logger
logger = logging.getLogger(__name__)

class BaseImporter(ABC):
    '''
    Classe de base pour les importateurs de données.
    Définit l'interface pour les classes d'importation.
    '''

    @abstractmethod
    def load_data(self, source) -> pd.DataFrame:
        '''
        Méthode abstraite pour importer des données à partir d'une source.
        :param source: La source de données à importer, qui peut être un fichier csv, excel, zip
        ou une base de données.
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


class OperationType(Enum):
    '''
    Enumération pour les types d'opérations.
    Définit les types d'opérations possibles dans le système.
    '''
    RETAIL = "Retail"
    NON_RETAIL = "Non Retail"

class OperationStatus(Enum):
    '''
    Enumération pour les statuts des opérations.
    Définit les statuts possibles pour les opérations dans le système.
    '''
    PERFORMING = "S1+S2" # Stage 1 + Stage 2
    DEFAULTED = "S3" # Stage 3

@dataclass
class TemplateData:
    '''
    Generic container for Excel template data
    '''
    template: Dict[str, pd.DataFrame]

@dataclass
class ValidationResult:
    '''
    Generic container for template validation results
    '''
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    template_name: Optional[str] = None

class TemplateManager(ABC):
    '''
    Classe de base pour la gestion des templates.
    Définit l'interface pour les classes de gestion de templates.
    '''

    def __init__(self, operation_type: OperationType, status: OperationStatus, template_file_path:str):
        self.operation_type = operation_type
        self.status = status
        self.template_file_path = template_file_path

    @abstractmethod
    def template_import(self) -> Dict[str, pd.DataFrame]:
        '''
        Méthode abstraite pour importer un template des paramètres.
        La liste des templates à charger dépend du type d'opération (Retail, Non Retail) et du statut (S1+S2 / S3).
        Chacun des sous périmètres est traité dans une sous-classe spécifique qui implémente cette méthode.
        :return: Un dictionnaire avec les noms des templates comme clés et les DataFrames comme valeurs.
        '''
        pass

    # def validate_template(self, data:TemplateData) -> bool:
    #     '''
    #     Méthode pour valider les données du template.
    #     :param data: Un objet TemplateData contenant les DataFrames des templates.
    #     :return: True si le template est valide, False sinon.
    #     '''
    #     if not isinstance(data, TemplateData):
    #         logger.error("Invalid data type for template validation.")
    #         return False
        
    #     for name, df in data.template.items():
    #         if df.empty:
    #             logger.warning(f"Template '{name}' is empty.")
    #             return False
    #         if not isinstance(df, pd.DataFrame):
    #             logger.error(f"Template '{name}' is not a valid DataFrame.")
    #             return False
        
    #     logger.info("All templates are valid.")
    #     return True

    @abstractmethod
    def validate_template(self, data: TemplateData) -> ValidationResult:
        '''
        Méthode abstraite pour valider les données du template.
        :param data: Un objet TemplateData contenant les DataFrames des templates.
        :return: Un objet ValidationResult contenant le résultat de la validation.
        '''
        pass

    def read_excel_file(self, file_path:str, sheets: Union[str, List[str], None]) -> Dict[str, pd.DataFrame]:
        '''
        Méthode pour lire un fichier Excel et retourner les DataFrames des feuilles spécifiées.
        :param file_path: Le chemin du fichier Excel à lire.
        :param sheets: Le nom de la feuille ou une liste de noms de feuilles à lire. 
                      Si None, toutes les feuilles seront lues.
        :return: Un dictionnaire avec les noms des feuilles comme clés et les DataFrames comme valeurs.
        '''
        try:
            logger.info(f"Reading Excel templates from file: {file_path}")
            df_dict = pd.read_excel(file_path, sheet_name=sheets)
            logger.info(f"Successfully read Excel file: {file_path}")
            return df_dict
        except FileNotFoundError:
            logger.error(f"Excel file '{file_path}' not found.")
            return {}
        except Exception as e:
            logger.error(f"Error reading Excel file '{file_path}': {e}")
            return {}
