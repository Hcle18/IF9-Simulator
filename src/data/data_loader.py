# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_data as bcls


class ExcelImporter(bcls.BaseImporter):
    '''
    Import Excel file.
    '''
    
    def load_data(self, sheet_name: Union[str, List[str], None]=None) -> pd.DataFrame:
        """
        Load data from Excel file and update the ECLOperationData container.
        
        Args:
            sheet_name: Name of sheet(s) to read
            
        Returns:
            pd.DataFrame: The loaded data
        """
        file_path = self.data.data_file_path
        
        if not file_path:
            raise ValueError("No data file path specified in ECLOperationData")
            
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if isinstance(df, dict):
                if sheet_name is None:
                    first_sheet = list(df.keys())[0]
                    if len(list(df.keys())) > 1:
                         logging.warning(f"Multiple sheets detected. Using the first sheet: {first_sheet}")
                    df = df[first_sheet]
            
            # Update the ECLOperationData container
            self.data.df = df
            logging.info(f"Excel data loaded successfully from {file_path}. Shape: {df.shape}")
            
            #return df
            
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        except ValueError as e:
            logging.error(f"Value error occurred while reading the file '{file_path}': {e}")
            raise ValueError(f"Value error occurred while reading the file '{file_path}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error occurred while reading the file '{file_path}': {e}")
            raise Exception(f"Unexpected error occurred while reading the file '{file_path}': {e}")

class ZipCSVImporter(bcls.BaseImporter):
    '''
    Import CSV files from a ZIP archive.
    '''

    def load_data(self, **kwargs) -> pd.DataFrame: 
        """
        Load data from ZIP file containing CSV files and update the ECLOperationData container.
        
        Returns:
            pd.DataFrame: The loaded and concatenated data
        """
        file_path = self.data.data_file_path
        
        if not file_path:
            raise ValueError("No data file path specified in ECLOperationData")
            
        try:
            # Get data configuration for the operation type and status
            # data_config = cst.DATA_LOADER_CONFIG.get(
            #     (self.data.operation_type, self.data.operation_status), {}
            # )
            
            # Read the zip file
            with zipfile.ZipFile(file_path, 'r') as zf:

                # List of all files inside the zip folder
                filelist = zf.namelist()

                # Focus on csv file(s)
                csv_files = fnmatch.filter(filelist, '*.csv')

                # Handle missing csv file
                if len(csv_files) == 0:
                    raise ValueError("Expected at least one csv. No csv file found inside the upload zip folder")
                
                # Read all the available csv files with the appropriate data config
                # csv_params = {
                #     'sep': data_config.get('csv_separator', None),
                #     'decimal': data_config.get('decimal', '.'),
                #     'encoding': data_config.get('encoding', 'utf-8'),
                #     'engine': data_config.get('engine', 'python'),
                #     'dtype': data_config.get('dtype', None)
                # }
                try:
                    data = [pd.read_csv(zf.open(csv_file), sep=";", decimal=",", dtype=str) for csv_file in csv_files]
                except Exception as e:
                    data = [pd.read_csv(zf.open(csv_file), sep=None, dtype=str) for csv_file in csv_files]
            
            # Handle invalid data
            if not data:
                logging.error(f"No valid CSV files found in the zip: {file_path}")
                raise ValueError(f"No valid CSV files found in the zip: {file_path}")

            # Warning if multiple CSV files are found
            if len(data) > 1:
                logging.warning(f"Multiple CSV files found in the zip: {file_path}. Concatenating all.")

            # Concatenate and return a dataframe
            concatenated_df = pd.concat(data, ignore_index=True)
            
            # Update the ECLOperationData container
            self.data.df = concatenated_df
            logging.info(f"ZIP CSV data loaded successfully from {file_path}. Shape: {concatenated_df.shape}")
            
            #return concatenated_df

        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            raise
        except ValueError as e:
            logging.error(f"Value error occurred while reading the file '{file_path}': {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error occurred while reading the file '{file_path}': {e}")
            raise

# Factory
def get_data_importer(ecl_operation_data: cst.ECLOperationData) -> bcls.BaseImporter:
    """
    Factory function to create appropriate importer based on file type.
    
    Args:
        file_path: Path to the data file
        operation_type: Type of operation (RETAIL, NON_RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        BaseImporter: Appropriate importer instance
    """
    file_path = ecl_operation_data.data_file_path

    if not os.path.exists(file_path):
        logging.error(f"The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    if file_path.lower().endswith(('.xlsx', '.xls')):
        logging.info(f"Creating ExcelImporter for file: {file_path}")
        return ExcelImporter(ecl_operation_data)
    
    elif file_path.lower().endswith('.zip'):
        logging.info(f"Creating ZipCSVImporter for file: {file_path}")
        return ZipCSVImporter(ecl_operation_data)
    
    else:
        logging.error(f"Unsupported file type: {file_path}. Please use one of the following:{', '.join(cst.SUPPORTED_FILE_TYPES)}")
        raise ValueError(f"Unsupported file type: '{Path(file_path).suffix}' for {file_path}")

# ==========================================
# ENTRY POINT TO CREATE DATA LOADER
# ==========================================
def data_loader(importer: bcls.BaseImporter) -> cst.ECLOperationData:
    """
    Load data using the provided importer.
    
    Args:
        importer: BaseImporter instance configured with ECLOperationData
        
    Returns:
        ECLOperationData: The updated container with loaded data
    """
    df = importer.load_data()
    
    if df is not None and not df.empty:
        logging.info(f"Data loaded successfully from {importer.data.data_file_path}. Shape: {df.shape}")
        # Data is already updated in the ECLOperationData container by the importer
        return importer.data
    else:
        logging.error("Failed to load data or data is empty.")
        raise ValueError("Failed to load data or data is empty.")

if __name__ == "__main__":
    # Example usage with the new ECLOperationData structure
    #file_name = "sample_non_retail.xlsx"
    file_name = "sample_non_retail.zip"
    file_path = os.path.join("sample", "data", file_name)

    # Create importer using the factory function
    importer = get_importer(
        file_path, 
        cst.OperationType.NON_RETAIL, 
        cst.OperationStatus.PERFORMING
    )
    
    print(f"Created importer: {type(importer).__name__}")
    print(f"Operation type: {importer.operation_type}")
    print(f"Operation status: {importer.operation_status}")
    
    # Load data using the data_loader function
    ecl_data = data_loader(importer)
    
    print(f"Data loaded successfully!")
    print(f"Data shape: {ecl_data.df.shape}")
    print(f"Data head:\n{ecl_data.df.head()}")
    print(f"Data types:\n{ecl_data.df.dtypes}")
    print(f"ECL data ready for calculation: {ecl_data.is_valid_for_calculation()}")