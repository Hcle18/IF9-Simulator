from src.core.librairies import *
from src.core import config as cst
logger = logging.getLogger(__name__)

import re
from typing import List, Dict, Any, Tuple

def get_template_data_keys(
    dict_config: Dict,
    dict_key: Tuple[str, str],
    template_data: Dict,
    split_columns: List[Dict[str, Any]] = None,
    concat_key: List[Dict[str, Any]] = None
):
    """
    Retrieves the template DataFrame and key columns for merging.

    Features:
        - Allows splitting of specified right_key columns using user-provided options.
          split_columns: list of dicts, each with pattern:
              {
                  "column": str,           # column to split
                  "delimiter": str,        # delimiter for splitting
                  "regex": {               # optional regex substitution
                      "pattern": str,
                      "replace": str
                  } or None
              }

        - Allows concatenation of key columns into one or more composite keys.
          concat_key: list of dicts, each with pattern:
              {
                  "name": str,             # name of the new key column
                  "columns": list,         # columns to concatenate
                  "sep": str,              # separator string (default "_")
                  "regex": {               # optional regex substitution
                      "pattern": str,
                      "replace": str
                  } or None
              }

    The order of keys in the final right_key matches the order in the original right_key, with concatenated keys replacing their specified columns.

    Returns:
        template_df: DataFrame with processed key columns
        left_key: list of left key columns
        right_key: list of right key columns (may be composite)
    """
    template_config = dict_config.get(dict_key)
    if template_config is None:
        raise KeyError(f"Configuration for {dict_key} not found in dict_config.")

    key, val = next(iter(template_config.items()))
    if key not in template_data:
        raise KeyError(f"Template '{key}' specified in configuration for {dict_key} not found in template data.")
    template_df = template_data[key]
    left_key, right_key = val[0], val[1]

    # Support split_columns as a list of dicts
    if split_columns is None:
        new_right_key = list(right_key)
    else:
        split_columns_dict = {d["column"]: d for d in split_columns}
        new_right_key = []
        for col in right_key:
            if col in split_columns_dict:
                opts = split_columns_dict[col]
                delimiter = opts.get("delimiter")
                regex_opts = opts.get("regex")
                if delimiter is None:
                    raise ValueError(f"Delimiter must be specified for splitting column '{col}'. Got: {opts}")
                n_parts = template_df[col].str.split(delimiter).map(len).max()
                split_col_names = [f"{col}_part{i+1}" for i in range(n_parts)]
                template_df[split_col_names] = template_df[col].str.split(delimiter, expand=True)
                if regex_opts:
                    pattern = regex_opts.get("pattern")
                    replace = regex_opts.get("replace")
                    for split_col in split_col_names:
                        template_df[split_col] = template_df[split_col].apply(lambda x: re.sub(pattern, replace, str(x)) if isinstance(x, str) else x)
                new_right_key.extend(split_col_names)
            else:
                new_right_key.append(col)

    # Support multiple concatenations
    concat_keys = concat_key if isinstance(concat_key, list) else ([concat_key] if concat_key else [])
    # Create all concatenated keys
    for concat in concat_keys:
        if concat:
            name = concat["name"]
            columns = concat["columns"]
            sep = concat.get("sep", "_")
            template_df[name] = template_df[columns].astype(str).agg(sep.join, axis=1)
            regex_opts = concat.get("regex")
            if regex_opts:
                pattern = regex_opts.get("pattern")
                replace = regex_opts.get("replace")
                template_df[name] = template_df[name].apply(lambda x: re.sub(pattern, replace, str(x)) if isinstance(x, str) else x)
    # Build right_key in order, replacing columns with their concat key
    if concat_keys:
        right_key = []
        skip_cols = set()
        for col in new_right_key:
            added = False
            for concat in concat_keys:
                if concat and col in concat["columns"] and concat["name"] not in right_key:
                    right_key.append(concat["name"])
                    skip_cols.update(concat["columns"])
                    added = True
                    break
            if not added and col not in skip_cols:
                right_key.append(col)
    else:
        right_key = new_right_key

    return template_df, left_key, right_key

def get_list_scenarios(dict_config:Dict, dict_key:Tuple[str, str], template_data:Dict):
    # Get template df
    sheet_name = list(dict_config.get(dict_key).keys())[0]
    if sheet_name not in template_data or sheet_name is None:
        return []
    template_df = template_data[sheet_name]

    # Check if 'SCENARIO' column exists
    if "SCENARIO" not in template_df.columns:
        return []
    
    # Exclude missing (NaN, empty, or blank) scenarios
    scenarios = template_df["SCENARIO"].dropna()
    scenarios = scenarios.astype(str).str.strip().str.upper()
    scenarios = scenarios[scenarios != ""]
    scenarios = sorted(scenarios.unique())
    return scenarios


def get_terms_from_template(
    simu_df: pd.DataFrame,
    dict_config: Dict,
    dict_key: Tuple[str, str],
    template_data: Dict,
    prefix="PD_",
    scenario: str="CENTRAL",
    asof_left: str = None,
    asof_right: str = None,
    groupby_col: str = None,
    fill_max: bool = False
):
    """
    Optionally supports asof merge (direction="forward") and filling unmatched rows with max(asof_right) for each group.
    """
    # Get template df and keys for merge
    template_df_cplt, left_key, right_key = get_template_data_keys(dict_config, dict_key, template_data)

    # Get template df for the specified scenario
    template_df = template_df_cplt[template_df_cplt["SCENARIO"].astype(str).str.strip().str.upper() == scenario]

    # Check if either DataFrame is None or empty
    if simu_df.empty:
        logger.error("Simulation or template DataFrame is empty.")
        raise ValueError("Simulation or template DataFrame is empty.")
    if template_df.empty or template_df is None:
        return simu_df

    # Check for missing keys in simu_df and template_df
    missing_keys_simu = [col for col in left_key if col not in simu_df.columns]
    missing_keys_template = [col for col in right_key if col not in template_df.columns]
    if missing_keys_simu:
        logger.error(f"Missing keys in simulation DataFrame: {missing_keys_simu}")
        raise ValueError(f"Missing keys in simulation DataFrame: {missing_keys_simu}")
    if missing_keys_template:
        logger.error(f"Missing keys in template DataFrame: {missing_keys_template}")
        raise ValueError(f"Missing keys in template DataFrame: {missing_keys_template}")

    # Clean and normalize keys
    for col in left_key:
        if simu_df[col].dtype == 'object':
            simu_df[col] = simu_df[col].where(simu_df[col].isna(), simu_df[col].astype(str).str.strip().str.upper())
    for col in right_key:
        if template_df[col].dtype == 'object':
            template_df[col] = template_df[col].where(template_df[col].isna(), template_df[col].astype(str).str.strip().str.upper())
            
    # Remove rows on template_df with missing keys
    template_df = template_df.dropna(subset=right_key)
    # Remove duplicates on template df, based on right key
    template_df = template_df.drop_duplicates(subset=right_key)
    get_columns = [col for col in template_df.columns if col.strip().startswith(prefix)]
    print(get_columns)

    prefix = "simu_"
    for col in get_columns:
        if col in simu_df.columns:
            simu_df.rename(columns={col: f"{prefix}{col}"}, inplace=True)

    # If asof merge is requested
    if asof_left and asof_right and groupby_col:
        simu_df_sorted = simu_df.sort_values([groupby_col, asof_left])
        template_df_sorted = template_df.sort_values([groupby_col, asof_right])
        result_list = []
        for group_val in simu_df_sorted[groupby_col].unique():
            simu_sub = simu_df_sorted[simu_df_sorted[groupby_col] == group_val]
            template_sub = template_df_sorted[template_df_sorted[groupby_col] == group_val]
            merged = pd.merge_asof(
                simu_sub.sort_values(asof_left),
                template_sub.sort_values(asof_right),
                left_on=asof_left,
                right_on=asof_right,
                direction="forward"
            )
            # Optionally fill unmatched rows with max(asof_right)
            if fill_max:
                mask = merged[asof_right].isna()
                max_val = template_sub[asof_right].max()
                for col in template_sub.columns:
                    if col == groupby_col:
                        merged.loc[mask, col] = group_val
                    elif col == asof_right:
                        merged.loc[mask, col] = max_val
                    else:
                        value = template_sub[template_sub[asof_right] == max_val][col].values
                        if len(value) > 0:
                            merged.loc[mask, col] = value[0]
            result_list.append(merged)
        merged_df = pd.concat(result_list, ignore_index=True)
        # Retain only from template_df the columns with prefix
        merged_df = merged_df[simu_df.columns.tolist() + get_columns]
        return merged_df

    # Default: Left join
    merged_df = simu_df.merge(template_df, how="left", left_on=left_key, right_on=right_key)
    print(merged_df.head())
    # Retain only from template_df the columns with prefix
    simu_df = merged_df[simu_df.columns.tolist() + get_columns]
    return simu_df

def extend_terms_columns(df, nb_steps_col="NB_TIME_STEPS", pd_prefix="PD_"):
    """
    Extends PD columns in the DataFrame if contracts require more steps than the template provides.
    Fills new PD columns with the value of the last available PD for each row.
    """
    # Find the maximum number of steps required by any contract
    max_steps = df[nb_steps_col].max()
    # Find existing PD columns
    existing_pd_cols = [col for col in df.columns if re.match(rf"^{pd_prefix}\d+$", col)]
    max_existing_steps = max([int(col.split('_')[-1]) for col in existing_pd_cols]) if existing_pd_cols else 0
    existing_pd_cols_sorted = sorted(existing_pd_cols, key=lambda x: int(x.split('_')[-1]))
    # Add missing PD columns and fill with last PD value per row
    for i in range(1, max_steps + 1):
        col_name = f"{pd_prefix}{i}"
        if col_name not in existing_pd_cols:
            # Find last available PD column for each row
            last_pd_col = existing_pd_cols_sorted[-1] if existing_pd_cols_sorted else None
            if last_pd_col:
                df[col_name] = df[last_pd_col]
            else:
                df[col_name] = np.nan
    # Reorder columns so PD columns are in order
    pd_cols_sorted = [f"{pd_prefix}{i}" for i in range(1, max_steps + 1)]
    other_cols = [col for col in df.columns if col not in pd_cols_sorted]
    df = df[other_cols + pd_cols_sorted]
    return df

def fill_terms_for_lgd_ccf(df, step_months, lgd_col='LGD_RATE_WITHOUT_TIME', ccf_col='CCF_WITHOUT_TIME', fallback_lgd='LGD_value', fallback_ccf='CCF'):
    """
    Fill LGD and CCF columns for all time steps according to rules:
    1. If LGD_RATE_WITHOUT_TIME or CCF_WITHOUT_TIME is present, replicate for all steps.
    2. If missing, use fallback LGD_value and CCF, replicate for all steps.
    Only fill LGD_{i} or CCF_{i} if the column is missing or empty (all NA or blank) in df.
    If LGD_{i} or CCF_{i} does not exist, create it and fill with lgd_source or ccf_source.
    """
    n_steps = len(step_months)
    # LGD
    lgd_clean = pd.to_numeric(df[lgd_col], errors='coerce') if lgd_col in df.columns else pd.Series([np.nan]*len(df))
    lgd_source = lgd_clean.combine_first(df[fallback_lgd]) if fallback_lgd in df.columns else lgd_clean
    for i in range(1, n_steps + 1):
        col_name = f'LGD_{i}'
        if col_name not in df.columns:
            df[col_name] = lgd_source
        else:
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(lgd_source)
    # CCF
    ccf_clean = pd.to_numeric(df[ccf_col], errors='coerce') if ccf_col in df.columns else pd.Series([np.nan]*len(df))
    ccf_source = ccf_clean.combine_first(df[fallback_ccf]) if fallback_ccf in df.columns else ccf_clean
    for i in range(1, n_steps + 1):
        col_name = f'CCF_{i}'
        if col_name not in df.columns:
            df[col_name] = ccf_source
        else:
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(ccf_source)
    return df

def map_lgd_by_maturity_vectorized(simu_df, lgd_template, product_col="PRODUCT", maturity_col="RESIDUAL_MATURITY_MONTHS", template_maturity_col="MATURITY_MAX"):
    """
    Vectorized mapping of RESIDUAL_MATURITY_MONTHS to closest (not exceeding) MATURITY_MAX by PRODUCT.
    Returns merged DataFrame.
    """
    import numpy as np
    simu_df = simu_df.copy()
    # Prepare output array
    maturity_max_lgd = np.full(len(simu_df), np.nan)
    # Group template by product for fast lookup
    template_groups = {prod: group.sort_values(template_maturity_col)[template_maturity_col].values
                       for prod, group in lgd_template.groupby(product_col)}
    for prod in simu_df[product_col].unique():
        mask = simu_df[product_col] == prod
        maturities = simu_df.loc[mask, maturity_col].values
        template_maturities = template_groups.get(prod, np.array([]))
        if len(template_maturities) == 0:
            continue
        # Use searchsorted to find insertion points
        idx = np.searchsorted(template_maturities, maturities, side='right') - 1
        # Clip indices to valid range
        idx = np.clip(idx, 0, len(template_maturities) - 1)
        # If maturity is less than all template values, assign min
        below_min = maturities < template_maturities[0]
        result = template_maturities[idx]
        result[below_min] = template_maturities[0]
        maturity_max_lgd[mask] = result
    simu_df["maturity_max_lgd"] = maturity_max_lgd
    # Standard left join
    lgd_template_sorted = lgd_template.sort_values([product_col, template_maturity_col])
    merged_df = simu_df.merge(lgd_template_sorted, how="left", left_on=[product_col, "maturity_max_lgd"], right_on=[product_col, template_maturity_col])
    return merged_df

if __name__ == "__main__":
    template_data = {
        "F6-PD S1S2 Non Retail": pd.DataFrame(columns=["IFRS9_PD_MODEL_AFTER_CRM", "RATING_CALCULATION", "IFRS9_PD_MODEL_CODE", "RATING"])
    }

    template_df, left_key, right_key = get_template_data_keys(cst.PD_SHEET_MAPPING_CONFIG, (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING), template_data)
    print(template_df.head())
    print(left_key)
    print(right_key)