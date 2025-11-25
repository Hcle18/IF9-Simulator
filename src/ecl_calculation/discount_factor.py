from src.core.librairies import *

logger = logging.getLogger(__name__)   

def discount_factor(df, as_of_date, exposure_end_date, annual_rate_col, step_months):
    as_of_date = pd.to_datetime(df[as_of_date], errors='coerce', dayfirst=True) + pd.offsets.MonthEnd(0)
    exposure_end_date = pd.to_datetime(df[exposure_end_date], errors='coerce', dayfirst=True)
    annual_rate = df[annual_rate_col].fillna(0).replace('', 0).astype(float)
    n_steps = len(step_months) 

    for i in range(1, n_steps + 1):
        if step_months[i - 1] <= 12:
            df.loc[:, f'DF_{i}'] = 1.0
        else:
            start_date = as_of_date + pd.DateOffset(months=step_months[i - 2])

            end_date = as_of_date + pd.DateOffset(months=step_months[i - 1]) - pd.DateOffset(days=1)
            end_date = np.minimum(exposure_end_date, end_date)

            duration_days = (start_date - end_date).dt.days + ((end_date - start_date).dt.days) / 2

            df.loc[:, f"DF_{i}"] = 1/(1 + annual_rate) ** (duration_days / 365)
    return df

def discount_factor_quarterly(df, annual_rate_col, step_months):
    annual_rate = df[annual_rate_col].fillna(0).replace('', 0).astype(float)
    n_steps = len(step_months) 

    for i in range(1, n_steps + 1):
        if step_months[i - 1] <= 3:
            df.loc[:, f'DF_{i}'] = 1.0
        else:
            n_quarters = (step_months[i - 2]) / 3
            df.loc[:, f"DF_{i}"] = 1/(1 + annual_rate/4) ** (n_quarters/4)
    return df

def apply_discount_factor(df, as_of_date_col, exposure_end_date_col, annual_rate_col, 
                          step_months, discount_map:Dict=None, default_discount_func=None) -> pd.DataFrame:
    # Default discount map if not specified
    if discount_map is None:
        discount_map = {
            'OFF_BALANCE': discount_factor,
            'ON_BALANCE_LINEAR': discount_factor_quarterly
        }
    
    # Default discount function if not specified
    if default_discount_func is None:
        default_discount_func = discount_factor

    result_dfs = []
    for amort_type, discount_func in discount_map.items():
        mask = df['AMORTIZATION_CATEGORY'] == amort_type
        if mask.any():
            df_subset = df.loc[mask]
            if discount_func == discount_factor_quarterly:
                df_discount = discount_func(df_subset, annual_rate_col, step_months)
            else:
                df_discount = discount_func(df_subset, as_of_date_col, exposure_end_date_col, annual_rate_col, step_months)
            result_dfs.append(df_discount)
    return pd.concat(result_dfs, axis=0).sort_index()