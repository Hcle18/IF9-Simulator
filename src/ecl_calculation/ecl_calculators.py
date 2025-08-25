"""
ECL Calculator implementations for different operation type and status combinations.
"""

# Global import
from src.core.librairies import *

# Local imports
from core import config as cst
from core.base_ecl_calculator import (
    BaseECLCalculator, 
    ECLCalculationInputs, 
    ECLCalculationResults
)
from src.ecl_parameters import ecl_param_timesteps as ecl_params

logger = logging.getLogger(__name__)


class NonRetailPerformingECLCalculator(BaseECLCalculator):
    """
    ECL Calculator for Non-Retail Performing (S1+S2) operations.
    
    This calculator handles:
    - Complex multi-scenario PD calculations
    - Time-stepped EAD amortization
    - Segment-based risk parameters
    """
    
    def __init__(self):
        super().__init__(cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING)
    
    def _perform_specific_input_validation(self, inputs: ECLCalculationInputs) -> None:
        """
        Validate inputs specific to Non-Retail Performing operations.
        """
        required_sheets = [
            "F1-Mapping fields Non Retail",
            "F2-Mapping time steps", 
            "F6-PD S1S2 Non Retail",
            "F8-LGD S1S2 Non Retail",
            "F12-CCF Non Retail"
        ]
        
        for sheet in required_sheets:
            if sheet not in inputs.template_data:
                raise ValueError(f"Required template sheet '{sheet}' not found")
                
        # Validate simulation data has required columns
        required_sim_columns = ["EXPOSURE_ID", "MATURITY_DATE", "EXPOSURE_AMOUNT", "SEGMENT", "RATING"]
        missing_columns = [col for col in required_sim_columns if col not in inputs.simulation_data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in simulation data: {missing_columns}")
    
    def _calculate_residual_maturity(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Calculate residual maturity using the ecl_param_timesteps module.
        """
        self.logger.info("Calculating residual maturity for Non-Retail Performing operations")
        
        residual_maturity_df = inputs.simulation_data.copy()
        residual_maturity_df['RESIDUAL_MATURITY_MONTHS'] = residual_maturity_df['MATURITY_DATE'].apply(
            lambda x: ecl_params.maturity(x, inputs.as_of_date)
        )
        
        return residual_maturity_df[['EXPOSURE_ID', 'RESIDUAL_MATURITY_MONTHS']]
    
    def _calculate_ead_amortization(self, inputs: ECLCalculationInputs, 
                                   residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EAD amortization schedule based on time steps template.
        """
        self.logger.info("Calculating EAD amortization for Non-Retail Performing operations")
        
        # Get time steps from template
        time_steps_df = inputs.template_data["F2-Mapping time steps"]
        
        # Merge with simulation data to get exposure amounts
        ead_data = inputs.simulation_data[['EXPOSURE_ID', 'EXPOSURE_AMOUNT']].copy()
        
        # Create amortization schedule for each time step
        amortization_schedule = []
        
        for _, exposure in ead_data.iterrows():
            exposure_id = exposure['EXPOSURE_ID']
            initial_amount = exposure['EXPOSURE_AMOUNT']
            
            # Get residual maturity for this exposure
            residual_months = residual_maturity[
                residual_maturity['EXPOSURE_ID'] == exposure_id
            ]['RESIDUAL_MATURITY_MONTHS'].iloc[0]
            
            for _, time_step in time_steps_df.iterrows():
                step = time_step['STEP']
                months = time_step['NB_MONTHS']
                
                # Simple linear amortization (can be made more sophisticated)
                if months <= residual_months:
                    remaining_ratio = max(0, (residual_months - months) / residual_months)
                    ead_amount = initial_amount * remaining_ratio
                else:
                    ead_amount = 0
                
                amortization_schedule.append({
                    'EXPOSURE_ID': exposure_id,
                    'TIME_STEP': step,
                    'MONTHS': months,
                    'EAD_AMOUNT': ead_amount
                })
        
        return pd.DataFrame(amortization_schedule)
    
    def _determine_pd_values(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Determine PD values from the F6-PD S1S2 Non Retail template.
        """
        self.logger.info("Determining PD values for Non-Retail Performing operations")
        
        pd_template = inputs.template_data["F6-PD S1S2 Non Retail"]
        
        # Get PD values by matching segment, scenario, and rating
        pd_results = []
        
        for _, exposure in inputs.simulation_data.iterrows():
            exposure_id = exposure['EXPOSURE_ID']
            segment = exposure['SEGMENT']
            rating = exposure['RATING']
            
            for scenario in inputs.scenarios:
                # Find matching PD values in template
                pd_match = pd_template[
                    (pd_template['SEGMENT'] == segment) & 
                    (pd_template['SCENARIO'] == scenario) &
                    (pd_template['RATING'] == rating)
                ]
                
                if not pd_match.empty:
                    # Extract time-stepped PD values
                    time_step_columns = [col for col in pd_match.columns if col.startswith('TIME_STEP')]
                    
                    for col in time_step_columns:
                        step_number = col.replace('TIME_STEP_', '')
                        pd_value = pd_match[col].iloc[0]
                        
                        pd_results.append({
                            'EXPOSURE_ID': exposure_id,
                            'SCENARIO': scenario,
                            'TIME_STEP': int(step_number),
                            'PD_VALUE': pd_value
                        })
        
        return pd.DataFrame(pd_results)
    
    def _determine_lgd_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine LGD values from the F8-LGD S1S2 Non Retail template.
        """
        self.logger.info("Determining LGD values for Non-Retail Performing operations")
        
        lgd_template = inputs.template_data["F8-LGD S1S2 Non Retail"]
        
        lgd_results = []
        
        for _, exposure in inputs.simulation_data.iterrows():
            exposure_id = exposure['EXPOSURE_ID']
            model_code = exposure.get('IFRS9_MODEL_CODE', 'DEFAULT')
            
            for scenario in inputs.scenarios:
                # Find matching LGD values
                lgd_match = lgd_template[
                    (lgd_template['IFRS9_MODEL_CODE'] == model_code) &
                    (lgd_template['SCENARIO'] == scenario)
                ]
                
                if not lgd_match.empty:
                    lgd_value = lgd_match['LGD_VALUE'].iloc[0]
                    lgd_results.append({
                        'EXPOSURE_ID': exposure_id,
                        'SCENARIO': scenario,
                        'LGD_VALUE': lgd_value
                    })
        
        return pd.DataFrame(lgd_results)
    
    def _determine_ccf_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine CCF values from the F12-CCF Non Retail template.
        """
        self.logger.info("Determining CCF values for Non-Retail Performing operations")
        
        ccf_template = inputs.template_data["F12-CCF Non Retail"]
        
        ccf_results = []
        
        for _, exposure in inputs.simulation_data.iterrows():
            exposure_id = exposure['EXPOSURE_ID']
            model_code = exposure.get('IFRS9_MODEL_CODE', 'DEFAULT')
            
            for scenario in inputs.scenarios:
                # Find matching CCF values
                ccf_match = ccf_template[
                    (ccf_template['IFRS9_MODEL_CODE'] == model_code) &
                    (ccf_template['SCENARIO'] == scenario)
                ]
                
                if not ccf_match.empty:
                    ccf_value = ccf_match['CCF_VALUE'].iloc[0]
                    ccf_results.append({
                        'EXPOSURE_ID': exposure_id,
                        'SCENARIO': scenario,
                        'CCF_VALUE': ccf_value
                    })
        
        return pd.DataFrame(ccf_results)
    
    def _calculate_final_ecl(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame,
                            ead_amortization: pd.DataFrame,
                            pd_values: pd.DataFrame,
                            lgd_values: pd.DataFrame,
                            ccf_values: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Calculate final ECL for Non-Retail Performing operations.
        """
        self.logger.info("Calculating final ECL for Non-Retail Performing operations")
        
        # Merge all components
        ecl_data = ead_amortization.copy()
        
        # Merge PD values
        ecl_data = ecl_data.merge(
            pd_values, 
            on=['EXPOSURE_ID', 'TIME_STEP'], 
            how='left'
        )
        
        # Merge LGD values
        ecl_data = ecl_data.merge(
            lgd_values, 
            on=['EXPOSURE_ID', 'SCENARIO'], 
            how='left'
        )
        
        # Merge CCF values
        ecl_data = ecl_data.merge(
            ccf_values, 
            on=['EXPOSURE_ID', 'SCENARIO'], 
            how='left'
        )
        
        # Calculate ECL: EAD * PD * LGD * CCF
        ecl_data['ECL_AMOUNT'] = (
            ecl_data['EAD_AMOUNT'] * 
            ecl_data['PD_VALUE'] * 
            ecl_data['LGD_VALUE'] * 
            ecl_data['CCF_VALUE']
        )
        
        # ECL by exposure
        ecl_by_exposure = ecl_data.groupby(['EXPOSURE_ID', 'SCENARIO'])['ECL_AMOUNT'].sum().reset_index()
        
        # ECL summary
        ecl_summary = ecl_by_exposure.groupby('SCENARIO')['ECL_AMOUNT'].agg(['sum', 'mean', 'count']).reset_index()
        ecl_summary.columns = ['SCENARIO', 'TOTAL_ECL', 'AVERAGE_ECL', 'EXPOSURE_COUNT']
        
        # Calculation details
        calculation_details = {
            'calculation_method': 'EAD * PD * LGD * CCF',
            'time_steps_used': len(ead_amortization['TIME_STEP'].unique()),
            'scenarios_calculated': len(inputs.scenarios),
            'total_exposures': len(inputs.simulation_data)
        }
        
        return ecl_by_exposure, ecl_summary, calculation_details


class RetailPerformingECLCalculator(BaseECLCalculator):
    """
    ECL Calculator for Retail Performing (S1+S2) operations.
    """
    
    def __init__(self):
        super().__init__(cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING)
    
    def _perform_specific_input_validation(self, inputs: ECLCalculationInputs) -> None:
        """
        Validate inputs specific to Retail Performing operations.
        """
        # Add retail-specific validation
        pass
    
    def _calculate_residual_maturity(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Calculate residual maturity for Retail Performing operations.
        """
        self.logger.info("Calculating residual maturity for Retail Performing operations")
        # Implementation specific to retail performing
        # For now, use the same logic as Non-Retail
        residual_maturity_df = inputs.simulation_data.copy()
        residual_maturity_df['RESIDUAL_MATURITY_MONTHS'] = residual_maturity_df['MATURITY_DATE'].apply(
            lambda x: ecl_params.maturity(x, inputs.as_of_date)
        )
        
        return residual_maturity_df[['EXPOSURE_ID', 'RESIDUAL_MATURITY_MONTHS']]
    
    def _calculate_ead_amortization(self, inputs: ECLCalculationInputs, 
                                   residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EAD amortization for Retail Performing operations.
        """
        self.logger.info("Calculating EAD amortization for Retail Performing operations")
        # Placeholder implementation - to be customized for retail
        return pd.DataFrame()
    
    def _determine_pd_values(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Determine PD values for Retail Performing operations.
        """
        self.logger.info("Determining PD values for Retail Performing operations")
        # Placeholder implementation - to be customized for retail
        return pd.DataFrame()
    
    def _determine_lgd_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine LGD values for Retail Performing operations.
        """
        self.logger.info("Determining LGD values for Retail Performing operations")
        # Placeholder implementation - to be customized for retail
        return pd.DataFrame()
    
    def _determine_ccf_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine CCF values for Retail Performing operations.
        """
        self.logger.info("Determining CCF values for Retail Performing operations")
        # Placeholder implementation - to be customized for retail
        return pd.DataFrame()
    
    def _calculate_final_ecl(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame,
                            ead_amortization: pd.DataFrame,
                            pd_values: pd.DataFrame,
                            lgd_values: pd.DataFrame,
                            ccf_values: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Calculate final ECL for Retail Performing operations.
        """
        self.logger.info("Calculating final ECL for Retail Performing operations")
        # Placeholder implementation - to be customized for retail
        return pd.DataFrame(), pd.DataFrame(), {}


class RetailDefaultedECLCalculator(BaseECLCalculator):
    """
    ECL Calculator for Retail Defaulted (S3) operations.
    """
    
    def __init__(self):
        super().__init__(cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED)
    
    def _perform_specific_input_validation(self, inputs: ECLCalculationInputs) -> None:
        """
        Validate inputs specific to Retail Defaulted operations.
        """
        # Add retail S3-specific validation
        pass
    
    def _calculate_residual_maturity(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Calculate residual maturity for Retail Defaulted operations.
        """
        self.logger.info("Calculating residual maturity for Retail Defaulted operations")
        # For defaulted exposures, residual maturity might be handled differently
        residual_maturity_df = inputs.simulation_data.copy()
        residual_maturity_df['RESIDUAL_MATURITY_MONTHS'] = residual_maturity_df['MATURITY_DATE'].apply(
            lambda x: ecl_params.maturity(x, inputs.as_of_date)
        )
        
        return residual_maturity_df[['EXPOSURE_ID', 'RESIDUAL_MATURITY_MONTHS']]
    
    def _calculate_ead_amortization(self, inputs: ECLCalculationInputs, 
                                   residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EAD amortization for Retail Defaulted operations.
        """
        self.logger.info("Calculating EAD amortization for Retail Defaulted operations")
        # For defaulted exposures, EAD might be the full exposure amount
        return pd.DataFrame()
    
    def _determine_pd_values(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame) -> pd.DataFrame:
        """
        Determine PD values for Retail Defaulted operations.
        """
        self.logger.info("Determining PD values for Retail Defaulted operations")
        # For defaulted exposures, PD might be 1.0
        return pd.DataFrame()
    
    def _determine_lgd_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine LGD values for Retail Defaulted operations.
        """
        self.logger.info("Determining LGD values for Retail Defaulted operations")
        # Placeholder implementation - to be customized for retail S3
        return pd.DataFrame()
    
    def _determine_ccf_values(self, inputs: ECLCalculationInputs) -> pd.DataFrame:
        """
        Determine CCF values for Retail Defaulted operations.
        """
        self.logger.info("Determining CCF values for Retail Defaulted operations")
        # For defaulted exposures, CCF might be different
        return pd.DataFrame()
    
    def _calculate_final_ecl(self, inputs: ECLCalculationInputs,
                            residual_maturity: pd.DataFrame,
                            ead_amortization: pd.DataFrame,
                            pd_values: pd.DataFrame,
                            lgd_values: pd.DataFrame,
                            ccf_values: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Calculate final ECL for Retail Defaulted operations.
        """
        self.logger.info("Calculating final ECL for Retail Defaulted operations")
        # Placeholder implementation - to be customized for retail S3
        return pd.DataFrame(), pd.DataFrame(), {}
