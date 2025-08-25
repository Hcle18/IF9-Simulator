# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_data as bcls
from src.core import base_template as tplm
from src.data import data_loader as dl
from src.templates import template_loader as tpl

logger = logging.getLogger(__name__)


# ========================================
# 1. Non Retail S1+S2 data validation
# ========================================
class NRS1S2DataValidator(bcls.BaseValidator):
    '''
    Custom class for Non Retail S1+S2 data validation
    '''
    def __init__(self, simu_data: bcls.OperationData, template_data: tplm.TemplateData):
        super().__init__(simu_data, template_data)

    def data_validator(self):
        pass


if __name__ == "__main__": 

    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING

    # Simulation data
    file_name = "sample_non_retail.zip"
    file_path = os.path.join("sample", "data", file_name)

    importer = dl.get_importer(file_path, operation_type, operation_status)
    #print(importer)
    
    # Templates
    template_path = r".\sample\templates\Template_outil_V1.xlsx"
    template_loader = tpl.template_loader(operation_type, operation_status, template_path)
    #print(template_loader.required_sheets)

    # Importing & validating templates
    NR_template_data = template_loader.template_importer()
    print(NR_template_data)
    template_validation = template_loader.validate_template(NR_template_data)

    # Data loader
    operation_nr_data = dl.data_loader(importer)
    print(f"Operation NR Data Columns: {operation_nr_data.data.columns}")
    # Data validation
    NR_data_validator = NRS1S2DataValidator(operation_nr_data, NR_template_data)
    df_mapped = NR_data_validator.mapping_fields()
    print(f"After mapping Data Columns: {df_mapped.columns}")
