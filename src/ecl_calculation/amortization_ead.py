# EAD per time steps based on multiple criteria:
 
# accounting type (On or Off Balance sheet)
# linear, constant, in-fine amortisation
# revolving or term loan
# frequency of time steps (based on time step template)

# Global import
from src.core.librairies import *


def constant_amortization(df:pd.DataFrame, prov_basis_series, resid_mat_series, step_months:np.ndarray):
    '''
    EAD_i = Prov_basis - (Prov_basis/resid_mat) * (step_months[i-1])
    Floor at 0 if EAD_i < 0
    '''

    df[f"EAD_1"] = df[prov_basis_series]  # EAD_1 = Prov_basis

    for i in range(1, len(step_months), 1):
        m = step_months[i-1]
        df[f"EAD_{i+1}"] = (
            df[prov_basis_series]
            - (df[prov_basis_series] / df[resid_mat_series]) * m
        )
        df[f"EAD_{i+1}"] = df[f"EAD_{i+1}"].clip(lower=0)
    return df

def infine_ead(df:pd.DataFrame, provisioning_basis_col:str, nb_steps_col:str, step_months:np.ndarray):
    """
    Calculate EAD for in-fine amortization by time steps.
    Args:
        df: DataFrame with contract data
        provisioning_basis_col: column name for initial EAD
        nb_steps_col: column name for number of steps
        step_months: array/list of time step boundaries
    """
    nb_steps = df[nb_steps_col]

    for i in range(1, len(step_months) + 1):
        mask = nb_steps >= i
        df.loc[mask, f"EAD_{i}"] = df.loc[mask, provisioning_basis_col]
        df.loc[~mask, f"EAD_{i}"] = 0
        
    return df

def off_balance_ead(df:pd.DataFrame, provisioning_basis_col:str, nb_steps_col:str, step_months:np.ndarray):
    """
    Calculate EAD for off-balance sheet items by time steps.
    Args:
        df: DataFrame with contract data
        provisioning_basis_col: column name for initial EAD
        nb_steps_col: column name for number of steps
        step_months: array/list of time step boundaries
    """
    nb_steps = df[nb_steps_col]

    for i in range(1, len(step_months) + 1):
        mask = nb_steps >= i
        df.loc[mask, f"EAD_{i}"] = df.loc[mask, provisioning_basis_col] * df.loc[mask, f"CCF_{i}"]
        df.loc[~mask, f"EAD_{i}"] = 0
        
    return df

def linear_ead_amortization(df, provisioning_basis_col, maturity_col, step_months, rate_col):
    """
    Calculate EAD amortization by time steps with constant payment and decreasing capital using pandas only.
    If rate_col is missing or empty, set to 0 for calculation only (do not modify df[rate_col]).
    Updates df in-place with new columns EAD_1, EAD_2, ..., EAD_n
    """
    n_steps = len(step_months)
    ead_cols = [f"EAD_{i+1}" for i in range(n_steps)]
    # Initial capital
    df[ead_cols[0]] = df[provisioning_basis_col]
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
        interest = df[last_ead_col] * ((1 + monthly_rate) ** months - 1)
        # Constant payment (linear amortization)
        payment = months * annuity/12
        # Amortized capital for this period
        amortized_capital = payment - interest
        # Next EAD
        df[ead_cols[i]] = (df[last_ead_col] - amortized_capital).clip(lower=0)
    return df

def apply_ead_amortization(df, step_months, prov_basis_col, resid_mat_col, nb_time_steps_col, rate_col, amortization_map:Dict=None):
    if amortization_map is None:
        amortization_map = {
            "OFF_BALANCE": off_balance_ead,
            "ON_BALANCE_INFINE": infine_ead,
            "ON_BALANCE_LINEAR": constant_amortization
        }
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