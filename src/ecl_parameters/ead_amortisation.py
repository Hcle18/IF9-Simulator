# EAD per time steps based on multiple criteria:
 
# accounting type (On or Off Balance sheet)
# linear, constant, in-fine amortisation
# revolving or term loan
# frequency of time steps (based on time step template)

# Global import
from src.core.librairies import *

def get_amortization_type(df:pd.DataFrame):
    pass


def linear_amortization(df:pd.DataFrame):
    max_residual_maturity = int(np.ceil(df["RESIDUAL_MATURITY_MONTHS"]))

def in_fine_amortization(df:pd.DataFrame):
    pass
