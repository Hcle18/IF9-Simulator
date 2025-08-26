from src.core.librairies import *

from src.core import config as cst
from src.templates import template_loader as tpld
from src.data import data_loader as dld
from src.data import data_validator as dvd
from src.ecl_calculation import ecl_calculator as calc

logger = logging.getLogger(__name__)

class OperationFactory:
    """
    Factory class for creating operation-related components.
    """
    def __init__(self, operation_type: cst.OperationType, operation_status: cst.OperationStatus, 
                 data_file_path: str, template_file_path: str):
        
        self.ecl_operation_data = cst.ECLOperationData(
            operation_type=operation_type,
            operation_status=operation_status,
            data_file_path=data_file_path,
            template_file_path=template_file_path,
            df=pd.DataFrame(),
            template_data={},
        )
        
        # Get data loader
        self.data_loader = dld.get_data_importer(self.ecl_operation_data)

        # Get template loader
        self.template_loader = tpld.template_loader(self.ecl_operation_data)

        # Get data validator
        self.data_validator = dvd.data_validator(self.ecl_operation_data)

        # Get ECL calculator
        self.ecl_calculator = calc.ecl_calculator(self.ecl_operation_data)

    def import_templates(self):
        """
        Import templates using the template loader.
        """
        self.template_loader.import_template()
    
    def validate_templates(self):
        self.template_loader.validate_template()
    
    def load_data(self, **kwargs) -> pd.DataFrame:
        """
        Load data using the data loader.
        """
        self.data_loader.load_data(**kwargs)

    def data_mapping_fields(self):
        self.data_validator.mapping_fields()

    def validate_data(self):
        self.data_validator.validate_data()
    
    def get_time_steps(self):
        self.ecl_calculator.get_time_steps()


if __name__ == "__main__":
    pass