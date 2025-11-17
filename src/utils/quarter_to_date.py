from src.core.librairies import *

def convert_quarter_to_date(quarter_series: pd.Series):
    q_map = {
        'Q1': 1,
        'Q2': 4,
        'Q3': 7,
        'Q4': 10
    }
    q, year = quarter_series.split()
    year = int(year)
    month = q_map.get(q.upper())
    if month is None:
        raise ValueError(f"Invalid quarter format: {quarter_series}. Expected format 'Qn YYYY'.")
    return pd.Timestamp(year=year, month=month, day=1)
