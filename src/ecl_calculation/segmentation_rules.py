from src.core.librairies import *

from src.core import config as cst
from src.utils import coerce_series_to_type

logger = logging.getLogger(__name__)

def parse_cell_conditions(cell_value: Any) -> Tuple[str, Any, Any]:

    if pd.isna(cell_value) or str(cell_value).strip() == "":
        return (None, None, None)
    
    text = str(cell_value).strip()

    # Split operator and value by first ":" delimiter
    if ":" in text:
        op_str, val_str = text.split(":", 1)
        op = op_str.strip().upper()
        val = val_str.strip()
    elif text.strip().upper() in ("IS NULL", "IS NOT NULL"):
        op = text.strip().upper()
        val = None
    else:
        op = None
        val = text.strip()

    # Get values, according to operator type
    value = None
    value_to = None

    if op in {"IS NULL", "IS NOT NULL"}:
        value = None

    elif op in {"IN", "NOT IN", "CONTAINS", "NOT CONTAINS", "REGEX"}:
        value = [v.strip().replace('"', '').replace("'", '') 
                 for v in re.split(r",", val) 
                 if v.strip() != ""]
    elif op in {"BETWEEN", "NOT BETWEEN"}:
        rng = [p.strip() for p in re.split(r"\.\.|;", val) if p.strip() != ""]
        if len(rng) >=2:
            value, value_to = rng[0], rng[1]
        else:
            value = None
            value_to = None
    else:
        # scalar
        value = val
    return op, value, value_to


def build_rules_from_columns_sheet(columns_df: pd.DataFrame,
                                   dict_config: Dict,
                                   dict_key: Tuple[str, str],
                                   template_data:Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build segmentation rules from the columns sheet.
    Args:
        columns_df (pd.DataFrame): DataFrame containing the columns sheet data.
        dict_config (Dict): Configuration dictionary for rules sheets.
        dict_key (Tuple[str, str]): Key to identify the operation type and status.
        template_data (Dict[str, pd.DataFrame]): Dictionary of template data.
    Returns:
        pd.DataFrame: DataFrame containing the segmentation rules.
    """

    if not {"SEGMENT", "TYPE_MODEL"}.issubset(columns_df.columns.str.strip().str.upper()):
        logger.warning("No 'SEGMENT' or 'TYPE_MODEL' column found in columns sheet. Skipping rules building.")
        return pd.DataFrame()
    
    rules_rows = []

    for idx, row in columns_df.reset_index(drop=True).iterrows():

        rule_id = f"RULE_{idx+1}"
        segment = str(row.get("SEGMENT")).strip()
        type_model = str(row.get("TYPE_MODEL")).strip().upper()
        target_column = None

        if not segment or pd.isna(segment) or not type_model or pd.isna(type_model):
            continue

        # Get target column for the type model, only if there is an associated curve sheet
        dict_target_config = dict_config.get(dict_key)
        if dict_target_config:
            dict_target = dict_target_config.get(type_model)
            if isinstance(dict_target, dict) and dict_target and template_data:
                template_curve, target_col_name = next(iter(dict_target.items()))
                template_curve_df = template_data.get(template_curve)

                if template_curve_df is not None and not template_curve_df.empty:
                    curve_column = template_curve_df.iloc[:, 0].dropna().astype(str).str.strip()
                    if segment in curve_column.unique():
                        target_column = str(target_col_name).strip()
                    else:
                        type_model = None 
                        logger.info(f"Lack of curve definition for segment '{segment}' in template '{template_curve}'. Skipping this rule.")
                        
            else:
                logger.info(f"No curve template defined for type model '{type_model}' under key '{dict_key}'. Skipping target column assignment.")
        for col in columns_df.columns:
            if col in {"SEGMENT", "TYPE_MODEL"}:
                continue
            op, value, value_to = parse_cell_conditions(row[col])
            if op is None and value is None and value_to is None:
                continue

            # Normalize value to string for storage
            val_str = value if isinstance(value, str) else ("|".join(value) if isinstance(value, list) 
                                                            else value)
            rules_rows.append({
                "RULE_ID": rule_id,
                "DRIVER": col,
                "OPERATOR": op,
                "VALUE": val_str,
                "VALUE_TO": value_to,
                "SEGMENT": segment,
                "TYPE_MODEL": type_model,
                "TARGET_COLUMN": target_column
            })
    if not rules_rows:
        return pd.DataFrame(columns=["RULE_ID", "DRIVER", "OPERATOR", "VALUE", "VALUE_TO", 
                                     "SEGMENT", "TYPE_MODEL", "TARGET_COLUMN"])

    rules_df = pd.DataFrame(rules_rows)

    return rules_df

def parse_list_values(value:Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip().upper() for v in value if str(v).strip() != ""]
    if pd.isna(value) or str(value).strip() == "":
        return []
    # split by , or |
    txt = str(value).strip()
    parts = re.split(r"[|,]", txt)
    return [p.strip().upper() for p in parts if p.strip() != ""]

def build_condition_mask(col: pd.Series,
                         operator:str,
                         dict_config:dict,
                         dict_key:Tuple[str, str],
                         template_data:Dict[str, pd.DataFrame],
                         value:Any,
                         value_to:Any = None) -> pd.Series:
    op = operator.strip().upper()
    value_type = None
    # Get value type from configuration
    template_name = dict_config.get(dict_key)
    driver_df = template_data.get(template_name)
    if driver_df is not None and not driver_df.empty:
        dict_driver = dict(zip(driver_df["CALCULATOR_COLUMN_NAME"], 
                               driver_df["VALUE_TYPE"]))
        value_type = dict_driver.get(col.name.strip().upper())
    else:
        logger.info(f"No driver template found for key '{dict_key}'. Skipping value type retrieval.")
    
    # Prepare series typing and normalization
    series = coerce_series_to_type(col, value_type) 
    if value_type == "STRING":
        series = series.apply(lambda x: str(x).strip().upper() if not pd.isna(x) else pd.NA)
    
    # Prepare comparison value(s)
    if op in {"IN", "NOT IN", "CONTAINS", "NOT CONTAINS", "STARTS WITH", "ENDS WITH", "REGEX"}:
        values = parse_list_values(value)
        values_norm = [v.strip() for v in values]
    else:
        values = value
        values_norm = value
    
    # Build condition mask
    if op in {"EQ", "="}:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "STRING":
            rhs = str(rhs).upper().strip() if rhs is not None else rhs
        return series == rhs

    if op in {"NE", "!="}:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "STRING":
            rhs = str(rhs).upper().strip() if rhs is not None else rhs
        return series != rhs

    if op == "IN":
        if value_type == "NUMBER":
            coerced = pd.to_numeric(values_norm, errors='coerce')
            values_norm = coerced.dropna().unique().tolist()
        elif value_type == "DATE":
            coerced = pd.to_datetime(values_norm, errors='coerce')
            values_norm = coerced.dropna().unique().tolist()
        return series.isin(values_norm)
    if op == "NOT IN":
        if value_type == "NUMBER":
            coerced = pd.to_numeric(values_norm, errors='coerce')
            values_norm = coerced.dropna().unique().tolist()
        elif value_type == "DATE":
            coerced = pd.to_datetime(values_norm, errors='coerce')
            values_norm = coerced.dropna().unique().tolist()
        return ~series.isin(values_norm)
    if op in {"GT", ">" }:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        return series > rhs
    if op in {"GE", ">=" }:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        return series >= rhs
    if op in {"LT", "<" }:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        return series < rhs
    if op in {"LE", "<=" }:
        rhs = values_norm
        if value_type == "NUMBER":
            rhs = pd.to_numeric(rhs, errors='coerce') if rhs is not None else rhs
        elif value_type == "DATE":
            rhs = pd.to_datetime(rhs, errors='coerce') if rhs is not None else rhs
        return series <= rhs
    if op == "BETWEEN":
        lo = pd.to_numeric(value, errors='coerce')
        hi = pd.to_numeric(value_to, errors='coerce')
        return (series >= lo) & (series < hi)
    if op == "NOT BETWEEN":
        lo = pd.to_numeric(value, errors='coerce')
        hi = pd.to_numeric(value_to, errors='coerce')
        return (series < lo) | (series >= hi)
    if op == "IS NULL":
        return series.isna()
    if op == "IS NOT NULL":
        return ~series.isna()
    if op == "CONTAINS":
        return series.astype(str).str.contains('|'.join(values_norm), na=False, case=False, regex=False)
    if op == "NOT CONTAINS":
        return ~series.astype(str).str.contains('|'.join(values_norm), na=False, case=False, regex=False)
    if op == "STARTS WITH":
        mask = pd.Series(False, index=series.index)
        for v in values_norm:
            mask |= series.astype(str).str.startswith(v, na=False)
        return mask
    if op == "ENDS WITH":
        mask = pd.Series(False, index=series.index)
        for v in values_norm:
            mask |= series.astype(str).str.endswith(v, na=False)
        return mask
    if op == "REGEX":
        pattern = '|'.join(values_norm)
        return series.astype(str).str.match(pattern, na=False)
    
    # Default: return all False
    return pd.Series(False, index=series.index)