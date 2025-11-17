"""
Abstract base class for ECL calculation strategies.

This module defines the interface for ECL calculators that handle different combinations
of operation types (Retail/Non-Retail) and operation status (Performing/Defaulted).
"""

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.core import base_data as bcls
from src.core import base_template as tplm
from src.ecl_calculation.get_terms import get_list_scenarios
from src.ecl_calculation.segmentation_rules import build_rules_from_columns_sheet, build_condition_mask

logger = logging.getLogger(__name__)

class BaseECLCalculator(ABC):
    """
    Abstract base class for ECL calculation strategies.
    
    Each concrete implementation handles a specific combination of:
    - Operation type (Retail, Non-Retail)  
    - Operation status (Performing, Defaulted)
    """

    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize BaseECLCalculator with ECLOperationData.
        
        Args:
            ecl_operation_data: Container with all necessary data for ECL calculation
        """
        self.data = ecl_operation_data

    @abstractmethod
    def get_time_steps(self):
        pass

    
    def get_scenarios(self):

        key = (self.data.operation_type, self.data.operation_status)
        list_scenarios_pd = get_list_scenarios(cst.PD_SHEET_MAPPING_CONFIG, key, self.data.template_data)
        list_scenarios_lgd = get_list_scenarios(cst.LGD_SHEET_MAPPING_CONFIG, key, self.data.template_data)
        list_scenarios_ccf = get_list_scenarios(cst.CCF_SHEET_MAPPING_CONFIG, key, self.data.template_data)

        self.data.list_scenarios = list(set(list_scenarios_pd + list_scenarios_lgd + list_scenarios_ccf))

        logger.info(f"Scenarios identified for {key}: {self.data.list_scenarios}")

    def apply_segmentation_by_rules(self) -> pd.DataFrame:
        key = (self.data.operation_type, self.data.operation_status)

        # Initialize target column
        map_init_target_col = cst.INIT_TARGET_SEGMENT_COLUMN.get(key)
        if map_init_target_col:
            for new_col, source_col in map_init_target_col.items():
                if source_col in self.data.df.columns:
                    self.data.df[new_col] = self.data.df[source_col]
                else:
                    self.data.df[new_col] = np.nan
        try:
            rules_sheet = cst.RULES_SHEET_CONFIG.get(key)
            rules_tmpl_df = self.data.template_data.get(rules_sheet)

            if rules_tmpl_df is None or rules_tmpl_df.empty:
                logger.warning(f"No segmentation rules found in template for {key}. Skipping segmentation.")
                return self.data.df
            
            rules = build_rules_from_columns_sheet(rules_tmpl_df, cst.TARGET_SEGMENT_COLUMN, key, 
                                                   self.data.template_data)
            if rules.empty:
                logger.info(f"No segmentation rules constructed for {key}. Skipping segmentation.")
                return self.data.df
            # Normalize column names in DataFrame
            required_cols = ["RULE_ID", "DRIVER", "OPERATOR", "VALUE", "VALUE_TO", 
                            "SEGMENT", "TYPE_MODEL", "TARGET_COLUMN"]
            for col in required_cols:
                if col not in rules.columns:
                    raise ValueError(f"Missing required column '{col}' in segmentation rules for {key}.")
            rules["DRIVER"] = rules["DRIVER"].astype(str).str.strip().upper()
            rules["TYPE_MODEL"] = rules["TYPE_MODEL"].astype(str).str.strip().upper()
            list_supported_models = list(cst.TARGET_SEGMENT_COLUMN.get(key).keys())

            recap = {model: [] for model in list_supported_models}

            for _, group_model in rules.sort_values(['TYPE_MODEL'].groupby("TYPE_MODEL", sort=False)):
                # Skip if unsupported models
                type_model = group_model["TYPE_MODEL"].unique()[0]
                if type_model not in list_supported_models:
                    logger.info(f"Skipping unsupported model '{type_model}' for {key}.")
                    continue

                # Get unique non-null values
                target_segment_col = group_model["TARGET_COLUMN"].dropna().unique()
                if len(target_segment_col) != 1:
                    logger.error(f"Multiple or no target segment columns found for model '{group_model['TYPE_MODEL'].unique()[0]}' in {key}.")
                    continue

                target_col = target_segment_col[0]

                # List segment to be assigned
                list_assign = group_model["SEGMENT"].dropna().unique().tolist()
                assigned_models = pd.Series([pd.NA] * len(self.data.df), index=self.data.df.index, dtype="object")

                for _, group in group_model.sort_values(['RULE_ID'].groupby("RULE_ID", sort=False)):
                    mask = pd.Series([True] * len(self.data.df), index=self.data.df.index)
                    seg_value = None
                    rule_nb = group["RULE_ID"].unique()[0]

                    for _, row in group.iterrows():
                        tmpl_driver = row["DRIVER"]
                        # type_model = row["TYPE_MODEL"]
                        if tmpl_driver not in self.data.df.columns:
                            logger.warning(f"Driver column '{tmpl_driver}' not found in data for rule {rule_nb} in {key}. Skipping this rule.")
                            mask = pd.Series([False] * len(self.data.df), index=self.data.df.index)
                            break
                        operator = row.get("OPERATOR")
                        if operator is None:
                            operator = "EQ"
                        value = row.get("VALUE")
                        value_to = row.get("VALUE_TO")
                        seg_value = str(row.get("SEGMENT"))
                        col_series = self.data.df[tmpl_driver]
                        cond = build_condition_mask(col_series, operator, cst.DRIVERS_TEMPLATE_CONFIG, key,
                                                    self.data.template_data,
                                                    value, value_to)
                        mask &= cond
                    # Assign segment values based on the constructed mask
                    if seg_value is not None:
                        assigned_models = assigned_models[mask].apply(lambda x: x + [seg_value])
                    assigned_models_cleaned = assigned_models.apply(
                        lambda x: ", ".join(sorted(set(x))) if isinstance(x, list) else pd.NA
                    )

                logger.info("Checking multi matches")
                mask_single_value = assigned_models_cleaned.apply(lambda x: isinstance(x, str) and ("," not in x))
                mask_multiple_values = assigned_models_cleaned.apply(lambda x: isinstance(x, str) and ("," in x))

                logger.info("Finalizing segment assignments")
                self.data.df.loc[mask_single_value, target_col] = assigned_models_cleaned[mask_single_value]
                self.data.df.loc[mask_multiple_values, target_col] = assigned_models_cleaned[mask_multiple_values]
                self.data.df.loc[mask_multiple_values, f"FLAG_MULTI_MATCH_MODEL_{type_model}"] = 1

                segment_no_match = sorted([seg for seg in list_assign if seg not in self.data.df[target_col].unique()])
                segment_match = sorted(self.data.df.loc[mask_single_value, target_col].unique().tolist())
                segment_multi_match = sorted(self.data.df.loc[mask_multiple_values, target_col].unique().tolist())

                recap[type_model] = {
                    "SEGMENTS_ASSIGNED": segment_match,
                    "SEGMENTS_NO_MATCH": segment_no_match,
                    "SEGMENTS_MULTI_MATCH": segment_multi_match
                }
            logger.info(f"Segmentation recap for {key}: {recap}")

        except Exception as e:
            logger.error(f"Error occurred while applying segmentation rules for {key}: {e}")
            return self.data.df

    @abstractmethod
    def get_amortization_type(self):
        pass

    @abstractmethod
    def calcul_ecl(self):
        pass

    @abstractmethod
    def calcul_stage(self):
        pass

    def calcul_ecl_multi(self, weights: Dict[str, float]) -> pd.DataFrame:
        '''
        ECL with multiple scenarios
        Weights: dictionary with scenario names as keys and their corresponding weights as values
        '''
        # Check scenario weights
        missing = [s for s in self.data.list_scenarios if s not in weights.keys()]
        if missing:
            raise ValueError(f"Missing weights for scenarios: {missing}")
        
        if len(weights) != len(self.data.list_scenarios):
            logger.error(f"Weights dictionary contains extra scenarios not in the data.")
            raise ValueError("Weights dictionary contains extra scenarios not in the data.")
        
        if any(w < 0 for w in weights.values()):
            logger.error("All weights must be non-negative.")
            raise ValueError("All weights must be non-negative.")
        
        total_weight = sum(weights.get(scen, 0) for scen in self.data.list_scenarios)
        if not np.isclose(total_weight, 1.0):
            logger.error(f"Weights must sum to 1. Current sum: {total_weight}")
            raise ValueError("Weights must sum to 1.")
        
        # Compute ECL multi
        self.data.df["ECL_1Y_MULTI"] = 0.0
        self.data.df["ECL_LIFETIME_MULTI"] = 0.0

        for scen, weight in weights.items():
            self.data.df["ECL_1Y_MULTI"] += self.data.df[f"ECL_1Y_{scen}"] * weight
            self.data.df["ECL_LIFETIME_MULTI"] += self.data.df[f"ECL_LIFETIME_{scen}"] * weight
        return self.data.df
    
