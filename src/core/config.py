from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np


# List of supported file type for data loader
SUPPORTED_FILE_TYPES = ['.xls', '.xlsx', '.csv', '.zip']

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
    PERFORMING = "Stage 1 & 2" # Stage 1 + Stage 2
    DEFAULTED = "Stage 3" # Stage 3

@dataclass
class TemplateValidationResult:
    '''
    Generic container for template validation results
    '''
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    template_name: Optional[str] = None

@dataclass
class DataValidationResult:
    '''
    Generic container for data validation results
    '''
    errors: List[str]
    warnings: List[str]
    validation_summary: Dict[str, Any] = None


@dataclass 
class ECLOperationData:
    '''
    Unified data container for ECL operations.
    
    This class serves as the single source of truth for all ECL-related data,
    containing both the simulation data and template data needed for calculations.
    
    Attributes:
        operation_type: Type of operation (RETAIL, NON_RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        template_file_path: Path to the Excel template file
        data_file_path: Path to the simulation data file
        df: Main simulation data DataFrame
        template_data: Dictionary containing template DataFrames by sheet name
    '''
    operation_type: OperationType
    operation_status: OperationStatus
    data_file_path: Any 
    template_file_path: Any
    simulation_name: str
    list_jarvis_file_paths: Any = None
    df: pd.DataFrame = None
    template_data: Dict[str, pd.DataFrame] = None
    step_months: np.ndarray = None
    list_scenarios: List[str] = None
    output_scen : Dict[str, pd.DataFrame] = None
    template_validation_results: TemplateValidationResult = None
    data_validation_results: DataValidationResult = None
    #scenario_weights: Dict[str, float] = None


# Excel sheets name to be used for importing data, depending on the operation type and status
TEMPLATE_SHEETS_CONFIG: Dict[Tuple[OperationType, OperationStatus], List[str]] = {

    # Retail Performing (S1 + S2)
    (OperationType.RETAIL, OperationStatus.PERFORMING): [
        "Mapping fields Retail S1S2", 
        "Data Import Retail"
    ],

    # Retail Defaulted (S3)
    (OperationType.RETAIL, OperationStatus.DEFAULTED): [
        "Mapping fields Retail S3", 
        "Data Import Retail"
    ],

    # Non Retail Performing (S1 + S2)
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): [
        "DRIVERS NON RETAIL",
        "F0-Mapping fields Non Retail", 
        "F1-Segmentation rules",
        "F2-Mapping time steps",
        "F3-Mapping Segment SICR",
        "F4-Histo PD Multi Non Retail",
        "F6-PD S1S2 Non Retail",
        "F8-LGD S1S2 Non Retail",
        "F12-CCF Non Retail",
        "Histo Coefficients Sectoriels"
    ]
}

# Configuration for starting row for each sheet (0-indexed), to be modified if necessary
SHEET_START_ROW_CONFIG: Dict[str, int] = {
    # Common sheets
    "F2-Mapping time steps": 3,         # Start from row 4

    # Non Retail sheets
    "DRIVERS NON RETAIL": 3,          # Start from row 4
    "F0-Mapping fields Non Retail": 3,  # Start from row 4 (0-indexed)
    "F1-Segmentation rules": 4,         # Start from row 5
    "F3-Mapping Segment SICR": 3,       # Start from row 4
    "F4-Histo PD Multi Non Retail": 4,  # Start from row 5
    "F6-PD S1S2 Non Retail": 4,         # Start from row 5
    "F8-LGD S1S2 Non Retail": 4,        # Start from row 5
    "F12-CCF Non Retail": 4,            # Start from row 5
    
    # Retail sheets, to be defined
    "Mapping fields Retail": 1,  
    "Data Import Retail": 2,
    
    # Default for any sheet not specified
    "default": 0
}

# Configuration for sheet required fields
TEMPLATE_REQUIRED_FIELDS_CONFIG: Dict[str, List[str]] = {
    # Common sheets
    "F2-Mapping time steps": ["STEP","NB_MONTHS"],

    # Non Retail sheets
    "DRIVERS NON RETAIL": ["CALCULATOR_COLUMN_NAME", "VALUE_TYPE"],
    "F0-Mapping fields Non Retail": ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME", "VALUE_TYPE"],
    "F1-Segmentation rules": ["SEGMENT", "TYPE_MODEL"],
    "F3-Mapping Segment SICR": ["IFRS9_PD_MODEL_CODE_REPORTING", "IFRS9_PD_MODEL_NAME_REPORTING", 
                                "IFRS9_PD_MODEL_NAME_ORIGINATION", "ABSOLUTE_THRESHOLD_SICR", "RELATIVE_THRESHOLD_SICR"],
    "F4-Histo PD Multi Non Retail": ["VINTAGE_QUARTER", "SEGMENT", "RATING"],
    "F6-PD S1S2 Non Retail": ["SEGMENT", "SCENARIO", "RATING"],
    "F8-LGD S1S2 Non Retail": ["IFRS9_MODEL_CODE"],
    "F12-CCF Non Retail": ["IFRS9_MODEL_CODE"],
    "Histo Coefficients Sectoriels": ["VINTAGE YEAR", "VINTAGE QUARTER", "CODE MODEL",
                                      "NAER LIST", "VALEUR COEFFICIENT"],

    # Retail sheets, to be defined
    "Mapping fields Retail": ["Field1", "Field2"],
    "Data Import Retail": ["ImportField1", "ImportField2"]
}

# Configuration for mapping fields
MAPPING_FIELDS_FILES_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "Mapping fields Non Retail.xlsx",

    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "Mapping fields Retail S1S2",

    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "Mapping fields Retail S3"
}

DRIVERS_TEMPLATE_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "DRIVERS NON RETAIL"
}

SECTO_TEMPLATE_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "Histo Coefficients Sectoriels"
}

# Configuration for segmentation rules templates
RULES_SHEET_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F1-Segmentation rules",
    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): None,
    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): None
}

MAPPING_TIME_STEPS_TEMPLATES_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F2-Mapping time steps",
    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "F2-Mapping time steps",
    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "F2-Mapping time steps"
}

PD_SHEET_MAPPING_CONFIG: Dict[Tuple[OperationType, OperationStatus], Dict[str, List[List[str]]]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        "F6-PD S1S2 Non Retail": [["PD_MODEL_CODE", "RATING_CALCULATION"], ["IFRS9_PD_MODEL_CODE", "RATING"]]
    } # PD_MODEL_CODE is created during simulation
}

LGD_SHEET_MAPPING_CONFIG: Dict[Tuple[OperationType, OperationStatus], Dict[str, List[List[str]]]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        "F8-LGD S1S2 Non Retail": [["LGD_MODEL_CODE"], ["IFRS9_LGD_MODEL_CODE"]]
    } # LGD_MODEL_CODE is created during simulation
}

CCF_SHEET_MAPPING_CONFIG: Dict[Tuple[OperationType, OperationStatus], Dict[str, List[List[str]]]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        "F12-CCF Non Retail": [["CCF_MODEL_CODE"], ["IFRS9_CCF_MODEL_CODE"]]
    }
}

# Configuration for target segment column by operation/model/template
TARGET_SEGMENT_COLUMN: Dict[Tuple[OperationType, OperationStatus], Dict[Any, Any]] = {
    # Example configuration for Non Retail Performing
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        # PD-related segmentation outputs
        'PD': {'F6-PD S1S2 Non Retail': 'PD_MODEL_CODE'},
        # LGD-related segmentation outputs
        'LGD': {'F8-LGD S1S2 Non Retail': 'LGD_MODEL_CODE'},
        # CCF/EAD can be added similarly if needed
        'CCF': {'F12-CCF Non Retail': 'CCF_MODEL_CODE'},
        'PD_BEFORE_CRM': {'F6-PD S1S2 Non Retail': 'PD_MODEL_CODE_BEFORE_CRM'}
    }
}

INIT_TARGET_SEGMENT_COLUMN: Dict[Tuple[OperationType, OperationStatus], Dict[Any, Any]] = {
    # Example configuration for Non Retail Performing
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        "LGD_MODEL_CODE": "IFRS9_LGD_MODEL_AFTER_CRM",
        "PD_MODEL_CODE": "IFRS9_PD_MODEL_AFTER_CRM",
        "CCF_MODEL_CODE": "CCF_MODEL",
        "PD_MODEL_CODE_BEFORE_CRM": "IFRS9_PD_MODEL_BEFORE_CRM"
    }
}

# Configuration for mapping segment SICR template
MAPPING_SICR_TEMPLATE_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F3-Mapping Segment SICR"
}

HISTO_PD_TEMPLATE_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F4-Histo PD Multi Non Retail"
}

RATING_DEFAULT_CONFIG: Dict[OperationType, List[Any]] = {
    OperationType.NON_RETAIL: ["8", "9", "10"]
}

# Define dir
CONFIG_PARENT_DIR = "./"

CONFIG_DATA_DIR: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "inputs/data/Non Retail/S1-S2",
    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "inputs/data/Retail/S1-S2",
    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "inputs/data/Retail/S3"
}

CONFIG_TEMPLATES_DIR: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "inputs/templates/Non Retail/S1-S2",
    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "inputs/templates/Retail/S1-S2",
    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "inputs/templates/Retail/S3"
}

CONFIG_DEFAULT_TEMPLATES: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "sample/templates/Non Retail/S1-S2/Template_outil_V1.xlsx",
    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "sample/templates/Retail/S1-S2/Template_outil_V1.xlsx",
    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "sample/templates/Retail/S3/Template_outil_V1.xlsx"
}