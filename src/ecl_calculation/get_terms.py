from src.core.librairies import *
from src.core import config as cst
from src.utils.split_concat_keys import split_key_columns, concat_key_columns

logger = logging.getLogger(__name__)

def get_template_data_keys(
        dict_config: Dict,
        dict_key: Tuple[str, str],
        template_data: Dict,
        split_right_keys: List[Dict[str, Any]] = None,
        concat_right_keys: List[Dict[str, Any]] = None
):
    template_config = dict_config.get(dict_key, None)

    if template_config is None:
        logger.warning(f"No template configuration found for key: {dict_key}")
        raise KeyError(f"No template configuration found for key: {dict_key}")
    
    template_name, key_mapping = next(iter(template_config.items()))

    if template_name not in template_data:
        logger.warning(f"Template '{template_name}' not found in template data.")
        raise KeyError(f"Template '{template_name}' not found in template data.")
    
    template_df = template_data.get(template_name)

    if len(key_mapping) < 2:
        raise ValueError(f"Key mapping for template '{template_name}' must contain a nested list.")
    
    left_key, right_key = key_mapping[0], key_mapping[1]

    # Apply options for splitting right keys if provided
    if split_right_keys:
        template_df, right_key = split_key_columns(template_df, right_key, split_right_keys)

    # Apply options for concatenating right keys if provided
    if concat_right_keys:
        template_df, right_key = concat_key_columns(template_df, right_key, concat_right_keys)

    # Final validation
    if len(right_key) != len(left_key):
        logger.error("Length mismatch between left keys and right keys.")
        raise ValueError("Length mismatch between left keys and right keys.")
    
    return template_df, left_key, right_key

def get_list_scenarios(
        dict_config: Dict,
        dict_key: Tuple[str, str],
        template_data: Dict
) -> List[str]:
    """
    Get the list of scenarios from the template data based on the provided configuration and key.

    Args:
        dict_config: Configuration dictionary mapping operation types and statuses to template details.
        dict_key: Tuple containing operation type and status.
        template_data: Dictionary containing template DataFrames.

    Returns:
        List[str]: List of scenarios extracted from the template data.
    """
    sheet_name = list(dict_config.get(dict_key).keys())[0]
    if sheet_name is None or sheet_name not in template_data:
        logger.warning(f"Sheet name '{sheet_name}' not found in template data for key: {dict_key}")
        return []
    
    template_df = template_data[sheet_name]

    if template_df is None or "SCENARIO" not in template_df.columns:
        logger.warning(f"'SCENARIO' column not found in template data for sheet '{sheet_name}'")
        return []
    
    scenarios = template_df["SCENARIO"].dropna()
    scenarios = scenarios.astype(str).str.strip().str.upper()
    scenarios = scenarios[scenarios != ""]

    scenarios = sorted(scenarios.unique())

    return scenarios

def get_terms_from_template(simu_df: pd.DataFrame, dict_config:Dict, dict_key:Tuple[str, str],
                            template_data:Dict[str, pd.DataFrame], prefix:str = "PD_", 
                            scenario:str="CENTRAL", defaulted_scen: str = "CENTRAL",
                            split_template_keys: Optional[List[Dict[str, Any]]] = None,
                            concat_template_keys: Optional[List[Dict[str, Any]]] = None,
                            additional_fields: List[str] = [],
                            simu_col_replace_value : List[Dict[str, Any]] = None) -> pd.DataFrame:
    '''
    Get terms from template data and merge with simulation data.
    
    Args:
        simu_df: Simulation data DataFrame
        dict_config: Configuration dictionary mapping operation types and statuses to template details
        dict_key: Tuple containing operation type and status
        template_data: Dictionary containing template DataFrames
        prefix: Prefix for the terms (e.g., "PD_", "LGD_", "CCF_")
        scenario: Scenario name to filter the terms

    Returns:
        pd.DataFrame: Merged DataFrame with terms from the template
    '''
    template_df_cplt, left_key, right_key = get_template_data_keys(
        dict_config,
        dict_key,
        template_data,
        split_template_keys,
        concat_template_keys
    )

    if simu_df is None or simu_df.empty:
        logger.error("Simulation data not found or empty.")
        raise ValueError("Simulation data not found or empty.")
    
    additional_fields = [field for field in additional_fields if field in simu_df.columns]
    
    # Check for missing keys
    missing_left_keys = [col for col in left_key if col not in simu_df.columns]
    missing_right_keys = [col for col in right_key if col not in template_df_cplt.columns]

    if missing_left_keys or missing_right_keys:
        logger.info(f"Missing keys in simulation or template data. Missing left keys: {missing_left_keys}, "
                    f"Missing right keys: {missing_right_keys} ")
        return simu_df.loc[:, ["NB_TIME_STEPS", "RESIDUAL_MATURITY_MONTHS", *additional_fields]]
    
    if template_df_cplt is None or template_df_cplt.empty:
        logger.info(f"Template data for key {dict_key} is empty after applying key mappings.")
        return simu_df.loc[:, ["NB_TIME_STEPS", "RESIDUAL_MATURITY_MONTHS", *additional_fields]]
    
    # Select relevant columns
    simu_df = simu_df.loc[:, left_key + ["NB_TIME_STEPS", "RESIDUAL_MATURITY_MONTHS", *additional_fields]]

    # Optional: find and replace some patterns on simu df
    if simu_col_replace_value:
        columns_dict = {d["column"]: d for d in simu_col_replace_value}
        for col in columns_dict:
            if col in simu_df.columns:
                val = columns_dict[col]
                list_regex = val.get("regex")
                if list_regex:
                    for regex in list_regex:
                        pattern = regex.get("pattern")
                        replace = regex.get("replace")
                        simu_df[col] = simu_df[col].apply(lambda x: re.sub(pattern, replace, str(x)) 
                                                          if isinstance(x, str) else x)

    # Filter template data for the specified scenario
    if "SCENARIO" in template_df_cplt.columns:
        template_df = template_df_cplt[template_df_cplt["SCENARIO"].astype(str).str.strip().str.upper() == scenario.strip().upper()]
        if template_df.empty:
            defaulted_scen_mask = template_df_cplt["SCENARIO"].astype(str).str.strip().str.upper() == defaulted_scen.strip().upper()
            if defaulted_scen_mask.any():
                template_df = template_df_cplt[defaulted_scen_mask]
                logger.info(f"Scenario '{scenario}' not found. Defaulting to '{defaulted_scen}' for key: {dict_key}")
            else:
                template_df = template_df_cplt.drop_duplicates(subset=right_key)
    else:
        template_df = template_df_cplt

    # Clean and normalize keys
    for key in left_key:
        if simu_df[key].dtype == object:
            simu_df.loc[:, key] = simu_df[key].where(simu_df[key].isna(), 
                                                     simu_df[key].astype(str).str.strip().str.upper())
    for key in right_key:
        if template_df[key].dtype == object:
            template_df.loc[:, key] = template_df[key].where(template_df[key].isna(), 
                                                             template_df[key].astype(str).str.strip().str.upper())
            
    # Remove rows on template with missing keys
    template_df = template_df.dropna(subset=right_key, how="all")

    # Remove duplicates on template based on right keys
    template_df = template_df.drop_duplicates(subset=right_key)
    get_columns = [col for col in template_df.columns if col.strip().startswith(prefix)]

    # Rename column on simu_df to avoid conflicts with get_columns
    #simu_df = simu_df.rename(columns={col: f"SIMU_{col}" for col in get_columns if col in simu_df.columns})

    # Merge simulation data with template terms
    merged_df = simu_df.merge(template_df, how='left', left_on=left_key, right_on=right_key, suffixes=('_SIMU', ''))
    merged_df.index = simu_df.index  # Preserve original index

    for col in get_columns:
        if col in merged_df.columns:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

    simu_df = merged_df[simu_df.columns.tolist() + get_columns]

    return simu_df

def extend_terms_columns(df, nb_steps_col="NB_TIME_STEPS", prefix="PD_"):
    """
    Extends PD columns in the DataFrame if contracts require more steps than the template provides.
    Fills new PD columns with the value of the last available PD for each row.
    """
    # Find the maximum number of steps required by any contract
    max_steps = df[nb_steps_col].max()

    # Find existing param columns: start with prefix and end with a number
    existing_param_cols = [col for col in df.columns if re.match(rf"^{prefix}\d+$", col)]
    max_existing_steps = max([int(col.split('_')[-1]) for col in existing_param_cols]) if existing_param_cols else 0
    existing_param_cols_sorted = sorted(existing_param_cols, key=lambda x: int(x.split('_')[-1]))
    
    # Add missing param columns and fill with last param value per row
    if max_steps > max_existing_steps:
        last_col = existing_param_cols_sorted[-1] if existing_param_cols_sorted else None
        if last_col:
            for i in range(max_existing_steps + 1, max_steps + 1):
                new_col = f"{prefix}{i}"
                df[new_col] = df[last_col] if last_col else np.nan
    return df

def pd_interpolation(df, step_months, nb_steps_col="NB_TIME_STEPS",
                     maturity_col="RESIDUAL_MATURITY_MONTHS",
                     method="linear", pd_prefix="PD_"):
    """
    Vectorized PD interpolation for the last time step using a common step_months array.
    Handles nb_steps == 1 case specifically.
    """
    # Gérer les valeurs non-finies avant conversion en int
    nb_steps_raw = pd.to_numeric(df[nb_steps_col], errors='coerce').fillna(0)
    nb_steps = nb_steps_raw.astype(int).to_numpy()
    residual_maturity = df[maturity_col].to_numpy()
    as_of_date = pd.to_datetime(df["AS_OF_DATE"], errors="coerce", dayfirst=True)
    step_months_arr = np.array(step_months)
    month_offset_last = step_months_arr[nb_steps - 1]

    # Add months using numpy (month precision)
    as_of_date_month = as_of_date.values.astype('datetime64[M]')
    start_date_last_step = as_of_date_month + month_offset_last.astype('timedelta64[M]')

    # Adjust to last day of month
    start_date_last_step = pd.to_datetime(start_date_last_step) + pd.offsets.MonthEnd(0)

    # If you need end_date_last_step, use exposure_end_date or similar logic
    exposure_end_date = pd.to_datetime(df["EXPOSURE_END_DATE"], errors="coerce", dayfirst=True)
    end_date_last_step = np.minimum(start_date_last_step.values, exposure_end_date.values)

    # Duration in days
    duration_days = (end_date_last_step - start_date_last_step.values).astype("timedelta64[D]").astype(int)
    
    # ...existing code for PD interpolation...
    full_duration = np.where(nb_steps == 1, step_months[0], step_months[nb_steps - 1] - step_months[nb_steps - 2])
    real_duration = np.where(nb_steps == 1, residual_maturity, residual_maturity - step_months[nb_steps - 2])
    weight = real_duration / full_duration
    pd_cols = [f"{pd_prefix}{i+1}" for i in range(len(step_months))]
    PD_matrix = df[pd_cols].to_numpy()
    PD_last = PD_matrix[np.arange(len(df)), nb_steps - 1]
    if method == "linear":
        PD_last_interp = PD_last * weight
    elif method == "survival":
        PD_cum_prev = PD_matrix[np.arange(len(df)), :nb_steps - 1].sum(axis=1)
        PD_cum_last = PD_matrix[np.arange(len(df)), :nb_steps].sum(axis=1)
        PD_last_interp = 1 - (1 - PD_cum_prev) ** (1 - weight) * (1 - PD_cum_last) ** weight
    else:
        raise ValueError("Unknown interpolation method")
    for idx, n in enumerate(nb_steps):
        df.at[df.index[idx], f"{pd_prefix}{n}"] = PD_last_interp[idx]
    return df

def fill_terms_param(df, step_months, template_used_col, fallback_col, prefix = "LGD_"):
    n_steps = len(step_months)
    param_clean = pd.to_numeric(df[template_used_col], errors='coerce') \
            if template_used_col in df.columns else pd.Series([np.nan]*len(df))
    fallback_clean = pd.to_numeric(df[fallback_col], errors='coerce') \
            if fallback_col in df.columns else pd.Series([np.nan]*len(df))

    param_source = param_clean.combine_first(fallback_clean)

    for i in range(1, n_steps + 1):
        col_name = f"{prefix}{i}"
        if col_name not in df.columns:
            df[col_name] = param_source
        else:
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(param_source)
    return df

def get_max_maturity_lgd(simu_df, lgd_template, product_col="PRODUCT", maturity_col="RESIDUAL_MATURITY_MONTHS", template_maturity_col="MATURITY_MAX"):
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
    return simu_df