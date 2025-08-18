import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Union, Optional
import pandas as pd
from pathlib import Path

# Local import
from src.core import constants as cst

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

class TemplateManager(ABC):
    '''
    Classe de base pour la gestion des templates.
    Définit l'interface pour les classes de gestion de templates.
    '''

    def __init__(self, operation_type: cst.OperationType, operation_status: cst.OperationStatus, template_file_path:str):
        self.operation_type = operation_type
        self.status = operation_status
        self.template_file_path = template_file_path

    @abstractmethod
    def template_importer(self) -> TemplateData:
        '''
        Méthode abstraite pour importer un template des paramètres.
        La liste des templates à charger dépend du type d'opération (Retail, Non Retail) et du statut (S1+S2 / S3).
        Chacun des sous périmètres est traité dans une sous-classe spécifique qui implémente cette méthode.
        :return: Un objet TemplateData contenant les DataFrames des templates.
        '''
        pass

    @abstractmethod
    def validate_template(self, data: TemplateData) -> TemplateValidationResult:
        '''
        Méthode abstraite pour valider les données du template.
        :param data: Un objet TemplateData contenant les DataFrames des templates.
        :return: Un objet TemplateValidationResult contenant le résultat de la validation.
        '''
        pass

    def _get_required_sheets(self) -> List[str]:
        '''
        Get required sheet names for this operation type and status from configuration.
        :return: List of sheet names to import
        '''
        key = (self.operation_type, self.status)
        return cst.TEMPLATE_SHEETS_CONFIG.get(key, [])

    def read_excel_file(self, file_path:str, sheets: List[str]) -> Dict[str, pd.DataFrame]:
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