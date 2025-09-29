# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
import re

logger = logging.getLogger(__name__)


def infer_driver_columns(segmentation_df: pd.DataFrame) -> List[str]:
    """
    Infer driver columns from the template by excluding the target 'SEGMENT' column.
    """
    return [col for col in segmentation_df.columns if col.upper() != "SEGMENT"]


def normalize_str_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def build_segmentation_key(df: pd.DataFrame, cols: List[str]) -> pd.Series:
    if not cols:
        return pd.Series([""] * len(df), index=df.index)
    parts = []
    for col in cols:
        if col not in df.columns:
            return pd.Series([np.nan] * len(df), index=df.index)
        part = df[col]
        if part.dtype == 'object':
            part = normalize_str_series(part)
        parts.append(part.astype(str))
    return pd.Series(["||".join(values) for values in zip(*parts)], index=df.index)


def apply_segmentation_by_drivers(
    ecl_data: cst.ECLOperationData,
    simulation_df: pd.DataFrame,
    target_segment_col: str = "SEGMENT_BY_DRIVERS",
    driver_mapping: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Apply segmentation based on driver columns defined in the template sheet 'F5-Segmentation by Drivers'.

    - If driver_mapping is provided, map template driver -> simulation column. Otherwise, use identical names.
    - Matches rows on exact equality of all declared drivers.
    - The template may contain any number of driver columns; the only required column is 'SEGMENT'.

    Returns a copy of the simulation_df with an added column target_segment_col.
    """
    template_key = (ecl_data.operation_type, ecl_data.operation_status)
    sheet_name = "F5-Segmentation by Drivers"

    if ecl_data.template_data is None or sheet_name not in ecl_data.template_data:
        logger.warning("Segmentation template sheet '%s' not found; skipping segmentation.", sheet_name)
        result = simulation_df.copy()
        result[target_segment_col] = np.nan
        return result

    segmentation_df = ecl_data.template_data[sheet_name].copy()
    if segmentation_df.empty:
        logger.warning("Segmentation template '%s' is empty; skipping.", sheet_name)
        result = simulation_df.copy()
        result[target_segment_col] = np.nan
        return result

    # Infer drivers from template
    template_driver_cols = infer_driver_columns(segmentation_df)
    if not template_driver_cols:
        logger.warning("No driver columns found in '%s'; only 'SEGMENT' present.")
        result = simulation_df.copy()
        # Broadcast a single segment value if present; else NaN
        single_segment = segmentation_df["SEGMENT"].iloc[0] if "SEGMENT" in segmentation_df.columns and len(segmentation_df) > 0 else np.nan
        result[target_segment_col] = single_segment
        return result

    # Build mapping template_driver -> simulation_column
    driver_mapping = driver_mapping or {d: d for d in template_driver_cols}

    # Validate simulation columns
    missing_sim_cols = [sim_col for sim_col in driver_mapping.values() if sim_col not in simulation_df.columns]
    if missing_sim_cols:
        raise ValueError(f"Missing simulation columns for driver mapping: {missing_sim_cols}")

    # Normalize template drivers
    for col in template_driver_cols:
        if segmentation_df[col].dtype == 'object':
            segmentation_df[col] = normalize_str_series(segmentation_df[col])
    if "SEGMENT" in segmentation_df.columns and segmentation_df["SEGMENT"].dtype == 'object':
        segmentation_df["SEGMENT"] = segmentation_df["SEGMENT"].astype(str).str.strip()

    # Remove rows with missing any driver
    segmentation_df = segmentation_df.dropna(subset=template_driver_cols)
    segmentation_df = segmentation_df.drop_duplicates(subset=template_driver_cols)

    # Build join keys
    segmentation_df["__seg_key"] = build_segmentation_key(segmentation_df, template_driver_cols)

    sim_df = simulation_df.copy()
    for tmpl_col, sim_col in driver_mapping.items():
        if sim_df[sim_col].dtype == 'object':
            sim_df[sim_col] = normalize_str_series(sim_df[sim_col])
    sim_df["__seg_key"] = build_segmentation_key(sim_df, list(driver_mapping.values()))

    # Left join to fetch SEGMENT
    merged = sim_df.merge(
        segmentation_df[["__seg_key", "SEGMENT"]],
        how="left",
        on="__seg_key",
        suffixes=("", "_tmpl"),
    )

    # Assign target segment column
    merged[target_segment_col] = merged["SEGMENT"]

    # Cleanup temp columns
    merged = merged.drop(columns=[col for col in ["__seg_key", "SEGMENT"] if col in merged.columns])

    return merged 


def _coerce_series_to_type(series: pd.Series, value_type: Optional[str]) -> pd.Series:
    if value_type is None:
        return series
    vt = str(value_type).strip().upper()
    if vt == "NUMBER":
        return pd.to_numeric(series, errors='coerce')
    if vt == "DATE":
        return pd.to_datetime(series, errors='coerce')
    return series.astype(str)


def _parse_list_values(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if pd.isna(value):
        return []
    # split by comma or |
    txt = str(value)
    parts = re.split(r"[|,]", txt)
    return [p.strip() for p in parts if p.strip() != ""]


def _build_condition_mask(col: pd.Series, operator: str, value: Any, value_to: Any = None, case_sensitive: bool = False, value_type: Optional[str] = None) -> pd.Series:
    op = operator.strip().upper()
    # prepare series typing and normalization
    series = _coerce_series_to_type(col, value_type)
    if series.dtype == 'object' and not case_sensitive:
        series = series.astype(str).str.upper().str.strip()
    # value preparations
    if op in {"IN", "NOT IN", "CONTAINS", "NOT CONTAINS", "STARTS WITH", "ENDS WITH", "REGEX"}:
        values = _parse_list_values(value)
        values_norm = [v.upper().strip() if not case_sensitive else v for v in values]
    else:
        values = value
        values_norm = value

    if op == "EQ":
        rhs = values_norm
        if series.dtype == 'object' and not case_sensitive:
            rhs = str(rhs).upper().strip() if rhs is not None else rhs
        return series == rhs
    if op == "NE":
        rhs = values_norm
        if series.dtype == 'object' and not case_sensitive:
            rhs = str(rhs).upper().strip() if rhs is not None else rhs
        return series != rhs
    if op == "IN":
        return series.isin(values_norm)
    if op == "NOT IN":
        return ~series.isin(values_norm)
    if op == "LT":
        return series < pd.to_numeric(values, errors='coerce')
    if op == "LE":
        return series <= pd.to_numeric(values, errors='coerce')
    if op == "GT":
        return series > pd.to_numeric(values, errors='coerce')
    if op == "GE":
        return series >= pd.to_numeric(values, errors='coerce')
    if op == "BETWEEN":
        lo = pd.to_numeric(values, errors='coerce')
        hi = pd.to_numeric(value_to, errors='coerce')
        return series.between(lo, hi, inclusive='both')
    if op == "NOT BETWEEN":
        lo = pd.to_numeric(values, errors='coerce')
        hi = pd.to_numeric(value_to, errors='coerce')
        return ~series.between(lo, hi, inclusive='both')
    if op == "CONTAINS":
        if len(values_norm) == 0:
            return pd.Series(False, index=series.index)
        mask = pd.Series(False, index=series.index)
        for v in values_norm:
            mask = mask | series.astype(str).str.contains(re.escape(v), case=case_sensitive, na=False)
        return mask
    if op == "NOT CONTAINS":
        if len(values_norm) == 0:
            return pd.Series(True, index=series.index)
        mask = pd.Series(True, index=series.index)
        for v in values_norm:
            mask = mask & ~series.astype(str).str.contains(re.escape(v), case=case_sensitive, na=False)
        return mask
    if op == "STARTS WITH":
        if len(values_norm) == 0:
            return pd.Series(False, index=series.index)
        mask = pd.Series(False, index=series.index)
        for v in values_norm:
            mask = mask | series.astype(str).str.startswith(v, na=False)
        return mask
    if op == "ENDS WITH":
        if len(values_norm) == 0:
            return pd.Series(False, index=series.index)
        mask = pd.Series(False, index=series.index)
        for v in values_norm:
            mask = mask | series.astype(str).str.endswith(v, na=False)
        return mask
    if op == "REGEX":
        if len(values_norm) == 0:
            return pd.Series(False, index=series.index)
        pattern = values[0] if isinstance(values, list) else values
        try:
            return series.astype(str).str.contains(pattern, regex=True, na=False)
        except re.error:
            return pd.Series(False, index=series.index)
    if op == "IS NULL":
        return series.isna() | (series.astype(str).str.len() == 0)
    if op == "IS NOT NULL":
        return ~(series.isna() | (series.astype(str).str.len() == 0))
    # fallback false
    return pd.Series(False, index=series.index)


def apply_segmentation_by_rules(
    ecl_data: cst.ECLOperationData,
    simulation_df: pd.DataFrame,
    target_segment_col: str = "SEGMENT_BY_DRIVERS",
    driver_mapping: Optional[Dict[str, str]] = None,
    rules_sheet: str = "F5-Segmentation Rules",
) -> pd.DataFrame:
    """
    Apply rule-based segmentation defined in the normalized rules sheet.

    Expected columns in rules sheet:
    - RULE_ID: groups conditions that must all be satisfied (AND) within one rule
    - DRIVER: template driver column name
    - OPERATOR: one of supported operators (EQ, NE, IN, NOT IN, LT, LE, GT, GE, BETWEEN, NOT BETWEEN, STARTS WITH, ENDS WITH, CONTAINS, NOT CONTAINS, REGEX, IS NULL, IS NOT NULL)
    - VALUE: value or list (comma or | separated); for BETWEEN, lower bound
    - VALUE_TO: optional, upper bound for BETWEEN operators
    - SEGMENT: resulting segment name for the rule
    - PRIORITY: optional integer; lower numbers applied first
    - CASE_SENSITIVE: optional Y/N
    - VALUE_TYPE: optional STRING/NUMBER/DATE for explicit coercion

    Rules are applied in ascending PRIORITY, then by RULE_ID order. First match assigns the segment and is not overwritten by later rules.
    """
    if ecl_data.template_data is None or rules_sheet not in ecl_data.template_data:
        logger.info("Rules sheet '%s' not found; skipping rule-based segmentation.", rules_sheet)
        result = simulation_df.copy()
        if target_segment_col not in result.columns:
            result[target_segment_col] = np.nan
        return result

    rules = ecl_data.template_data[rules_sheet].copy()
    if rules.empty:
        result = simulation_df.copy()
        if target_segment_col not in result.columns:
            result[target_segment_col] = np.nan
        return result

    # Normalize columns
    required_cols = ["RULE_ID", "DRIVER", "OPERATOR", "SEGMENT", "VALUE"]
    for col in required_cols:
        if col not in rules.columns:
            raise ValueError(f"Rules sheet missing required column: {col}")

    rules["OPERATOR"] = rules["OPERATOR"].astype(str).str.strip().str.upper()
    rules["DRIVER"] = rules["DRIVER"].astype(str).str.strip()

    # Build driver mapping template_driver -> simulation_column
    if driver_mapping is None:
        # default 1-1 mapping on demand during evaluation
        driver_mapping = {}

    df = simulation_df.copy()
    # Track assignment mask
    assigned = pd.Series(False, index=df.index)
    if target_segment_col not in df.columns:
        df[target_segment_col] = np.nan

    # Sort by PRIORITY then RULE_ID for determinism
    if "PRIORITY" in rules.columns:
        rules["__PRIORITY_SORT"] = pd.to_numeric(rules["PRIORITY"], errors='coerce').fillna(np.inf)
    else:
        rules["__PRIORITY_SORT"] = np.inf

    for rule_id, group in rules.sort_values(["__PRIORITY_SORT", "RULE_ID"]).groupby("RULE_ID", sort=False):
        # Build combined mask with AND across rows for this RULE_ID
        mask = pd.Series(True, index=df.index)
        seg_value = None
        case_sensitive = False
        for _, row in group.iterrows():
            tmpl_driver = row["DRIVER"]
            sim_col = driver_mapping.get(tmpl_driver, tmpl_driver)
            if sim_col not in df.columns:
                # Missing column -> rule cannot apply
                mask = pd.Series(False, index=df.index)
                break
            operator = row["OPERATOR"]
            value = row.get("VALUE", None)
            value_to = row.get("VALUE_TO", None)
            val_type = row.get("VALUE_TYPE", None)
            cs = row.get("CASE_SENSITIVE", None)
            if isinstance(cs, str):
                case_sensitive = (cs.strip().upper() in {"Y", "YES", "TRUE"})
            seg_value = row.get("SEGMENT", seg_value)

            col_series = df[sim_col]
            cond = _build_condition_mask(col_series, operator, value, value_to, case_sensitive, val_type)
            mask = mask & cond
        # Assign where rule matches and not yet assigned
        apply_mask = mask & (~assigned)
        if seg_value is not None:
            df.loc[apply_mask, target_segment_col] = seg_value
        assigned = assigned | apply_mask

    # Cleanup temp
    if "__PRIORITY_SORT" in rules.columns:
        rules.drop(columns=["__PRIORITY_SORT"], inplace=True, errors='ignore')

    return df 


def _parse_cell_condition(cell_value: Any) -> Tuple[str, Any, Any, Optional[bool], Optional[str]]:
    """
    Parse a single driver cell formatted as 'OPERATOR: value [|flags]'.
    Returns: (operator, value, value_to, case_sensitive, value_type)
    """
    if pd.isna(cell_value) or str(cell_value).strip() == "":
        return None, None, None, None, None
    text = str(cell_value).strip()
    # Split flags from the right by '|'
    parts = [p.strip() for p in text.split('|')]
    base = parts[0]
    flags = set([p.strip().lower() for p in parts[1:]]) if len(parts) > 1 else set()

    case_sensitive = True if ('cs' in flags or 'case' in flags) else False
    value_type = None
    if 'num' in flags or 'number' in flags:
        value_type = 'NUMBER'
    elif 'date' in flags:
        value_type = 'DATE'

    # Split operator and value by first ':'
    if ':' in base:
        op_str, val_str = base.split(':', 1)
        op = op_str.strip().upper()
        val = val_str.strip()
    else:
        # For operators without value like IS NULL
        op = base.strip().upper()
        val = None

    value = None
    value_to = None

    if op in {"IS NULL", "IS NOT NULL"}:
        value = None
    elif op in {"IN", "NOT IN", "CONTAINS", "NOT CONTAINS", "REGEX"}:
        value = [v.strip() for v in re.split(r",", val) if v.strip() != ""]
    elif op in {"BETWEEN", "NOT BETWEEN"}:
        # split on .. or ,
        rng = [p.strip() for p in re.split(r"\.\.|,", val) if p.strip() != ""]
        if len(rng) >= 2:
            value, value_to = rng[0], rng[1]
        elif len(rng) == 1:
            value = rng[0]
            value_to = rng[0]
        else:
            value = None
            value_to = None
    else:
        # scalar
        value = val

    return op, value, value_to, case_sensitive, value_type


def build_rules_from_columns_sheet(columns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a driver-in-columns sheet into normalized rules DataFrame.

    Input columns:
    - SEGMENT (required)
    - Any other columns are driver names with cell syntax 'OP: value[|flags]'

    Output normalized rules with columns:
    - RULE_ID, DRIVER, OPERATOR, VALUE, VALUE_TO, SEGMENT, PRIORITY, CASE_SENSITIVE, VALUE_TYPE
    RULE_ID is generated per row.
    PRIORITY defaults to row order (1..N).
    """
    if "SEGMENT" not in columns_df.columns:
        raise ValueError("F5-Segmentation Columns sheet must contain 'SEGMENT' column.")

    rules_rows = []
    # Default priority by row order
    for idx, row in columns_df.reset_index(drop=True).iterrows():
        rule_id = f"COL_{idx+1}"
        segment = row["SEGMENT"]
        priority = idx + 1
        for col in columns_df.columns:
            if col == "SEGMENT":
                continue
            op, value, value_to, cs, vtype = _parse_cell_condition(row[col])
            if op is None:
                continue
            # Normalize value to string for storage
            val_str = value if isinstance(value, str) else ("|".join(value) if isinstance(value, list) else value)
            rules_rows.append({
                "RULE_ID": rule_id,
                "DRIVER": col,
                "OPERATOR": op,
                "VALUE": val_str,
                "VALUE_TO": value_to,
                "SEGMENT": segment,
                "PRIORITY": priority,
                "CASE_SENSITIVE": 'Y' if cs else 'N',
                "VALUE_TYPE": vtype or ''
            })
    if not rules_rows:
        # Empty rules -> return empty normalized DataFrame
        return pd.DataFrame(columns=["RULE_ID","DRIVER","OPERATOR","VALUE","VALUE_TO","SEGMENT","PRIORITY","CASE_SENSITIVE","VALUE_TYPE"])

    rules_df = pd.DataFrame(rules_rows)
    return rules_df


def apply_segmentation_by_columns(
    ecl_data: cst.ECLOperationData,
    simulation_df: pd.DataFrame,
    target_segment_col: str = "SEGMENT_BY_DRIVERS",
    columns_sheet: str = "F5-Segmentation Columns",
    driver_mapping: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Read the columns-driven sheet, convert to normalized rules, then evaluate with apply_segmentation_by_rules.
    """
    if ecl_data.template_data is None or columns_sheet not in ecl_data.template_data:
        logger.info("Columns sheet '%s' not found; skipping columns-based segmentation.", columns_sheet)
        result = simulation_df.copy()
        if target_segment_col not in result.columns:
            result[target_segment_col] = np.nan
        return result

    cols_df = ecl_data.template_data[columns_sheet].copy()
    rules_df = build_rules_from_columns_sheet(cols_df)
    # Reuse evaluator by injecting the rules_df as if it were the rules sheet
    ecl_copy = cst.ECLOperationData(
        operation_type=ecl_data.operation_type,
        operation_status=ecl_data.operation_status,
        template_file_path=ecl_data.template_file_path,
        data_file_path=ecl_data.data_file_path,
        df=ecl_data.df,
        template_data={"__INLINE_RULES__": rules_df}
    )
    result = apply_segmentation_by_rules(
        ecl_data=ecl_copy,
        simulation_df=simulation_df,
        target_segment_col=target_segment_col,
        driver_mapping=driver_mapping,
        rules_sheet="__INLINE_RULES__",
    )
    return result 