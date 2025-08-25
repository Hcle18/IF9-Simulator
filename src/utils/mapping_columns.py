# Global import
from src.core.librairies import *

def normalize_field_name(field):
    """
    Normalize the field name by removing special characters and converting to lowercase.
    """
    if pd.isna(field):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(field).lower())

def mapping_columns(input_df, field_mapping):
    """
    Map the columns of the input DataFrame to the simulator fields.
    """
    # Create a normalized mapping dictionary
    normalized_mapping = {}
    for sim_field, client_field in field_mapping.items():
        if pd.notna(client_field):
            normalized_mapping[normalize_field_name(client_field)] = sim_field

    # Create a dictionary for renaming columns
    rename_dict = {}
    for col in input_df.columns:
        normalized_col = normalize_field_name(col)
        if normalized_col in normalized_mapping:
            rename_dict[col] = normalized_mapping[normalized_col]

    # Rename the DataFrame columns
    return input_df.rename(columns=rename_dict)