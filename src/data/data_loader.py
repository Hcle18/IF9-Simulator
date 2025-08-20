# Librairies
import os
import pandas as pd
from pathlib import Path
import zipfile
import fnmatch
import logging
from typing import Union, List, Dict

# Local import
from src.core import constants as cst
from src.core import base_classes as bcls

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
    
    def load_data(self) -> pd.DataFrame:
        try:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            if isinstance(df, dict):
                if self.sheet_name is None:
                    first_sheet = list(df.keys())[0]
                    if len(list(df.keys())) > 1:
                         logging.warning(f"Multiple sheets detected. Using the first sheet: {first_sheet}")
                    df = df[first_sheet]
            return df
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

    def load_data(self) -> pd.DataFrame: 
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
            return pd.concat(data, ignore_index=True)
        
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

def data_loader(importer: bcls.BaseImporter) -> pd.DataFrame:
    '''
    Load data using the provided importer.
    '''
    df = importer.load_data()
    if df is not None and not df.empty:
        logging.info(f"Data loaded successfully from {importer.file_path}. Shape: {df.shape}")
        return df
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
    df = data_loader(importer)
    print(df.head())
    print(df.dtypes)