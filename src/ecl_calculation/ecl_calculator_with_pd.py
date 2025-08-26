"""
Integration module for ECL calculation with PD segment mapping.

This module extends the existing ECL calculator to include PD segment mapping
functionality, combining time steps calculation with PD values extraction.
"""

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.core import base_ecl_calculator as bcalc
from src.ecl_calculation.time_steps import maturity, nb_time_steps
from src.ecl_calculation.get_terms import create_pd_segment_mapper

# Module logger
logger = logging.getLogger(__name__)


class ECLCalculatorWithPD(bcalc.BaseECLCalculator):
    """
    Enhanced ECL Calculator that includes PD segment mapping functionality.
    
    This class extends the base ECL calculator to:
    1. Calculate time steps for each contract
    2. Map PD segments from simulation data to template data  
    3. Extract PD values for each time step
    4. Prepare data for ECL calculation
    """
    
    def __init__(self, ecl_operation_data: cst.ECLOperationData):
        """
        Initialize ECL Calculator with PD mapping capabilities.
        
        Args:
            ecl_operation_data: Container with operation details, simulation data, and template data
        """
        super().__init__(ecl_operation_data)
        self.pd_mapper = None
        
    def initialize_pd_mapper(self):
        """
        Initialize the PD segment mapper.
        """
        if self.pd_mapper is None:
            self.pd_mapper = create_pd_segment_mapper(self.data)
            logger.info("PD segment mapper initialized")
    
    def get_time_steps(self):
        """
        Calculate time steps and maturity for each contract.
        This extends the base functionality to prepare for PD mapping.
        """
        # Get the template for time steps mapping
        template_name = cst.MAPPING_TIME_STEPS_TEMPLATES_CONFIG.get(
            (self.data.operation_type, self.data.operation_status)
        )
        
        if not template_name:
            logger.error(f"No time steps template configured for {self.data.operation_type.value} - {self.data.operation_status.value}")
            return
            
        template_df = self.data.template_data.get(template_name)
        if template_df is None or template_df.empty:
            logger.error(f"Time steps template '{template_name}' not found or empty")
            return
        
        # Calculate residual maturity in months
        logger.info("Calculating residual maturity for contracts...")
        self.data.df["RESIDUAL_MATURITY_MONTHS"] = self.data.df.apply(
            lambda x: maturity(x['EXPOSURE_END_DATE'], x['AS_OF_DATE']), 
            axis=1
        )
        
        # Calculate number of time steps and time step lists
        logger.info("Calculating time steps for contracts...")
        time_step_results = self.data.df["RESIDUAL_MATURITY_MONTHS"].apply(
            lambda x: nb_time_steps(x, template_df)
        )
        
        self.data.df["NB_TIME_STEPS"] = time_step_results.apply(lambda x: x[0])
        self.data.df["NB_MONTHS_LIST"] = time_step_results.apply(lambda x: x[1])
        
        logger.info(f"Time steps calculated for {len(self.data.df)} contracts")
        logger.info(f"Average number of time steps: {self.data.df['NB_TIME_STEPS'].mean():.2f}")
        
    def map_pd_segments(self, 
                       segment_column: str = 'CALCULATION_RATING',
                       scenario: str = 'BASE',
                       default_segment: str = None) -> pd.DataFrame:
        """
        Map PD segments and extract PD values for each contract.
        
        Args:
            segment_column: Column name containing segment information
            scenario: Scenario to use for PD lookup  
            default_segment: Default segment to use if no match is found
            
        Returns:
            pd.DataFrame: DataFrame with PD values mapped for each contract
        """
        # Initialize PD mapper if not already done
        self.initialize_pd_mapper()
        
        # Map PD segments
        logger.info(f"Mapping PD segments using scenario '{scenario}'...")
        pd_results = self.pd_mapper.map_pd_segments(
            segment_column=segment_column,
            scenario=scenario,
            default_segment=default_segment
        )
        
        return pd_results
    
    def create_expanded_dataset_with_pd(self,
                                      segment_column: str = 'CALCULATION_RATING',
                                      scenario: str = 'BASE',
                                      default_segment: str = None) -> pd.DataFrame:
        """
        Create expanded dataset with one row per time step, including PD values.
        
        This method:
        1. Expands each contract to multiple rows (one per time step)
        2. Adds PD values for each time step
        3. Adds time step information
        
        Args:
            segment_column: Column name containing segment information
            scenario: Scenario to use for PD lookup
            default_segment: Default segment to use if no match is found
            
        Returns:
            pd.DataFrame: Expanded dataset with PD values per time step
        """
        # Ensure time steps are calculated
        if 'NB_TIME_STEPS' not in self.data.df.columns:
            logger.info("Time steps not calculated yet. Calculating now...")
            self.get_time_steps()
        
        # Get PD mapping
        pd_results = self.map_pd_segments(
            segment_column=segment_column,
            scenario=scenario,
            default_segment=default_segment
        )
        
        if pd_results.empty:
            logger.error("No PD mapping results available for dataset expansion")
            return pd.DataFrame()
        
        # Merge simulation data with PD results
        merged_df = self.data.df.merge(
            pd_results[['CONTRACT_ID', 'SEGMENT_MAPPED', 'SCENARIO'] + 
                      [col for col in pd_results.columns if col.startswith('PD_')]],
            on='CONTRACT_ID',
            how='left'
        )
        
        logger.info(f"Merged simulation data with PD results: {len(merged_df)} contracts")
        
        # Expand dataset - one row per time step
        expanded_rows = []
        
        for idx, row in merged_df.iterrows():
            contract_id = row['CONTRACT_ID']
            nb_time_steps = row['NB_TIME_STEPS']
            nb_months_list = row['NB_MONTHS_LIST']
            
            # Get PD columns for this contract
            pd_columns = [col for col in row.index if col.startswith('PD_')]
            pd_values = [row[col] for col in pd_columns]
            
            # Create one row per time step
            for step in range(int(nb_time_steps)):
                expanded_row = row.copy()
                
                # Add time step information
                expanded_row['TIME_STEP'] = step + 1
                expanded_row['TIME_STEP_MONTHS'] = nb_months_list[step] if step < len(nb_months_list) else np.nan
                
                # Add PD value for this time step
                expanded_row['PD_VALUE'] = pd_values[step] if step < len(pd_values) else np.nan
                
                # Add time to maturity for this step
                if step == 0:
                    expanded_row['TIME_TO_STEP_MONTHS'] = nb_months_list[step] if nb_months_list else 0
                else:
                    prev_months = nb_months_list[step-1] if step-1 < len(nb_months_list) else 0
                    curr_months = nb_months_list[step] if step < len(nb_months_list) else 0
                    expanded_row['TIME_TO_STEP_MONTHS'] = curr_months - prev_months
                
                expanded_rows.append(expanded_row)
        
        expanded_df = pd.DataFrame(expanded_rows)
        
        logger.info(f"Created expanded dataset with {len(expanded_df)} rows ({len(expanded_df)/len(merged_df):.1f} rows per contract on average)")
        
        return expanded_df
    
    def get_pd_statistics(self, 
                         segment_column: str = 'CALCULATION_RATING',
                         scenario: str = 'BASE') -> Dict[str, Any]:
        """
        Get statistics about PD values in the dataset.
        
        Args:
            segment_column: Column name containing segment information
            scenario: Scenario to use for PD lookup
            
        Returns:
            Dict: Dictionary with PD statistics
        """
        # Get PD mapping
        pd_results = self.map_pd_segments(
            segment_column=segment_column,
            scenario=scenario
        )
        
        if pd_results.empty:
            return {}
        
        stats = {}
        
        # Get PD columns
        pd_columns = [col for col in pd_results.columns if col.startswith('PD_')]
        
        for col in pd_columns:
            pd_values = pd_results[col].dropna()
            if len(pd_values) > 0:
                stats[col] = {
                    'count': len(pd_values),
                    'mean': pd_values.mean(),
                    'std': pd_values.std(),
                    'min': pd_values.min(),
                    'max': pd_values.max(),
                    'median': pd_values.median()
                }
        
        # Overall statistics
        all_pd_values = pd.concat([pd_results[col].dropna() for col in pd_columns])
        if len(all_pd_values) > 0:
            stats['overall'] = {
                'total_values': len(all_pd_values),
                'mean': all_pd_values.mean(),
                'std': all_pd_values.std(),
                'min': all_pd_values.min(),
                'max': all_pd_values.max()
            }
        
        # Segment statistics
        if 'SEGMENT_MAPPED' in pd_results.columns:
            segment_stats = {}
            for segment in pd_results['SEGMENT_MAPPED'].unique():
                segment_data = pd_results[pd_results['SEGMENT_MAPPED'] == segment]
                segment_pd_values = pd.concat([segment_data[col].dropna() for col in pd_columns])
                if len(segment_pd_values) > 0:
                    segment_stats[segment] = {
                        'contracts': len(segment_data),
                        'mean_pd': segment_pd_values.mean(),
                        'min_pd': segment_pd_values.min(),
                        'max_pd': segment_pd_values.max()
                    }
            stats['by_segment'] = segment_stats
        
        return stats
    
    def validate_pd_mapping(self, 
                           segment_column: str = 'CALCULATION_RATING',
                           scenario: str = 'BASE') -> Dict[str, Any]:
        """
        Validate PD mapping results and identify potential issues.
        
        Args:
            segment_column: Column name containing segment information
            scenario: Scenario to use for PD lookup
            
        Returns:
            Dict: Validation results with warnings and errors
        """
        validation_results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        try:
            # Check if required data is available
            if self.data.df is None or self.data.df.empty:
                validation_results['errors'].append("No simulation data available")
                return validation_results
            
            if segment_column not in self.data.df.columns:
                validation_results['errors'].append(f"Segment column '{segment_column}' not found in simulation data")
                return validation_results
            
            # Initialize PD mapper
            self.initialize_pd_mapper()
            
            # Check available segments and scenarios
            available_segments = self.pd_mapper.get_available_segments()
            available_scenarios = self.pd_mapper.get_available_scenarios()
            
            if not available_segments:
                validation_results['errors'].append("No segments available in PD template")
                return validation_results
            
            if scenario not in [s.upper() for s in available_scenarios]:
                validation_results['warnings'].append(f"Scenario '{scenario}' not found in available scenarios: {available_scenarios}")
            
            # Get PD mapping
            pd_results = self.map_pd_segments(
                segment_column=segment_column,
                scenario=scenario
            )
            
            if pd_results.empty:
                validation_results['errors'].append("PD mapping returned no results")
                return validation_results
            
            # Check for unmapped contracts
            unmapped_count = pd_results['SEGMENT_MAPPED'].isna().sum()
            if unmapped_count > 0:
                validation_results['warnings'].append(f"{unmapped_count} contracts have unmapped segments")
            
            # Check for missing PD values
            pd_columns = [col for col in pd_results.columns if col.startswith('PD_')]
            for col in pd_columns:
                missing_count = pd_results[col].isna().sum()
                if missing_count > 0:
                    validation_results['warnings'].append(f"{missing_count} contracts missing PD values for {col}")
            
            # Check for unusual PD values
            for col in pd_columns:
                pd_values = pd_results[col].dropna()
                if len(pd_values) > 0:
                    if (pd_values < 0).any():
                        validation_results['warnings'].append(f"Negative PD values found in {col}")
                    if (pd_values > 1).any():
                        validation_results['warnings'].append(f"PD values > 1 found in {col}")
                    if pd_values.std() == 0:
                        validation_results['info'].append(f"All PD values are identical in {col}")
            
            # Success info
            validation_results['info'].append(f"Successfully mapped PD values for {len(pd_results)} contracts")
            validation_results['info'].append(f"Available segments: {available_segments}")
            validation_results['info'].append(f"Available scenarios: {available_scenarios}")
            validation_results['info'].append(f"PD time steps columns: {len(pd_columns)}")
            
        except Exception as e:
            validation_results['errors'].append(f"Error during validation: {str(e)}")
        
        return validation_results


# Enhanced Non-Retail ECL Calculator with PD mapping
class NRS1S2ECLCalculatorWithPD(ECLCalculatorWithPD):
    """
    Non-Retail S1+S2 ECL Calculator with PD mapping capabilities.
    """
    
    def calculate_ecl_with_pd(self, 
                            segment_column: str = 'CALCULATION_RATING',
                            scenario: str = 'BASE',
                            default_segment: str = 'INVESTMENT_GRADE') -> pd.DataFrame:
        """
        Calculate ECL with PD mapping for Non-Retail S1+S2 operations.
        
        Args:
            segment_column: Column name containing segment information
            scenario: Scenario to use for PD lookup
            default_segment: Default segment for unmapped contracts
            
        Returns:
            pd.DataFrame: Expanded dataset ready for ECL calculation
        """
        logger.info("Starting ECL calculation with PD mapping for Non-Retail S1+S2")
        
        # Step 1: Calculate time steps
        self.get_time_steps()
        
        # Step 2: Create expanded dataset with PD values
        expanded_df = self.create_expanded_dataset_with_pd(
            segment_column=segment_column,
            scenario=scenario,
            default_segment=default_segment
        )
        
        if expanded_df.empty:
            logger.error("Failed to create expanded dataset with PD values")
            return pd.DataFrame()
        
        # Step 3: Validate results
        validation_results = self.validate_pd_mapping(segment_column, scenario)
        
        if validation_results['errors']:
            logger.error(f"Validation errors: {validation_results['errors']}")
        
        if validation_results['warnings']:
            logger.warning(f"Validation warnings: {validation_results['warnings']}")
        
        logger.info("ECL calculation with PD mapping completed successfully")
        
        return expanded_df


# Factory function for enhanced ECL calculators
def create_ecl_calculator_with_pd(ecl_operation_data: cst.ECLOperationData) -> ECLCalculatorWithPD:
    """
    Factory function to create ECL calculator with PD mapping capabilities.
    
    Args:
        ecl_operation_data: Container with operation details, simulation data, and template data
        
    Returns:
        ECLCalculatorWithPD: Enhanced ECL calculator instance
    """
    calculator_mapping = {
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): NRS1S2ECLCalculatorWithPD,
        # Add more mappings as needed
        # (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): RetailS1S2ECLCalculatorWithPD,
    }
    
    key = (ecl_operation_data.operation_type, ecl_operation_data.operation_status)
    calculator_class = calculator_mapping.get(key)
    
    if not calculator_class:
        # Fall back to base class
        logger.warning(f"No specific calculator found for {key}. Using base ECLCalculatorWithPD")
        calculator_class = ECLCalculatorWithPD
    
    return calculator_class(ecl_operation_data)


if __name__ == "__main__":
    print("ECL Calculator with PD mapping module loaded successfully")
    print("Available classes:")
    print("- ECLCalculatorWithPD: Base enhanced ECL calculator")
    print("- NRS1S2ECLCalculatorWithPD: Non-Retail S1+S2 specific calculator")
    print("- create_ecl_calculator_with_pd(): Factory function")
