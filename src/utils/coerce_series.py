from src.core.librairies import *

def coerce_series_to_type(series: pd.Series, value_type: Optional[str]) -> pd.Series:
    """
    Coerce a pandas Series to the specified data type.

    Args:
        series (pd.Series): The input pandas Series.
        value_type (Optional[str]): The target data type as a string. 
                                    Supported types: 'string', 'integer', 'float', 'date', None.

    Returns:
        pd.Series: The coerced pandas Series.
    """
    if value_type is None:
        return series
    vt = str(value_type).strip().upper()

    if vt == "NUMBER":
        series_cleaned = series.astype(str).str.replace(',', '.')
        series_cleaned[series.isna()] = pd.NA
        return pd.to_numeric(series_cleaned, errors='coerce')
    if vt == "DATE":
        return pd.to_datetime(series, errors='coerce')
    if vt == "DATE_DAYFIRST":
        return pd.to_datetime(series, dayfirst=True, errors='coerce')
    if vt == "STRING":
        result = series.apply(clean_value).astype("string")
        return result
    
    return series

def clean_value(val):
    if pd.isna(val):
        return pd.NA
    if isinstance(val, float) and val.is_integer():
        return str(int(val)).strip() # Remove leading zeros for float integers
    return str(val).strip()

