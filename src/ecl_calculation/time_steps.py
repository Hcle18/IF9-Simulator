# Global import
from src.core.librairies import *

# Local import
from src.data import data_loader as dl
from src.templates import template_loader as tpl

logger = logging.getLogger(__name__)

def maturity(date_maturity, as_of_date):
    '''
    Compute the residual maturity in months between as_of_date and date_maturity.
    Both dates can be strings or pandas.Timestamp.
    Returns a float (fractional months allowed).
    '''

    # Convert to pandas Timestamp if not already
    date_maturity = pd.to_datetime(date_maturity, errors='coerce', dayfirst=True)
    as_of_date = pd.to_datetime(as_of_date, errors='coerce', dayfirst=True)

    # Calculate the difference in months (fractional)
    delta = (date_maturity.dt.year - as_of_date.dt.year) * 12 + (date_maturity.dt.month - as_of_date.dt.month)

    # Add fractional part based on days
    day_fraction = (date_maturity.dt.day - as_of_date.dt.day) * 12/365
    residual_months = delta + day_fraction

    # If maturity date is before as_of_date, return 0 
    return residual_months.clip(lower=0)


def nb_time_steps_(residual_maturity, template_steps: pd.DataFrame):
    '''
    Determine the number of time steps required for a given residual maturity based on a template.

    Args:
    - residual_maturity (float): The residual maturity in months.
    - template_steps (pd.DataFrame): A DataFrame containing the template steps with their durations.
    Returns:
    - int: The number of time steps required.

    '''

    # Vérifications d'entrée
    if residual_maturity <= 0:
        return 0, [] # Exposition expirée ou invalide
    
    if template_steps.empty or "NB_MONTHS" not in template_steps.columns:
        logger.error("Invalid template for time steps or NB_MONTHS column is missing")
        raise ValueError("Invalid template for time steps or NB_MONTHS column is missing")
    
    # Extraction des bornes du template, triées
    bounds = template_steps["NB_MONTHS"].sort_values().to_numpy()

    # Cas 1: Maturité couverte par le template existant
    if residual_maturity <= bounds[-1]:
        # Trouve le premier step qui couvre la maturité
        step_index = np.searchsorted(bounds, residual_maturity, side="left")
        nb_step = step_index + 1 # On commence le step à 1
        # Ajouter la liste des mois correspondant
        nb_months_list = bounds[:nb_step].tolist()
        return nb_step, nb_months_list 
    
    # Cas 2: Maturité dépasse le max bound du template => Prolongation nécessaire
    max_template = bounds[-1]
    second_last = bounds[-2] if len(bounds) > 1 else 0
    nb_diff = max_template - second_last # Nombre de mois d'écart entre les deux derniers steps

    # Calcul du nombre de steps supplémentaires i à créer pour couvrir la maturité résiduelle
    # Formule: max_template + nb_diff * i >= residual_maturity
    # Donc: i >= (residual_maturity - max_template) / nb_diff
    i = math.ceil((residual_maturity-max_template) / nb_diff)

    # Le nombre de step
    nb_step = len(bounds) + i

    # La liste des mois correspondant
    nb_months_list = bounds.tolist()
    for j in range(1, i+1):
        nb_months_list.append(max_template + nb_diff * j)

    # print(f"Valeur du step créé est {max_template + nb_diff * i} qui couvre la maturité {residual_maturity}")
    
    return nb_step, nb_months_list

def nb_time_steps(residual_maturities, template_steps: pd.DataFrame):
    """
    Vectorized computation of nb_time_steps for an array-like of residual maturities.
    Returns two arrays: nb_steps and nb_months_lists.
    """
    bounds = np.sort(template_steps["NB_MONTHS"].to_numpy())
    max_template = bounds[-1]
    second_last = bounds[-2] if len(bounds) > 1 else 0
    nb_diff = max_template - second_last if len(bounds) > 1 else max_template

    # residual_maturities = np.asarray(residual_maturities)

    # Step 1: In bounds and valid
    valid = residual_maturities > 0
    in_bounds = (residual_maturities <= max_template) & valid
    step_indices = np.searchsorted(bounds, residual_maturities, side="left")
    nb_steps = np.where(in_bounds, step_indices + 1, 0)

    # Step 2: Out of bounds
    out_bounds = (residual_maturities > max_template) & valid
    i_extra = np.ceil((residual_maturities - max_template) / nb_diff).astype(int)
    nb_steps[out_bounds] = len(bounds) + i_extra[out_bounds]

    # Step 3: Build nb_months_list for each row
    # nb_months_lists = []
    # for mat in residual_maturities:
    #     if mat <= 0:
    #         nb_months_lists.append([])
    #     elif mat <= max_template:
    #         idx = np.searchsorted(bounds, mat, side="left") + 1
    #         nb_months_lists.append(bounds[:idx].tolist())
    #     else:
    #         i = int(np.ceil((mat - max_template) / nb_diff))
    #         months = bounds.tolist()
    #         for j in range(1, i + 1):
    #             months.append(int(max_template + nb_diff * j))
    #         nb_months_lists.append(months)

    return nb_steps


if __name__ == "__main__":

    # Template d'exemple
    template_data = {
        "STEP": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "NB_MONTHS": [3, 6, 9, 12, 15, 18, 30, 42, 54]  # nb_diff entre 4 et 5 = 3
    }
    template_df = pd.DataFrame(template_data)

    # Test residual maturity in bounds
    # residual_maturity = 8.9
    # step_max = nb_time_steps(residual_maturity, template_df)
    # print(f"In bound. Le step max est: {step_max}")

    # # Test residual maturity out bounds
    # residual_maturity = 22.5
    # step_max = nb_time_steps(residual_maturity, template_df)
    # print(f"Out bound. Le step max est: {step_max}")


    # Test avec un portefeuille complet
    print("Test avec un portefeuille complet")
    portfolio_data = {
        'CONTRACT_ID': ['C1', 'C2', 'C3', 'C4', 'C5'],
        'RESIDUAL_MATURITY_MONTHS': [15, 41.8, 10.4, 0.5, 65]
    }
    portfolio_df = pd.DataFrame(portfolio_data)

    time_step_results = portfolio_df["RESIDUAL_MATURITY_MONTHS"].apply(lambda mat: nb_time_steps(mat, template_df))
    
    print(time_step_results)

    portfolio_df["NB_TIME_STEP"] = time_step_results.apply(lambda x: x[0])

    df_expanded = portfolio_df.loc[np.repeat(portfolio_df.index, portfolio_df['NB_TIME_STEP'])].reset_index(drop=True)
    print(df_expanded.head(10))

    portfolio_df["NB_MONTHS_LIST"] = time_step_results.apply(lambda x: x[1])
    print(portfolio_df["NB_MONTHS_LIST"])

    all_steps = []
    for nb_months_list in portfolio_df["NB_MONTHS_LIST"]:
        all_steps.extend(nb_months_list)


    #print(all_steps)

    df_expanded["TIME_STEP"] = all_steps
    print(df_expanded.head(10))



    




