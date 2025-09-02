from src.core.librairies import *
from src.core import config as cst
logger = logging.getLogger(__name__)


def get_template_data_keys(dict_config:Dict, dict_key:Tuple[str, str], template_data:Dict):

    template_config = dict_config.get(dict_key)
    if template_config is None:
        raise KeyError(f"Configuration for {dict_key} not found in dict_config.")

    key, val = next(iter(template_config.items()))
    if key not in template_data:
        raise KeyError(f"Template '{key}' specified in configuration for {dict_key} not found in template data.")
    template_df = template_data[key]
    left_key, right_key = val[0], val[1]
    return template_df, left_key, right_key

def get_terms_from_template(simu_df:pd.DataFrame, dict_config:Dict, dict_key:Tuple[str, str], template_data:Dict, prefix="PD_"):

    # Get template df and keys for merge
    template_df, left_key, right_key = get_template_data_keys(dict_config, dict_key, template_data)

    # Check if either DataFrame is None or empty
    if simu_df.empty or template_df.empty:
        logger.error("Simulation or template DataFrame is empty.")
        raise ValueError("Simulation or template DataFrame is empty.")

    # Check for missing keys in simu_df and template_df
    missing_keys_simu = [col for col in left_key if col not in simu_df.columns]
    missing_keys_template = [col for col in right_key if col not in template_df.columns]

    if missing_keys_simu:
        logger.error(f"Missing keys in simulation DataFrame: {missing_keys_simu}")
        raise ValueError(f"Missing keys in simulation DataFrame: {missing_keys_simu}")
    if missing_keys_template:
        logger.error(f"Missing keys in template DataFrame: {missing_keys_template}")
        raise ValueError(f"Missing keys in template DataFrame: {missing_keys_template}")

    # Clean and normalize keys
    for col in left_key:
        simu_df[col] = simu_df[col].where(simu_df[col].isna(), simu_df[col].astype(str).str.strip().str.upper())
    for col in right_key:
        template_df[col] = template_df[col].where(template_df[col].isna(), template_df[col].astype(str).str.strip().str.upper())

    # Remove rows on template_df with missing keys
    template_df = template_df.dropna(subset=right_key)

    # Remove duplicates on template df, based on right key
    template_df = template_df.drop_duplicates(subset=right_key)
    get_columns = [col for col in template_df.columns if col.strip().startswith(prefix)]

    # Left join simu_df and template_df
    merged_df = simu_df.merge(template_df, how="left", left_on=left_key, right_on=right_key)
    # Retain only from template_df the columns with prefix
    simu_df = merged_df[simu_df.columns.tolist() + get_columns]

    return simu_df


if __name__ == "__main__":
    template_data = {
        "F6-PD S1S2 Non Retail": pd.DataFrame(columns=["IFRS9_PD_MODEL_AFTER_CRM", "RATING_CALCULATION", "IFRS9_PD_MODEL_CODE", "RATING"])
    }

    template_df, left_key, right_key = get_template_data_keys(cst.PD_SHEET_MAPPING_CONFIG, (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING), template_data)
    print(template_df.head())
    print(left_key)
    print(right_key)