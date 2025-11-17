from src.core.librairies import *

from src.core import config as cst

logger = logging.getLogger(__name__)

def aggregate_results_sql(df:pd.DataFrame,
                          group_by_col: List[str],
                          group_by_label: Optional[List[str]]=None,
                          values_col: List[str]=[],
                          values_col_label: Optional[List[str]]=None,
                          agg_func: str="SUM") -> pd.DataFrame: 
    # Connect to duckdb
    con = duckdb.connect()
    # Register DataFrame as a table
    con.register('df', df)

    group_labels = group_by_label if group_by_label else group_by_col
    value_labels = values_col_label if values_col_label else values_col

    # Select clause
    select_parts = []
    for col, label in zip(group_by_col, group_labels):
        select_parts.append(f"CASE WHEN GROUPING({col})=1 THEN 'Total' ELSE {col} END AS \"{label}\"")
    for col, label in zip(values_col, value_labels):
        select_parts.append(f"{agg_func}({col}) AS \"{label}\"")
    
    select_sql = ", ".join(select_parts)

    # Group by clause
    grouping_sets = [f"({', '.join(group_by_col)})"] if group_by_col else []

    if len(group_by_col) > 1:
        for i in range(len(group_by_col)):
            subset = group_by_col[:i] + group_by_col[i+1:]
            if subset:
                grouping_sets.append(f"({', '.join(subset)})")
    
    grouping_sets.append("()")  # Grand total

    grouping_sets_sql = ",\n    ".join(grouping_sets)

    # Final SQL query
    query = f"""
    SELECT
        {select_sql}
    FROM df
    GROUP BY GROUPING SETS
    {grouping_sets_sql}
    ORDER BY
        {', '.join(group_by_col)}
    """
    # Execute the query and fetch the results
    result = con.execute(query).fetchdf()
    con.close()
    return result

def create_excel_report(contexts:str, output_path: str, sheet_name="ECL Synthesis"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))
    header_fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    start_row = 1

    for idx, (context_name, df) in enumerate(contexts.items(), start=1):
        start_col = (idx - 1) * (df.shape[1] + 3) + 1  # 3 columns gap between tables

        ws.merge_cells(start_row=start_row, start_column=start_col, 
                       end_row=start_row, end_column=start_col + df.shape[1] - 1)
        title_cell = ws.cell(row=start_row, column=start_col)
        title_cell.value = context_name
        title_cell.font = Font(bold=True, size=14)


    wb.save(output_path)