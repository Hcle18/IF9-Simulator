# EAD per time steps based on multiple criteria:
 
# accounting type (On or Off Balance sheet)
# linear, constant, in-fine amortisation
# revolving or term loan
# frequency of time steps (based on time step template)

# Global import
from src.core.librairies import *

def get_amortization_type(df:pd.DataFrame):
    pass


def constant_amortization(df:pd.DataFrame, prov_basis_series, resid_mat_series, step_months:np.ndarray):
    '''
    EAD_i = Prov_basis - (Prov_basis/resid_mat) * (step_months[i-1])
    Floor at 0 if EAD_i < 0
    '''

    df[f"EAD_1"] = df[prov_basis_series]  # EAD_1 = Prov_basis

    for i in range(1, len(step_months), 1):
        m = step_months[i-1]
        df[f"EAD_{i+1}"] = df[prov_basis_series] - (df[prov_basis_series] / df[resid_mat_series]) * m
        df[f"EAD_{i+1}"] = df[f"EAD_{i+1}"].clip(lower=0)
    return df

def in_fine_amortization(df:pd.DataFrame):
    pass
