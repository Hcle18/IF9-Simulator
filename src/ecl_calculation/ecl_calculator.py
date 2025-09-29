from src.ecl_calculation.discount_factor import discount_factor, discount_factor_quarterly
from src.core.librairies import *

from src.core import config as cst
from src.core import base_ecl_calculator as bcalc

from src.ecl_calculation.time_steps import maturity, nb_time_steps
from src.ecl_calculation.get_terms import get_list_scenarios, get_terms_from_template, extend_terms_columns, fill_terms_for_lgd_ccf
from src.utils.get_matrix import get_matrix_prefix

logger = logging.getLogger(__name__)  

# ----------------------------------------
# 1. Non Retail Performing ECL Calculator
# ----------------------------------------

class NRS1S2ECLCalculator(bcalc.BaseECLCalculator):
    '''
    Custom class for Non Retail S1+S2 ECL calculation
    '''

    def get_time_steps(self):
        '''
        Get the number of time steps and maturity from the template data.
        '''

        # Get the data for mapping template
        template_name = cst.MAPPING_TIME_STEPS_TEMPLATES_CONFIG.get((self.data.operation_type, self.data.operation_status))

        template_df = self.data.template_data.get(template_name)

        # Residual maturity in months
        self.data.df["RESIDUAL_MATURITY_MONTHS"] =  maturity(self.data.df['EXPOSURE_END_DATE'], self.data.df['AS_OF_DATE'])

        # Number of steps
        #nb_steps, nb_months_list = nb_time_steps(self.data.df["RESIDUAL_MATURITY_MONTHS"], template_df)
        self.data.df["NB_TIME_STEPS"] = nb_time_steps(self.data.df["RESIDUAL_MATURITY_MONTHS"], template_df)
        # self.data.df["NB_MONTHS_LIST"] = nb_months_list

        # Update mapping step to fit the maximum maturity
        step_months = np.sort(template_df["NB_MONTHS"].to_numpy())
        max_maturity = self.data.df["RESIDUAL_MATURITY_MONTHS"].max()
        # Extend step_months to cover all contracts
        while step_months[-1] < max_maturity:
            nb_diff = step_months[-1] - step_months[-2] if len(step_months) > 1 else step_months[-1]
            step_months = np.append(step_months, step_months[-1] + nb_diff)
        self.data.step_months = step_months

    def get_amortization_type(self):

        df = self.data.df

        # Default amortization category
        df["AMORTIZATION_CATEGORY"] = "ON_BALANCE_LINEAR"
        
        if "ACCOUNTING_TYPE" in df.columns:
            # Off balance sheet items => Off-balance amortization
            mask = df["ACCOUNTING_TYPE"].astype(str).str.strip().str.upper().isin(["H", "OFF_BALANCE", "OFF-BALANCE", "OFF BALANCE"])
            df.loc[mask, "AMORTIZATION_CATEGORY"] = "OFF_BALANCE"
        
            # On balance sheet in-fine amortization
            mask_on_balance = (df["ACCOUNTING_TYPE"].astype(str).str.strip().str.upper().isin(["B", "ON_BALANCE", "ON-BALANCE", "ON BALANCE"]))
            mask_infine = df["AMORTIZATION_TYPE"].astype(str).str.strip().str.upper().isin(["IN FINE", "I_FINE", "I FINE", "IN_FINE"])
            mask = mask_on_balance & mask_infine
            df.loc[mask, "AMORTIZATION_CATEGORY"] = "ON_BALANCE_INFINE"

            # On balance sheet linear amortization
            mask_linear = df["AMORTIZATION_TYPE"].astype(str).str.strip().str.upper().isin(["LINEAR", "M-LINEAR"])
            mask = mask_on_balance & mask_linear
            df.loc[mask, "AMORTIZATION_CATEGORY"] = "ON_BALANCE_LINEAR"

        self.data.df = df

    def get_discount_factor(self):
        
        discount_map = {
            "OFF_BALANCE": discount_factor,
            "ON_BALANCE_INFINE": discount_factor,
            "ON_BALANCE_LINEAR": discount_factor_quarterly,
        }
        df = self.data.df
        result_dfs = []
        for amort_type, discount_func in discount_map.items():
            mask = df["AMORTIZATION_CATEGORY"] == amort_type
            if mask.any():
                df_subset = df[mask]
                if discount_func == discount_factor_quarterly:
                    params = ("CONTRACTUAL_CLIENT_RATE", self.data.step_months)
                else:
                    params = ("AS_OF_DATE", "EXPOSURE_END_DATE", "CONTRACTUAL_CLIENT_RATE", self.data.step_months)
                df_subset = discount_func(df_subset, *params)
                result_dfs.append(df_subset)
        self.data.df = pd.concat(result_dfs, axis=0).sort_index()

    def calcul_ecl(self):
        key = (self.data.operation_type, self.data.operation_status)

        all_steps = len(self.data.step_months)

        for scen in self.data.list_scenarios:
            scen_df = get_terms_from_template(self.data.df, cst.PD_SHEET_MAPPING_CONFIG, key, self.data.template_data, "PD_", scen)
            scen_df = extend_terms_columns(scen_df, "NB_TIME_STEPS", "PD_")
            
            scen_df = get_terms_from_template(scen_df, cst.LGD_SHEET_MAPPING_CONFIG, key, self.data.template_data, "LGD_", scen)
            scen_df = extend_terms_columns(scen_df, "NB_TIME_STEPS", "LGD_")

            scen_df = get_terms_from_template(scen_df, cst.CCF_SHEET_MAPPING_CONFIG, key, self.data.template_data, "CCF_", scen)
            scen_df = extend_terms_columns(scen_df, "NB_TIME_STEPS", "CCF_")

            scen_df = fill_terms_for_lgd_ccf(scen_df, self.data.step_months)

            # Calculate EAD
            scen_df = apply_ead_amortization(scen_df, step_months, rate_col="CONTRACTUAL_CLIENT_RATE")

            # Get matrix for EAD, PD, LGD, DISCOUNT
            EAD_matrix = get_matrix_prefix(scen_df, "EAD_")
            PD_matrix = get_matrix_prefix(scen_df, "PD_", round=True, round_nb=7)
            LGD_matrix = get_matrix_prefix(scen_df, "LGD_", round=True, round_nb=7)
            CCF_matrix = get_matrix_prefix(scen_df, "CCF_", round=True, round_nb=7)
            DF_matrix = get_matrix_prefix(scen_df, "DISCOUNT_")

            ECL = EAD_matrix * PD_matrix * LGD_matrix * DF_matrix

            ecl_1y_cols = [i for i in range(all_steps) if step_months[i] <= 12]
            ECL_1Y = ECL[:, ecl_1y_cols].sum(axis=1)
            ECL_LT = ECL.sum(axis=1)

            # Add ECL columns to DataFrame
            ECL_1Y_df = pd.DataFrame(ECL_1Y, columns=[f"ECL_1Y_{scenario}"], index=scen_df.index)
            ECL_LT_df = pd.DataFrame(ECL_LT, columns=[f"ECL_LT_{scenario}"], index=scen_df.index)

            df = pd.concat([df, ECL_1Y_df, ECL_LT_df], axis=1)

            
# ----------------------------------------
# 2. Retail Performing ECL Calculator
# ----------------------------------------




# ========================================
# ECL Calculator Factory
# ========================================

class ECLCalculatorFactory:
    """
    Factory class for creating appropriate ECL calculators based on operation type and status.
    """

    # Registry mapping operation type & status to ECL calculator classes
    _registry_loader: dict[tuple[cst.OperationType, cst.OperationStatus], bcalc.BaseECLCalculator] = {
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): None,
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): None,
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NRS1S2ECLCalculator
    }

    @classmethod
    def get_ecl_calculator(cls, ecl_operation_data: cst.ECLOperationData) -> bcalc.BaseECLCalculator:
        """
        Get the appropriate ECL calculator based on operation type and status from ECLOperationData.

        Args:
            ecl_operation_data: Container with operation details and template file path
            
        Returns:
            BaseECLCalculator: The appropriate ECL calculator instance

        Raises:
            ValueError: If no loader is found for the given operation type and status
        """
        # Get the key as combination of operation type and status
        key = (ecl_operation_data.operation_type, ecl_operation_data.operation_status)

        # Handle case where key is not found in registry
        if key not in cls._registry_loader:
            raise ValueError(f"No template loader found for {ecl_operation_data.operation_type.value} - {ecl_operation_data.operation_status.value}")

        # Get the calculator class from the registry
        calculator_class = cls._registry_loader[key]
        logger.info(f"Creating ECL calculator for {ecl_operation_data.operation_type.value} - {ecl_operation_data.operation_status.value}")

        return calculator_class(ecl_operation_data)

# ==========================================
# ENTRY POINT TO CREATE ECL CALCULATOR
# ==========================================

def ecl_calculator(ecl_operation_data: cst.ECLOperationData) -> bcalc.BaseECLCalculator:
    """
    Entry point function to get a template loader instance for importing & validating templates.

    Args:
        operation_type: The type of operation (NON_RETAIL, RETAIL)
        operation_status: The status of operation (PERFORMING, DEFAULTED)
        template_file_path: Path to the template file
        
    Returns:
        BaseTemplate: The appropriate template loader instance
    """

    # Use the factory to get the appropriate ECL calculator
    return ECLCalculatorFactory.get_ecl_calculator(ecl_operation_data)