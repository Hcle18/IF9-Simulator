# EAD per time steps based on multiple criteria:
 
# accounting type (On or Off Balance sheet)
# linear, constant, in-fine amortisation
# revolving or term loan
# frequency of time steps (based on time step template)

# Global import
from src.core.librairies import *


def constant_amortization(df:pd.DataFrame, prov_basis_series, resid_mat_series, nb_steps_series, step_months:np.ndarray):
    '''
    EAD_i = Prov_basis - (Prov_basis/resid_mat) * (step_months[i-1])
    Floor at 0 if EAD_i < 0
    '''
    nb_steps_ope = df[nb_steps_series].values
    prov_basis = df[prov_basis_series].values
    maturity = df[resid_mat_series].values

    # Monthly amortization
    constant_amort = prov_basis / maturity

    result_df = pd.DataFrame(index=df.index)
    result_df[f"EAD_1"] = prov_basis

    for i in range(1, len(step_months)):
        m = step_months[i-1]
        mask = nb_steps_ope >= i+1

        ead = np.where(mask, prov_basis - constant_amort * m, 0)
        result_df[f"EAD_{i+1}"] = np.maximum(ead, 0)

    return result_df

def infine_ead(df:pd.DataFrame, provisioning_basis_col:str, nb_steps_col:str, step_months:np.ndarray):
    """
    Calculate EAD for in-fine amortization by time steps.
    Args:
        df: DataFrame with contract data
        provisioning_basis_col: column name for initial EAD
        nb_steps_col: column name for number of steps
        step_months: array/list of time step boundaries
    """
    nb_steps_ope = df[nb_steps_col]
    result_df = pd.DataFrame(index=df.index)

    for i in range(1, len(step_months) + 1):
        mask = nb_steps_ope >= i
        result_df[f"EAD_{i}"] = df[provisioning_basis_col].where(mask, 0)

    return result_df

def off_balance_ead(df:pd.DataFrame, provisioning_basis_col:str, nb_steps_col:str, step_months:np.ndarray):
    """
    Calculate EAD for off-balance sheet items by time steps.
    Args:
        df: DataFrame with contract data
        provisioning_basis_col: column name for initial EAD
        nb_steps_col: column name for number of steps
        step_months: array/list of time step boundaries
    """
    nb_steps_ope = df[nb_steps_col]
    result_df = pd.DataFrame(index=df.index)

    for i in range(1, len(step_months) + 1):
        mask = nb_steps_ope >= i
        result_df[f"EAD_{i}"] = (df[provisioning_basis_col] * df[f"CCF_{i}"]).where(mask, 0)

    return result_df


def linear_ead_amortization(df:pd.DataFrame, provisioning_basis_col:str, maturity_col:str, step_months:np.ndarray, rate_col:str):
    """
    Calculate EAD amortization by time steps with constant payment and decreasing capital using pandas only.
    If rate_col is missing or empty, set to 0 for calculation only (do not modify df[rate_col]).
    Updates df in-place with new columns EAD_1, EAD_2, ..., EAD_n
    """
    n_steps = len(step_months)
    ead_cols = [f"EAD_{i+1}" for i in range(n_steps)]

    result = pd.DataFrame(index=df.index)

    # Initial capital
    result[ead_cols[0]] = df[provisioning_basis_col]

    # Monthly rate, handle missing/empty rate_col (do not modify df[rate_col])
    rate_series = df[rate_col].fillna(0).replace('', 0).astype(float)
    monthly_rate = rate_series / 12
    # Total months
    total_months = df[maturity_col]

    # Annual payment (constant)
    annuity = np.where(
        rate_series == 0,
        df[provisioning_basis_col] / (total_months / 12),
        df[provisioning_basis_col] * rate_series / (1 - (1 + rate_series) ** (-total_months / 12))
    )
    # For each time step
    for i in range(1, n_steps):
        if i == 1:
            months = step_months[i-1]
        else:
            months = step_months[i-1] - step_months[i-2]

        last_ead_col = ead_cols[i-1]
        # Interest for the period
        interest = result[last_ead_col] * ((1 + monthly_rate) ** months - 1)
        # Constant payment (linear amortization)
        payment = months * annuity/12
        # Amortized capital for this period
        amortized_capital = payment - interest
        # Next EAD
        result[ead_cols[i]] = (result[last_ead_col] - amortized_capital).clip(lower=0)
    return result

def apply_ead_amortization(df, step_months, 
                           prov_basis_col, resid_mat_col, nb_time_steps_col, rate_col, business_percent_col,
                           amortization_map:Dict=None, default_amort_func = None) -> pd.DataFrame:
    if amortization_map is None:
        amortization_map = {
            "OFF_BALANCE": off_balance_ead,
            "ON_BALANCE_INFINE": infine_ead,
            "ON_BALANCE_LINEAR": constant_amortization
        }

    if default_amort_func is None:
        default_amort_func = infine_ead
    
    result_dfs = []

    for amortization_type, func in amortization_map.items():
        mask = df['AMORTIZATION_TYPE'] == amortization_type
        if mask.any():
            df_subset = df[mask]
            if func == constant_amortization:
                df_ead = func(df_subset, prov_basis_col, resid_mat_col, step_months)
            elif func == infine_ead:
                df_ead = func(df_subset, prov_basis_col, nb_time_steps_col, step_months)
            elif func == off_balance_ead:
                df_ead = func(df_subset, prov_basis_col, nb_time_steps_col, step_months)
            elif func == linear_ead_amortization:
                df_ead = func(df_subset, prov_basis_col, resid_mat_col, step_months, rate_col)
            result_dfs.append(df_ead)

    return pd.concat(result_dfs, axis=0).sort_index()