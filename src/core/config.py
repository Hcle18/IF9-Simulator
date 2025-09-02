from enum import Enum
from typing import Dict, List, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


# List of supported file type for data loader
SUPPORTED_FILE_TYPES = ['xls', '.xlsx', '.zip']

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
    template_file_path: str
    data_file_path: str 
    df: pd.DataFrame = None
    template_data: Dict[str, pd.DataFrame] = None
    step_months: np.ndarray = None


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
        "F1-Mapping fields Non Retail", 
        "F2-Mapping time steps",
        "F3-Mapping Segment SICR",
        "F4-Histo PD Multi Non Retail",
        "F6-PD S1S2 Non Retail",
        "F8-LGD S1S2 Non Retail",
        "F12-CCF Non Retail"
    ]
}

# Configuration for starting row for each sheet (0-indexed), to be modified if necessary
SHEET_START_ROW_CONFIG: Dict[str, int] = {
    # Non Retail sheets
    "F1-Mapping fields Non Retail": 3,  # Start from row 4 (0-indexed)
    "F2-Mapping time steps": 3,         # Start from row 4
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
    # Non Retail sheets
    "F1-Mapping fields Non Retail": ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME"],
    "F2-Mapping time steps": ["NB_MONTHS"],
    "F3-Mapping Segment SICR": ["SEGMENT_REPORTING", "SEGMENT_ORIGINATION"],
    "F4-Histo PD Multi Non Retail": ["START_DATE_VALIDITY", "END_DATE_VALIDITY", "SEGMENT", "RATING"],
    "F6-PD S1S2 Non Retail": ["SEGMENT", "SCENARIO", "RATING"],
    "F8-LGD S1S2 Non Retail": ["IFRS9_MODEL_CODE", "SCENARIO"],
    "F12-CCF Non Retail": ["IFRS9_MODEL_CODE", "SCENARIO"],

    # Retail sheets, to be defined
    "Mapping fields Retail": ["Field1", "Field2"],
    "Data Import Retail": ["ImportField1", "ImportField2"]
}

# Configuration for mapping fields
MAPPING_FIELDS_TEMPLATES_CONFIG: Dict[Tuple[OperationType, OperationStatus], str] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): "F1-Mapping fields Non Retail",

    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): "Mapping fields Retail S1S2",

    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): "Mapping fields Retail S3"
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
        "F6-PD S1S2 Non Retail": [["IFRS9_PD_MODEL_AFTER_CRM", "RATING_CALCULATION"], ["IFRS9_PD_MODEL_CODE", "RATING"]]
    }
}

LGD_SHEET_MAPPING_CONFIG: Dict[Tuple[OperationType, OperationStatus], Dict[str, List[List[str]]]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        "F8-LGD S1S2 Non Retail": [["IFRS9_LGD_MODEL_AFTER_CRM"], ["IFRS9_LGD_MODEL_CODE"]]
    }
}


# Configuration for data loading per operation type and operation status
DATA_LOADER_CONFIG: Dict[Tuple[OperationType, OperationStatus], Dict[str, str]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): {
        'csv_separator': None,
        'decimal': ",",
        'encoding': 'utf-8',
        'engine': 'python',
        'dtype': {"Contract_id": str, 'Product_code': str}
    },

    # Retail S1+S2 configuration
    (OperationType.RETAIL, OperationStatus.PERFORMING): {
        'csv_separator': None,
        'decimal': ',',
        'encoding': 'utf-8',
        'engine': 'python',
        'dtype': None
    },

    # Retail S3 configuration
    (OperationType.RETAIL, OperationStatus.DEFAULTED): {
        'csv_separator': None,
        'decimal': ',',
        'encoding': 'utf-8',
        'engine': 'python',
        'dtype': None
    }
}


# Configuration for data required fields
DATA_REQUIRED_FIELDS_CONFIG: Dict[Tuple[OperationType, OperationStatus], List[str]] = {
    # Non Retail S1+S2 configuration
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING):[
        "OBLIGOR_RCT",
        "RATING_ORIGINATION_OBLIGOR_FOREIGN_CURRENCY",
        "RATING_ORIGINATION_OBLIGOR_LOCAL_CURRENCY",
        "RATING_OBLIGOR_FC",
        "RATING_OBLIGOR_LC",
        "CALCULATION_RATING",
        "CONTRACT_ID",
        "OPERATION_ID",
        "TRANCH_BEARER_RCT",
        "TRANCHE_TYPE",
        "IFRS9_BUCKET",
        "IFRS9_BUCKET_REASON",
        "EXPOSURE_START_DATE",
        "EXPOSURE_END_DATE",
        "CONTRACTUAL_CLIENT_RATE",
        "IFRS9_PD_MODEL_BEFORE_CRM",
        "IFRS9_PD_MODEL_AFTER_CRM",
        "IFRS9_LGD_MODEL_BEFORE_CRM",
        "IFRS9_LGD_MODEL_AFTER_CRM",
        "AMORTIZATION_TYPE",
        "PROVISIONING_BASIS",
        "ACCOUNTING_TYPE",
        "AS_OF_DATE",
        "PRODUCT_CODE",
        "CCF"
    ],

    # Retail sheets, to be defined
}
