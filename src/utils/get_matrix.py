from src.core.librairies import *

def get_matrix_prefix(df, prefix, round=False, round_nb:int=7):
    """
    Extracts columns with a given prefix and returns them as a NumPy matrix.
    Optionally rounds the values to a specified number of decimal places.
    """
    cols_sorted = []
    cols = [col for col in df.columns if re.match(rf"^{prefix}\d+$", col)]
    cols_sorted = sorted(cols, key=lambda x: int(x.split('_')[-1]))
    cols_sorted_val = df[cols_sorted].values
    if round:
        cols_sorted_val = np.round(cols_sorted_val, round_nb)
    return cols_sorted_val