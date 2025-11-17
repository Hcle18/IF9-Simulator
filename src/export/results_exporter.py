from src.core.librairies import *
from src.core import config as cst
from src.export.create_excel_report import create_excel_report, aggregate_results_sql

logger = logging.getLogger(__name__)

class ResultsExporter():
    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        self.data = ecl_operation_data

    def export_results(self, contexts: str, output_path: str):
        try:
            create_excel_report(contexts, output_path)
            logger.info(f"Results successfully exported to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting results: {e}")