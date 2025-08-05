from typing import Dict, List, Tuple
from .base_classes import OperationType, OperationStatus

# Excel sheets name to be used for importing data, depending on the operation type and status
TEMPLATE_SHEETS_CONFIG: Dict[Tuple[OperationType, OperationStatus], List[str]] = {

    # Retail Performing (S1 + S2)
    (OperationType.RETAIL, OperationStatus.PERFORMING): [
        "Mapping fields Retail", "Data Import Retail"
    ],

    # Retail Defaulted (S3)
    (OperationType.RETAIL, OperationStatus.DEFAULTED): [
        "Mapping fields Retail", "Data Import Retail"
    ],

    # Non Retail Performing (S1 + S2)
    (OperationType.NON_RETAIL, OperationStatus.PERFORMING): [
        "Mapping fields Non Retail", "Data Import Non Retail"
    ],

    # Non Retail Defaulted (S3)
    (OperationType.NON_RETAIL, OperationStatus.DEFAULTED): [
        "Mapping fields Non Retail", "Data Import Non Retail"
    ]
}