"""
Stage calculation module for IFRS9 ECL calculation.
Contains functions for collecting PD at origination date from historical templates.
"""

from src.core.librairies import *
from src.utils import convert_quarter_to_date

logger = logging.getLogger(__name__)

def stage_get_pd_name(mapping_sicr_df: pd.DataFrame,
                      pd_model_col,
                      template_pd_code_reporting,
                      template_pd_name_reporting,
                      template_pd_name_origination,
                      fallback_mapping: Dict=None):
    try:
        if fallback_mapping is None:
            fallback_mapping = {}
        
        # Ensure pd_model_col is a pandas Series
        if not isinstance(mapping_sicr_df[pd_model_col], pd.Series):
            raise ValueError(f"The column {pd_model_col} must be a pandas Series.")
        
        if mapping_sicr_df is None or mapping_sicr_df.empty:
            logger.warning("Mapping SICR DataFrame is empty or None. Using fallback mapping.")
            return pd_model_col.map(fallback_mapping), pd_model_col.map(fallback_mapping)
        
        # Ensure input strings are stripped of whitespace
        template_pd_code_reporting = str(template_pd_code_reporting).strip()
        template_pd_name_reporting = str(template_pd_name_reporting).strip()
        template_pd_name_origination = str(template_pd_name_origination).strip()

        # Check if the required columns exist in the DataFrame
        required_columns = [template_pd_code_reporting, template_pd_name_reporting, template_pd_name_origination]
        missing_cols = [col for col in required_columns if col not in mapping_sicr_df.columns]
        if missing_cols:
            # Use fallback mapping if columns are missing
            logger.warning(f"Missing columns in mapping_sicr_df: {missing_cols}. Using fallback mapping.")
            return pd_model_col.map(fallback_mapping), pd_model_col.map(fallback_mapping)
        
        # Create mapping dictionaries
        mapping_orig = dict(zip(mapping_sicr_df[template_pd_code_reporting], mapping_sicr_df[template_pd_name_origination]))
        mapping_reporting = dict(zip(mapping_sicr_df[template_pd_code_reporting], mapping_sicr_df[template_pd_name_reporting]))

        # Apply mappings
        return pd_model_col.map(mapping_orig), pd_model_col.map(mapping_reporting)
    except Exception as e:
        logger.error(f"Error in stage_get_pd_name: {e}")
        return None, None
    
def stage_get_pd_cumulative(simulation_df: pd.DataFrame,
                            template_df: pd.DataFrame,
                            simu_segment_col: str,
                            simu_rating_col: str,
                            simu_date_col: str,
                            simu_nb_step_col: str = "NB_TIME_STEPS",
                            template_vintage_col: str = "VINTAGE_QUARTER",
                            template_segment_col: str = "IFRS9_PD_MODEL_CODE",
                            template_rating_col: str = "RATING") -> pd.DataFrame:
    # Check if either DataFrame is None or empty
    if simulation_df is None or simulation_df.empty:
        logger.warning("Simulation DataFrame is empty or None.")
        raise ValueError("Simulation DataFrame is empty or None.")
    if template_df is None or template_df.empty:
        logger.warning("Template DataFrame is empty or None.")
        raise ValueError("Template DataFrame is empty or None.")
    
    # Handle missing columns
    required_simu_cols = [simu_segment_col, simu_rating_col, simu_date_col, simu_nb_step_col]
    missing_simu_cols = [col for col in required_simu_cols if col not in simulation_df.columns]
    if missing_simu_cols:
        logger.error(f"Missing columns in simulation_df: {missing_simu_cols}")
        raise ValueError(f"Missing columns in simulation_df: {missing_simu_cols}")
    
    required_template_cols = [template_vintage_col, template_segment_col, template_rating_col]
    missing_template_cols = [col for col in required_template_cols if col not in template_df.columns]
    if missing_template_cols:
        logger.error(f"Missing columns in template_df: {missing_template_cols}")
        raise ValueError(f"Missing columns in template_df: {missing_template_cols}")
    
    simulation_df = simulation_df.loc[:, required_simu_cols]

    # Convert date column to datetime
    simulation_df[simu_date_col] = pd.to_datetime(simulation_df[simu_date_col], errors='coerce')

    # Remove na rows from template
    template_df = template_df.dropna(subset=[template_vintage_col, template_segment_col, template_rating_col])

    # Drop duplicates, keeping the last occurrence
    template_df = template_df.drop_duplicates(subset=[template_vintage_col, template_segment_col, template_rating_col], keep='last')

    # Normalize string columns to uppercase and strip whitespace
    for col in required_simu_cols:
        if simulation_df[col].dtype == object:
            simulation_df.loc[:, col] = simulation_df[col].where(simulation_df[col].isna(), simulation_df[col].astype(str).str.upper().str.strip())
    for col in required_template_cols:
        if template_df[col].dtype == object:
            template_df.loc[:, col] = template_df[col].where(template_df[col].isna(), template_df[col].astype(str).str.upper().str.strip())

    # Get PD columns from template
    pd_columns = [col for col in template_df.columns if col.startswith("PD_")]

    # Convert vintage quarters to dates
    list_date_vintage = [convert_quarter_to_date(q) for q in template_df[template_vintage_col].unique()]
    min_date_vintage = min(list_date_vintage)

    # Floor simulation dates to min vintage date
    simulation_df[f"{simu_date_col}_FLOOR"] = simulation_df[simu_date_col].clip(lower=min_date_vintage)
    simulation_df['VINTAGE_QUARTER'] = simulation_df[f"{simu_date_col}_FLOOR"].dt.quarter.astype(str) + ' ' + simulation_df[f"{simu_date_col}_FLOOR"].dt.year.astype(str)

    # Pivot template for faster lookup
    template_df_melt = pd.melt(template_df,
                               id_vars=[template_vintage_col, template_segment_col, template_rating_col],
                               value_vars=pd_columns,
                               var_name='Step',
                               value_name='CUMULATED_PD_LIFETIME')
    # Gérer les valeurs non-numériques avant conversion en int
    template_df_melt["Step"] = pd.to_numeric(
        template_df_melt["Step"].str.replace("PD_", ""), 
        errors='coerce'
    ).fillna(0).astype(int)

    # cap number of steps to max available in template
    simulation_df[simu_nb_step_col] = simulation_df[simu_nb_step_col].clip(upper=len(pd_columns))

    result_df = simulation_df.merge(template_df_melt, how="left",
                                    left_on=['VINTAGE_QUARTER', simu_segment_col, simu_rating_col, simu_nb_step_col],
                                    right_on=[template_vintage_col, template_segment_col, template_rating_col, 'Step'])
    result_df.index = simulation_df.index

    if "CUMULATED_PD_LIFETIME" in result_df:
        # Ensure CUMULATED_PD_LIFETIME is float
        result_df["CUMULATED_PD_LIFETIME"] = pd.to_numeric(result_df["CUMULATED_PD_LIFETIME"], errors='coerce')
        logger.info("Successfully retrieved CUMULATED_PD_LIFETIME from template.")
        return result_df.loc[:, [*required_simu_cols, "CUMULATED_PD_LIFETIME"]]
    
    return result_df

def stage_pd_comparison(resid_mat, PD_origination_date, PD_reporting_date):

    pd_lt_reporting = PD_reporting_date.clip(lower = 0, upper= 1)/resid_mat
    pd_lt_origination = PD_origination_date.clip(lower = 0, upper= 1)/resid_mat

    absolute_diff = (pd_lt_reporting - pd_lt_origination)
    relative_diff = pd_lt_reporting / pd_lt_origination.replace(0, np.nan)

    return absolute_diff, relative_diff

def get_rating_as_of_date(df, tranche_type_col, contract_id_col, operation_id_col, rating_calculation_col, rating_status_col):

    # Select rating_calculation for each contract & operation whose tranche_type is in ["UNSECURED", "COLLATERALIZED"]
    # and spread over all tranches of the contract & operation
    obligor_mask = df[tranche_type_col].isin(["UNSECURED", "COLLATERALIZED"])
    obligor_rating = (df.loc[obligor_mask]
                      .groupby([contract_id_col, operation_id_col])[rating_calculation_col]
                      .first())
    return obligor_rating.reindex(df.index)
