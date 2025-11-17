from src.core.librairies import *

def get_data_identifier(data_path):

    if hasattr(data_path, 'name') and hasattr(data_path, 'getvalue'):
        data_identifier = data_path.name
    elif isinstance(data_path, str):
        data_identifier = data_path
    else:
        raise TypeError("Unsupported data_path type")
    return data_identifier
