import pandas as pd
#dic_test = {"sheet1": pd.DataFrame(), "sheet2": pd.DataFrame()}

#print(", ".join(dic_test.keys()))


sheet_fields_test = ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME", "FORMAT", "MEANING"]
sheet_required_fields = ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME"]
missing_columns = set(sheet_required_fields) - set(sheet_fields_test)