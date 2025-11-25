
from src.core.librairies import *
from src.core import config as cst
from src.core import base_ecl_calculator as bcalc

from src.ecl_calculation.time_steps import maturity, nb_time_steps
from src.ecl_calculation.get_terms import get_terms_from_template, extend_terms_columns, fill_terms_param, pd_interpolation, get_max_maturity_lgd
from src.ecl_calculation.amortization_ead import constant_amortization, infine_ead, off_balance_ead, linear_ead_amortization, apply_ead_amortization
from src.ecl_calculation.discount_factor import discount_factor, discount_factor_quarterly, apply_discount_factor

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

        if self.data.df is None or self.data.df.empty:
            logger.error("DataFrame is empty. Cannot compute time steps.")
            raise ValueError("DataFrame is empty. Cannot compute time steps.")
 
        # Get the data for mapping template
        template_name = cst.MAPPING_TIME_STEPS_TEMPLATES_CONFIG.get((self.data.operation_type, self.data.operation_status))

        if self.data.template_data is not None:
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
        # Update mapping time steps in data container
        self.data.step_months = step_months

    def get_scenarios(self):
        '''
        Get the list of scenarios for ECL calculation.
        Inherited from BaseECLCalculator.
        '''
        return super().get_scenarios()
    
    def apply_segmentation_by_rules(self):
        '''
        Apply segmentation rules to the DataFrame.
        Inherited from BaseECLCalculator.
        '''
        return super().apply_segmentation_by_rules()
    
    def get_amortization_type(self):

        # Get EAD from Jarvis results
        # if self.data.list_jarvis_file_paths:
        #     results_ead_jarvis = []
        #     for jarvis_file in self.data.list_jarvis_file_paths:
        #         logger.info(f"Loading EAD from Jarvis file: {jarvis_file}")
        #         ead_jarvis = get_ead_jarvis(i, "timeBuckets.json")
        #         results_ead_jarvis.append(ead_jarvis)
        #         del ead_jarvis
        #         gc.collect()
        #     jarvis_ead_df = pd.concat(results_ead_jarvis, axis=0).sort_index()
        #     del results_ead_jarvis
        #     gc.collect()

        #     if jarvis_ead_df is not None and not jarvis_ead_df.empty:
        #         self.data.df = self.data.df.merge(jarvis_ead_df, how='left', left_index=True, right_index=True)
        # Default amortization category
        self.data.df["AMORTIZATION_CATEGORY"] = "ON_BALANCE_INFINE"

        if "ACCOUNTING_TYPE" in self.data.df.columns:
            # Off balance sheet items => Off-balance amortization
            mask = self.data.df["ACCOUNTING_TYPE"].astype(str).str.strip().str.upper().isin(["H", "OFF_BALANCE", "OFF-BALANCE", "OFF BALANCE"])
            self.data.df.loc[mask, "AMORTIZATION_CATEGORY"] = "OFF_BALANCE"

            # On balance sheet in-fine amortization
            mask_on_balance = (self.data.df["ACCOUNTING_TYPE"].astype(str).str.strip().str.upper().isin(["B", "ON_BALANCE", "ON-BALANCE", "ON BALANCE"]))
            mask_infine = (self.data.df["AMORTIZATION_TYPE"].astype(str).str.strip().str.upper().isin(["IN FINE", "I_FINE", "I FINE", "IN_FINE"]))
            mask = mask_on_balance & mask_infine
            self.data.df.loc[mask, "AMORTIZATION_CATEGORY"] = "ON_BALANCE_INFINE"

            # On balance sheet linear amortization
            mask_linear = self.data.df["AMORTIZATION_TYPE"].astype(str).str.strip().str.upper().isin(["LINEAR", "M-LINEAR"])
            mask = mask_on_balance & mask_linear
            self.data.df.loc[mask, "AMORTIZATION_CATEGORY"] = "ON_BALANCE_LINEAR"

    def calcul_ecl(self):
        key = (self.data.operation_type, self.data.operation_status)

        # NB row initial
        nb_row_init = self.data.df.shape[0]

        # Discount factor mapping
        discount_map = {
            "OFF_BALANCE": discount_factor,
            "ON_BALANCE_LINEAR": discount_factor,
            "ON_BALANCE_INFINE": discount_factor
        }
        # Amortization mapping
        amortization_map = {
            "OFF_BALANCE": off_balance_ead,
            "ON_BALANCE_INFINE": infine_ead,
            "ON_BALANCE_LINEAR": linear_ead_amortization
        }

        # Discount factor calculation
        logger.info("\n*** Step 0: Calculate Discount Factors ***\n")
        DF_df = apply_discount_factor(self.data.df, 
                                      as_of_date_col="AS_OF_DATE", 
                                      exposure_end_date_col="EXPOSURE_END_DATE",
                                      annual_rate_col="CONTRACTUAL_CLIENT_RATE",
                                      step_months=self.data.step_months,
                                      discount_map=discount_map)
        
        all_steps = len(self.data.step_months)

        for scen in self.data.list_scenarios:

            logger.info(f"\n\n--------------------Calculating ECL for scenario: {scen} ------------------\n")
            # PD
            logger.info("\n*** Step 1: Get PD terms from template ***\n")
            import time
            time.sleep(5)
            PD_df = get_terms_from_template(self.data.df, cst.PD_SHEET_MAPPING_CONFIG, key, 
                                            self.data.template_data, "PD_", scen,
                                            additional_fields=["AS_OF_DATE", "EXPOSURE_END_DATE"])
            
            PD_df = extend_terms_columns(PD_df, "NB_TIME_STEPS", "PD_")
            PD_df = pd_interpolation(PD_df, self.data.step_months,
                                     nb_steps_col="NB_TIME_STEPS",
                                     maturity_col="RESIDUAL_MATURITY_MONTHS",
                                     method="linear", pd_prefix="PD_")
            
            # LGD
            
            logger.info("\n*** Step 2: Get LGD terms from template ***\n")
            time.sleep(5)
            LGD_df = get_terms_from_template(self.data.df, cst.LGD_SHEET_MAPPING_CONFIG, key, 
                                             self.data.template_data, "LGD_", scen,
                                             additional_fields=["LGD_VALUE"])
            LGD_df = extend_terms_columns(LGD_df, "NB_TIME_STEPS", "LGD_")
            LGD_df = fill_terms_param(LGD_df, self.data.step_months,
                                      "LGD_WITHOUT_TIME", "LGD_VALUE", "LGD_")

            # CCF
            logger.info("\n*** Step 3: Get CCF terms from template ***\n")
            time.sleep(5)
            ead_jarvis_columns = [col for col in self.data.df.columns if col.upper().startswith("EAD_JARVIS_")]
            CCF_df = get_terms_from_template(self.data.df, cst.CCF_SHEET_MAPPING_CONFIG, key, 
                                             self.data.template_data, "CCF_", scen,
                                             additional_fields=["PROVISIONING_BASIS", 
                                                                "AMORTIZATION_CATEGORY",
                                                                "CCF",
                                                                "CONTRACTUAL_CLIENT_RATE",
                                                                "PC_PERCENT"] +
                                                                ead_jarvis_columns)
            CCF_df = extend_terms_columns(CCF_df, "NB_TIME_STEPS", "CCF_")
            CCF_df = fill_terms_param(CCF_df, self.data.step_months,
                                      "CCF_WITHOUT_TIME", "CCF", "CCF_")
            
            # EAD calculation
            logger.info("\n*** Step 4: Calculate EAD amortization by time steps ***\n")
            time.sleep(5)
            EAD_df = apply_ead_amortization(df= CCF_df, 
                                            step_months=self.data.step_months,
                                            prov_basis_col="PROVISIONING_BASIS",
                                            resid_mat_col="RESIDUAL_MATURITY_MONTHS",
                                            nb_time_steps_col="NB_TIME_STEPS",
                                            rate_col="CONTRACTUAL_CLIENT_RATE",
                                            business_percent_col="PC_PERCENT",
                                            amortization_map=amortization_map)
            
            # ECL array, step by step
            logger.info("\n*** Step 5: Calculate ECL by time steps ***\n")
            ECL_df = pd.DataFrame(index=self.data.df.index)
            for i in range(1, all_steps + 1):
                ECL_df[f"ECL_{scen}_{i}"] = (EAD_df[f"EAD_{i}"] * PD_df[f"PD_{i}"] * LGD_df[f"LGD_{i}"] * DF_df[f"DF_{i}"]).clip(lower=0)

            # ECL 1Y and ECL Lifetime
            ECL_df[f"ECL_LT_{scen}"] = ECL_df.sum(axis=1)
            # Les colonnes ECL commencent à 1, pas 0
            ecl_1y_cols = [f"ECL_{scen}_{i+1}" for i in range(all_steps) if self.data.step_months[i] <= 12]
            ECL_df[f"ECL_1Y_{scen}"] = ECL_df[ecl_1y_cols].sum(axis=1)
            results_ecl = ECL_df[[f"ECL_1Y_{scen}", f"ECL_LT_{scen}"]]

            del [CCF_df, EAD_df, ECL_df]
            gc.collect()

            # Extract PD_1Y, LGD_1Y for reporting
            pd_1y_cols = [f"PD_{i+1}" for i in range(all_steps) if self.data.step_months[i] <= 12 and f"PD_{i+1}" in PD_df.columns]
            lgd_1y_cols = [f"LGD_{i+1}" for i in range(all_steps) if self.data.step_months[i] == 12 and f"LGD_{i+1}" in LGD_df.columns]
            pd_1y = PD_df[pd_1y_cols].sum(axis=1) if pd_1y_cols else pd.Series(pd.NA, index=self.data.df.index)
            pd_1y.name = f"CUMULATIVE_PD_1Y_{scen}"

            # Agréger LGD à 12 mois en prenant la dernière valeur (ou moyenne)
            if lgd_1y_cols:
                lgd_1y = LGD_df[lgd_1y_cols].iloc[:, -1] if len(lgd_1y_cols) == 1 else LGD_df[lgd_1y_cols].mean(axis=1)
            else:
                lgd_1y = pd.Series(pd.NA, index=self.data.df.index)
            lgd_1y.name = f"LGD_1Y_{scen}"
            results_ecl = results_ecl.join(pd_1y).join(lgd_1y)

            # Clean up
            del [PD_df, LGD_df]
            gc.collect()

            # Merge results back to main DataFrame
            self.data.df = self.data.df.join(results_ecl)
            del results_ecl
            gc.collect()
        del DF_df
        gc.collect()

    def calcul_stage(self):
        '''
        Calculate the stage for each contract.
        Inherited from BaseECLCalculator.
        '''
        return super().calcul_stage()
    
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