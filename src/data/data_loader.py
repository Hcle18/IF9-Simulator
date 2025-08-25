# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_data as bcls


class ExcelImporter(bcls.BaseImporter):
    '''
    Import Excel file.
    '''
    def __init__(self, file_path: str,
                 operation_type: cst.OperationType,
                 operation_status: cst.OperationStatus,
                 sheet_name: Union[str, List[str], None]=None):
        '''
        Initialize the ExcelImporter.
        '''
        # Call parent constructor
        super().__init__(file_path, operation_type, operation_status)
        
        # Child attributes for selecting sheet name
        self.sheet_name = sheet_name
    
    def load_data(self) -> bcls.OperationData:
        try:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            if isinstance(df, dict):
                if self.sheet_name is None:
                    first_sheet = list(df.keys())[0]
                    if len(list(df.keys())) > 1:
                         logging.warning(f"Multiple sheets detected. Using the first sheet: {first_sheet}")
                    df = df[first_sheet]
            return bcls.OperationData(data=df, operation_type=self.operation_type, operation_status=self.status)
        except FileNotFoundError:
            logging.error(f"File not found: {self.file_path}")
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except ValueError as e:
            logging.error(f"Value error occurred while reading the file '{self.file_path}': {e}")
            raise ValueError(f"Value error occurred while reading the file '{self.file_path}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred while reading the file '{self.file_path}': {e}")
            raise Exception(f"Unexpected error occurred while reading the file '{self.file_path}': {e}")

class ZipCSVImporter(bcls.BaseImporter):
    '''
    Import CSV files from a ZIP archive.
    '''
    def __init__(self, file_path: str, 
                 operation_type: cst.OperationType,
                 operation_status: cst.OperationStatus):
        
        # Inherit from BaseImporter
        super().__init__(file_path, operation_type, operation_status)

    def load_data(self) -> bcls.OperationData: 
        try:
            # Get data configuration for the operation type and status
            data_config = cst.DATA_LOADER_CONFIG.get(
                (self.operation_type, self.status), {}
            )
            # Read the zip file
            with zipfile.ZipFile(self.file_path, 'r') as zf:

                # List of all files inside the zip folder
                filelist = zf.namelist()

                # Focus on csv file(s)
                csv_files = fnmatch.filter(filelist, '*.csv')

                # Handle missing csv file
                if len(csv_files) == 0:
                    raise ValueError("Expected at least one csv. No csv file found inside the upload zip folder")
                
                # Read all the available csv files with the appropriate data config
                csv_params = {
                    'sep': data_config.get('csv_separator', None),
                    'decimal': data_config.get('decimal', '.'),
                    'encoding': data_config.get('encoding', 'utf-8'),
                    'engine': data_config.get('engine', 'python'),
                    'dtype': data_config.get('dtype', None)
                }

                data = [pd.read_csv(zf.open(csv_file), **csv_params) for csv_file in csv_files]
            
            # Handle invalid data
            if not data:
                logging.error(f"No valid CSV files found in the zip: {self.file_path}")
                raise ValueError(f"No valid CSV files found in the zip: {self.file_path}")

            # Warning if multiple CSV files are found
            if len(data) > 1:
                logging.warning(f"Multiple CSV files found in the zip: {self.file_path}. Concatenating all.")

            # Concatenate and return a dataframe
            return bcls.OperationData(data=bcls.pd.concat(data, ignore_index=True),
                                       operation_type=self.operation_type,
                                       operation_status=self.status)

        except FileNotFoundError:
            logging.error(f"File not found: {self.file_path}")
            raise
        except ValueError as e:
            logging.error(f"Value error occurred while reading the file '{self.file_path}': {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error occurred while reading the file '{self.file_path}': {e}")
            raise

# Factory
def get_importer(file_path: str, 
                 operation_type: cst.OperationType = None, 
                 operation_status: cst.OperationStatus = None) -> bcls.BaseImporter:
    
    if not os.path.exists(file_path):
        logging.error(f"The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    if file_path.lower().endswith(('.xlsx', '.xls')):
        logging.info(f"Creating ExcelImporter for file: {file_path}")
        return ExcelImporter(file_path, operation_type, operation_status)
    
    elif file_path.lower().endswith('.zip'):
        logging.info(f"Creating ZipCSVImporter for file: {file_path}")
        return ZipCSVImporter(file_path, operation_type, operation_status)
    
    else:
        logging.error(f"Unsupported file type: {file_path}. Please use one of the following:{', '.join(cst.SUPPORTED_FILE_TYPES)}")
        raise ValueError(f"Unsupported file type: {file_path}")

# ==========================================
# ENTRY POINT TO CREATE DATA LOADER
# ==========================================
def data_loader(importer: bcls.BaseImporter) -> bcls.OperationData:
    '''
    Load data using the provided importer.
    '''
    operation = importer.load_data()
    if operation.data is not None and not operation.data.empty:
        logging.info(f"Data loaded successfully from {importer.file_path}. Shape: {operation.data.shape}")
        return operation
    else:
        logging.error("Failed to load data or data is empty.")
        raise ValueError("Failed to load data or data is empty.")




if __name__ == "__main__":
    # Example usage
    #file_name = "sample_non_retail.xlsx"
    file_name = "sample_non_retail.zip"
    file_path = os.path.join("sample", "data", file_name)

    importer = get_importer(file_path, cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING)
    #importer = get_importer(file_path)
    print(importer)
    df = data_loader(importer).data
    print(df.head())
    print(df.dtypes)