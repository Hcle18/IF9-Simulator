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
    Import Excel files.
    '''
    def __init__(self, file_path: str, sheet_name: Union[str, List[str], None]=None):
        '''
        Initialize the ExcelImporter.
        '''
        self.file_path = file_path
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
    def __init__(self, file_path: str, csv_file_name: str, **kwargs):
        self.file_path = file_path
        self.csv_file_name = csv_file_name

    def load_data(self) -> pd.DataFrame: 
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                with zf.open(self.csv_file_name) as f:
                    return pd.read_csv(f)
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
def get_importer(file_path: str, **kwargs) -> bcls.BaseImporter:
    if not os.path.exists(file_path):
        logging.error(f"The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    if file_path.lower().endswith(('.xlsx', '.xls')):
        logging.info(f"Creating ExcelImporter for file: {file_path}")
        return ExcelImporter(file_path, **kwargs)
    elif file_path.lower().endswith('.zip'):
        if 'csv_file_name' not in kwargs:
            logging.error("CSV file name must be provided for ZIP imports.")
            raise ValueError("CSV file name must be provided for ZIP imports.")
        logging.info(f"Creating ZipCSVImporter for file: {file_path}, csv_file_name: {kwargs['csv_file_name']}")
        return ZipCSVImporter(file_path, **kwargs)
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
    file_name = "sample_non_retail.xlsx"
    file_path = os.path.join("sample", "data", file_name)

    importer = get_importer(file_path)
    df = data_loader(importer)
    print(df.head())