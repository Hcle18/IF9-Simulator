"""
Module for mapping PD segments from simulation data with PD segments in Excel template sheet
to retrieve PD values per time steps for IFRS9 ECL calculations.

This module provides functionality using a functional approach:
1. Map PD segments between simulation data and template data
2. Extract PD values for specific time steps based on segments
3. Handle different scenarios (base, optimistic, pessimistic)
4. Support flexible templates where any column not starting with "Time_step_" is a driver
5. Support both Non-Retail and Retail operations

Key functions:
- get_driver_columns(): Get all driver columns from template
- map_pd_segments(): Main mapping function with flexible drivers
- get_pd_for_simulation_data(): Convenience function for complete workflow
"""

# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst

# Module logger
logger = logging.getLogger(__name__)


def _get_pd_template_sheet_name(operation_type: cst.OperationType, operation_status: cst.OperationStatus) -> str:
    """
    Get the appropriate PD template sheet name based on operation type and status.
    
    Args:
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        str: Name of the PD template sheet
    """
    pd_sheet_mapping = {
        (cst.OperationType.NON_RETAIL, cst.OperationStatus.PERFORMING): "F6-PD S1S2 Non Retail",
        (cst.OperationType.RETAIL, cst.OperationStatus.PERFORMING): "F6-PD S1S2 Retail",
        (cst.OperationType.RETAIL, cst.OperationStatus.DEFAULTED): "F6-PD S3 Retail"
    }
    
    key = (operation_type, operation_status)
    sheet_name = pd_sheet_mapping.get(key)
    
    if not sheet_name:
        raise ValueError(f"No PD template sheet configured for {operation_type.value} - {operation_status.value}")
        
    return sheet_name


def get_driver_columns(template_data: Dict[str, pd.DataFrame], 
                      operation_type: cst.OperationType, 
                      operation_status: cst.OperationStatus) -> List[str]:
    """
    Get list of driver columns (all columns except time step columns) from the template data.
    Driver columns are any columns that don't start with 'time_step_' (case insensitive).
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        List[str]: List of driver column names in the PD template
    """
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    
    if not template_data or pd_template_sheet not in template_data:
        logger.error(f"PD template sheet '{pd_template_sheet}' not found in template data")
        return []
        
    pd_template = template_data[pd_template_sheet]
    
    # Get all columns that are not time step columns
    driver_columns = [col for col in pd_template.columns 
                     if not col.lower().startswith('time_step')]
    
    logger.info(f"Identified {len(driver_columns)} driver columns: {driver_columns}")
    return driver_columns


def get_unique_values_for_driver(template_data: Dict[str, pd.DataFrame],
                                operation_type: cst.OperationType,
                                operation_status: cst.OperationStatus,
                                driver_column: str) -> List[str]:
    """
    Get list of unique values for a specific driver column.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        driver_column: Name of the driver column
        
    Returns:
        List[str]: List of unique values for the specified driver column
    """
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    
    if not template_data or pd_template_sheet not in template_data:
        logger.error(f"PD template sheet '{pd_template_sheet}' not found in template data")
        return []
        
    pd_template = template_data[pd_template_sheet]
    
    if driver_column not in pd_template.columns:
        logger.error(f"Driver column '{driver_column}' not found in PD template sheet '{pd_template_sheet}'")
        return []
        
    unique_values = pd_template[driver_column].dropna().unique().tolist()
    logger.info(f"Found {len(unique_values)} unique values for driver '{driver_column}': {unique_values}")
    return unique_values


def get_all_driver_combinations(template_data: Dict[str, pd.DataFrame],
                               operation_type: cst.OperationType,
                               operation_status: cst.OperationStatus) -> pd.DataFrame:
    """
    Get all unique combinations of driver values from the template data.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        pd.DataFrame: DataFrame with all unique combinations of driver values
    """
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    
    if not template_data or pd_template_sheet not in template_data:
        logger.error(f"PD template sheet '{pd_template_sheet}' not found in template data")
        return pd.DataFrame()
        
    pd_template = template_data[pd_template_sheet]
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    
    if not driver_columns:
        logger.warning("No driver columns found in PD template")
        return pd.DataFrame()
        
    # Get unique combinations of all driver columns
    driver_combinations = pd_template[driver_columns].drop_duplicates().reset_index(drop=True)
    
    logger.info(f"Found {len(driver_combinations)} unique driver combinations")
    return driver_combinations


def get_time_step_columns(pd_template: pd.DataFrame) -> List[str]:
    """
    Extract time step columns from the PD template.
    
    Args:
        pd_template: DataFrame containing the PD template data
        
    Returns:
        List[str]: List of time step column names sorted by step number
    """
    time_step_columns = [col for col in pd_template.columns if col.lower().startswith('time_step')]
    
    # Sort columns by step number
    def extract_step_number(col_name: str) -> int:
        match = re.search(r'time_step_?(\d+)', col_name.lower())
        return int(match.group(1)) if match else 0
        
    time_step_columns.sort(key=extract_step_number)
    return time_step_columns


def auto_detect_driver_mappings(simulation_df: pd.DataFrame, driver_columns: List[str]) -> Dict[str, str]:
    """
    Auto-detect mappings between template driver columns and simulation data columns.
    
    Args:
        simulation_df: DataFrame containing simulation data
        driver_columns: List of driver column names from template
        
    Returns:
        Dict[str, str]: Mapping from template columns to simulation columns
    """
    mappings = {}
    sim_columns = simulation_df.columns.tolist()
    
    for template_col in driver_columns:
        template_lower = template_col.lower()
        
        # Try exact match first
        exact_matches = [col for col in sim_columns if col.lower() == template_lower]
        if exact_matches:
            mappings[template_col] = exact_matches[0]
            continue
        
        # Try partial matches for common patterns
        if 'segment' in template_lower:
            segment_matches = [col for col in sim_columns 
                             if 'segment' in col.lower() or 'rating' in col.lower()]
            if segment_matches:
                mappings[template_col] = segment_matches[0]
                continue
        
        if 'scenario' in template_lower:
            scenario_matches = [col for col in sim_columns 
                              if 'scenario' in col.lower()]
            if scenario_matches:
                mappings[template_col] = scenario_matches[0]
                continue
                
        if 'rating' in template_lower:
            rating_matches = [col for col in sim_columns 
                            if 'rating' in col.lower()]
            if rating_matches:
                mappings[template_col] = rating_matches[0]
                continue
        
        # If no match found, set to None (will use default value)
        mappings[template_col] = None
        logger.warning(f"No simulation column found for template driver '{template_col}'")
    
    return mappings


def get_default_values(template_data: Dict[str, pd.DataFrame],
                      operation_type: cst.OperationType,
                      operation_status: cst.OperationStatus,
                      driver_columns: List[str]) -> Dict[str, str]:
    """
    Get default values for driver columns.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        driver_columns: List of driver column names
        
    Returns:
        Dict[str, str]: Default values for each driver column
    """
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    pd_template = template_data[pd_template_sheet]
    
    defaults = {}
    
    for col in driver_columns:
        col_lower = col.lower()
        
        # Get most common value as default
        if col in pd_template.columns:
            most_common = pd_template[col].mode()
            if len(most_common) > 0:
                defaults[col] = most_common.iloc[0]
            else:
                # Fallback defaults based on column type
                if 'segment' in col_lower:
                    defaults[col] = 'DEFAULT_SEGMENT'
                elif 'scenario' in col_lower:
                    defaults[col] = 'BASE'
                elif 'rating' in col_lower:
                    defaults[col] = 'DEFAULT_RATING'
                else:
                    defaults[col] = 'DEFAULT'
        else:
            defaults[col] = 'DEFAULT'
    
    return defaults


def map_simulation_value_to_template_value(template_column: str, simulation_value: str) -> str:
    """
    Map simulation data value to template value for a specific driver column.
    This function can be customized for specific business logic.
    
    Args:
        template_column: Name of the template driver column
        simulation_value: Value from simulation data
        
    Returns:
        str: Mapped value for template lookup
    """
    if not simulation_value or pd.isna(simulation_value):
        return 'DEFAULT'
        
    # Convert to string and clean
    value = str(simulation_value).strip().upper()
    template_col_lower = template_column.lower()
    
    # Apply column-specific mapping logic
    if 'segment' in template_col_lower or 'rating' in template_col_lower:
        # Example rating/segment mapping logic (customize as needed)
        if value in ['A+', 'A', 'A-', 'AAA', 'AA+', 'AA', 'AA-']:
            return 'HIGH_GRADE'
        elif value in ['BBB+', 'BBB', 'BBB-']:
            return 'INVESTMENT_GRADE'
        elif value in ['BB+', 'BB', 'BB-', 'B+', 'B', 'B-']:
            return 'SUB_INVESTMENT_GRADE'
        elif value in ['CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D']:
            return 'HIGH_RISK'
        else:
            return value  # Return as-is if no mapping rule applies
            
    elif 'scenario' in template_col_lower:
        # Scenario mapping
        scenario_mapping = {
            'BASELINE': 'BASE',
            'OPTIMISTIC': 'OPTIMISTIC',
            'PESSIMISTIC': 'PESSIMISTIC',
            'ADVERSE': 'PESSIMISTIC',
            'STRESSED': 'PESSIMISTIC'
        }
        return scenario_mapping.get(value, value)
    
    else:
        # For other columns, return as-is
        return value
def map_pd_segments(simulation_df: pd.DataFrame,
                   template_data: Dict[str, pd.DataFrame], 
                   operation_type: cst.OperationType,
                   operation_status: cst.OperationStatus,
                   driver_mappings: Dict[str, str] = None,
                   default_values: Dict[str, str] = None) -> pd.DataFrame:
    """
    Map PD segments from simulation data to template data and extract PD values using flexible drivers.
    
    Args:
        simulation_df: DataFrame containing simulation data
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        driver_mappings: Dictionary mapping template driver columns to simulation data columns
                        e.g., {'SEGMENT': 'CALCULATION_RATING', 'SCENARIO': 'ECONOMIC_SCENARIO'}
                        If None, will try to auto-detect based on column names
        default_values: Dictionary of default values to use for each driver when no match is found
                       e.g., {'SEGMENT': 'INVESTMENT_GRADE', 'SCENARIO': 'BASE'}
        
    Returns:
        pd.DataFrame: DataFrame with mapped PD values per time step for each contract
    """
    if simulation_df is None or simulation_df.empty:
        logger.error("No simulation data available for PD segment mapping")
        return pd.DataFrame()
        
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    
    if not template_data or pd_template_sheet not in template_data:
        logger.error(f"PD template sheet '{pd_template_sheet}' not found in template data")
        return pd.DataFrame()
        
    # Get PD template data
    pd_template = template_data[pd_template_sheet]
    
    # Get driver columns and time step columns
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    time_step_columns = get_time_step_columns(pd_template)
    
    if not driver_columns:
        logger.error("No driver columns found in PD template")
        return pd.DataFrame()
        
    if not time_step_columns:
        logger.warning(f"No time step columns found in PD template sheet '{pd_template_sheet}'")
        return pd.DataFrame()
        
    logger.info(f"Found {len(driver_columns)} driver columns: {driver_columns}")
    logger.info(f"Found {len(time_step_columns)} time step columns: {time_step_columns}")
    
    # Set up driver mappings - auto-detect if not provided
    if driver_mappings is None:
        driver_mappings = auto_detect_driver_mappings(simulation_df, driver_columns)
        
    # Set up default values if not provided
    if default_values is None:
        default_values = get_default_values(template_data, operation_type, operation_status, driver_columns)
        
    logger.info(f"Using driver mappings: {driver_mappings}")
    logger.info(f"Using default values: {default_values}")
    
    # Validate that mapped columns exist in simulation data
    missing_columns = []
    for template_col, sim_col in driver_mappings.items():
        if sim_col and sim_col not in simulation_df.columns:
            missing_columns.append(sim_col)
            
    if missing_columns:
        logger.error(f"Missing columns in simulation data: {missing_columns}")
        return pd.DataFrame()
    
    # Create mapping dictionary: tuple of driver values -> PD values per time step
    pd_mapping = {}
    for _, row in pd_template.iterrows():
        # Create key tuple from all driver values
        key_values = []
        for driver_col in driver_columns:
            key_values.append(row[driver_col])
        key = tuple(key_values)
        
        # Extract PD values for this combination
        pd_values = [row[col] for col in time_step_columns]
        pd_mapping[key] = pd_values
        
    logger.info(f"Created PD mapping for {len(pd_mapping)} driver combinations")
    
    # Apply mapping to simulation data
    results = []
    unmapped_combinations = set()
    
    for idx, sim_row in simulation_df.iterrows():
        contract_id = sim_row.get('CONTRACT_ID', f'Contract_{idx}')
        
        # Create lookup key from simulation data
        lookup_values = []
        driver_info = {}
        
        for template_col in driver_columns:
            sim_col = driver_mappings.get(template_col)
            
            if sim_col and sim_col in sim_row:
                # Map simulation value to template value
                sim_value = sim_row[sim_col]
                mapped_value = map_simulation_value_to_template_value(
                    template_col, sim_value
                )
                lookup_values.append(mapped_value)
                driver_info[f'{template_col}_ORIGINAL'] = sim_value
                driver_info[f'{template_col}_MAPPED'] = mapped_value
            else:
                # Use default value
                default_val = default_values.get(template_col, 'DEFAULT')
                lookup_values.append(default_val)
                driver_info[f'{template_col}_ORIGINAL'] = None
                driver_info[f'{template_col}_MAPPED'] = default_val
        
        lookup_key = tuple(lookup_values)
        
        # Look up PD values
        if lookup_key in pd_mapping:
            pd_values = pd_mapping[lookup_key]
        else:
            pd_values = [np.nan] * len(time_step_columns)
            unmapped_combinations.add(str(lookup_key))
        
        # Create result row
        result_row = {
            'CONTRACT_ID': contract_id,
            **driver_info  # Add all driver information
        }
        
        # Add PD values for each time step
        for i, col in enumerate(time_step_columns):
            result_row[f'PD_{col}'] = pd_values[i] if i < len(pd_values) else np.nan
            
        results.append(result_row)
    
    # Log unmapped combinations
    if unmapped_combinations:
        logger.warning(f"Unmapped driver combinations: {unmapped_combinations}")
        
    result_df = pd.DataFrame(results)
    logger.info(f"Successfully mapped PD values for {len(result_df)} contracts")
    
    return result_df


# Legacy convenience functions for backward compatibility
def get_available_segments(template_data: Dict[str, pd.DataFrame],
                          operation_type: cst.OperationType,
                          operation_status: cst.OperationStatus) -> List[str]:
    """
    Get list of available PD segments from the template data.
    Legacy function for backward compatibility.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        List[str]: List of available segments in the PD template
    """
    # Try to find a segment-like column
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    segment_like_columns = [col for col in driver_columns 
                           if 'segment' in col.lower()]
    
    if segment_like_columns:
        return get_unique_values_for_driver(template_data, operation_type, operation_status, segment_like_columns[0])
    else:
        logger.warning("No segment-like column found. Use get_driver_columns() for flexible approach.")
        return []


def get_available_scenarios(template_data: Dict[str, pd.DataFrame],
                           operation_type: cst.OperationType,
                           operation_status: cst.OperationStatus) -> List[str]:
    """
    Get list of available scenarios from the template data.
    Legacy function for backward compatibility.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        List[str]: List of available scenarios in the PD template
    """
    # Try to find a scenario-like column
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    scenario_like_columns = [col for col in driver_columns 
                            if 'scenario' in col.lower()]
    
    if scenario_like_columns:
        return get_unique_values_for_driver(template_data, operation_type, operation_status, scenario_like_columns[0])
    else:
        logger.warning("No scenario-like column found. Use get_driver_columns() for flexible approach.")
        return []


def get_available_ratings(template_data: Dict[str, pd.DataFrame],
                         operation_type: cst.OperationType,
                         operation_status: cst.OperationStatus) -> List[str]:
    """
    Get list of available ratings from the template data.
    Legacy function for backward compatibility.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        
    Returns:
        List[str]: List of available ratings in the PD template
    """
    # Try to find a rating-like column
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    rating_like_columns = [col for col in driver_columns 
                          if 'rating' in col.lower()]
    
    if rating_like_columns:
        return get_unique_values_for_driver(template_data, operation_type, operation_status, rating_like_columns[0])
    else:
        logger.warning("No rating-like column found. Use get_driver_columns() for flexible approach.")
        return []


def map_pd_segments_legacy(simulation_df: pd.DataFrame,
                          template_data: Dict[str, pd.DataFrame],
                          operation_type: cst.OperationType,
                          operation_status: cst.OperationStatus,
                          segment_column: str = 'CALCULATION_RATING',
                          scenario: str = 'BASE',
                          default_segment: str = None) -> pd.DataFrame:
    """
    Legacy function for backward compatibility with the original API.
    
    Args:
        simulation_df: DataFrame containing simulation data
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        segment_column: Column name in simulation data containing the segment information
        scenario: Scenario to use for PD lookup (BASE, OPTIMISTIC, PESSIMISTIC)
        default_segment: Default segment to use if no match is found
        
    Returns:
        pd.DataFrame: DataFrame with mapped PD values per time step for each contract
    """
    # Convert legacy parameters to new flexible format
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    
    # Try to identify scenario and segment columns
    scenario_col = None
    segment_col = None
    
    for col in driver_columns:
        if 'scenario' in col.lower() and scenario_col is None:
            scenario_col = col
        if ('segment' in col.lower() or 'rating' in col.lower()) and segment_col is None:
            segment_col = col
    
    # Build driver mappings
    driver_mappings = {}
    default_values = {}
    
    if scenario_col:
        driver_mappings[scenario_col] = None  # Use default value
        default_values[scenario_col] = scenario
        
    if segment_col:
        driver_mappings[segment_col] = segment_column
        if default_segment:
            default_values[segment_col] = default_segment
    
    # Add other driver columns with auto-detection
    for col in driver_columns:
        if col not in driver_mappings:
            driver_mappings[col] = None  # Will auto-detect or use default
    
    # Call the new flexible function
    result_df = map_pd_segments(
        simulation_df=simulation_df,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        driver_mappings=driver_mappings,
        default_values=default_values
    )
    
    # Rename columns to match legacy format if possible
    if not result_df.empty:
        rename_mapping = {}
        for col in result_df.columns:
            if segment_col and f'{segment_col}_ORIGINAL' in col:
                rename_mapping[col] = 'SEGMENT_ORIGINAL'
            elif segment_col and f'{segment_col}_MAPPED' in col:
                rename_mapping[col] = 'SEGMENT_MAPPED'
            elif scenario_col and f'{scenario_col}_MAPPED' in col:
                rename_mapping[col] = 'SCENARIO'
        
        if rename_mapping:
            result_df = result_df.rename(columns=rename_mapping)
    
    return result_df


def get_pd_for_specific_contracts(simulation_df: pd.DataFrame,
                                 template_data: Dict[str, pd.DataFrame],
                                 operation_type: cst.OperationType,
                                 operation_status: cst.OperationStatus,
                                 contract_ids: List[str],
                                 driver_mappings: Dict[str, str] = None,
                                 default_values: Dict[str, str] = None) -> pd.DataFrame:
    """
    Get PD values for specific contracts using flexible driver mappings.
    
    Args:
        simulation_df: DataFrame containing simulation data
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        contract_ids: List of contract IDs to get PD values for
        driver_mappings: Dictionary mapping template driver columns to simulation columns
        default_values: Dictionary of default values for each driver
        
    Returns:
        pd.DataFrame: DataFrame with PD values for specified contracts
    """
    # Filter simulation data for specific contracts
    contract_filter = simulation_df['CONTRACT_ID'].isin(contract_ids)
    filtered_data = simulation_df[contract_filter].copy()
    
    if filtered_data.empty:
        logger.warning(f"No contracts found for IDs: {contract_ids}")
        return pd.DataFrame()
        
    # Get PD mapping for filtered contracts
    result_df = map_pd_segments(
        simulation_df=filtered_data,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        driver_mappings=driver_mappings,
        default_values=default_values
    )
    
    return result_df


def get_pd_summary_by_drivers(template_data: Dict[str, pd.DataFrame],
                             operation_type: cst.OperationType,
                             operation_status: cst.OperationStatus,
                             scenario: str = 'BASE') -> pd.DataFrame:
    """
    Get summary of PD values by driver combinations from the template data.
    
    Args:
        template_data: Dictionary containing template DataFrames by sheet name
        operation_type: Type of operation (NON_RETAIL, RETAIL)
        operation_status: Status of operation (PERFORMING, DEFAULTED)
        scenario: Scenario to use for PD lookup (if scenario column exists)
        
    Returns:
        pd.DataFrame: Summary of PD values by driver combinations
    """
    pd_template_sheet = _get_pd_template_sheet_name(operation_type, operation_status)
    
    if not template_data or pd_template_sheet not in template_data:
        logger.error(f"PD template sheet '{pd_template_sheet}' not found in template data")
        return pd.DataFrame()
        
    pd_template = template_data[pd_template_sheet]
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    
    # Check if there's a scenario column and filter if needed
    scenario_col = next((col for col in driver_columns if 'scenario' in col.lower()), None)
    
    if scenario_col:
        # Filter by scenario
        scenario_template = pd_template[pd_template[scenario_col].str.upper() == scenario.upper()].copy()
        if scenario_template.empty:
            logger.error(f"No data found for scenario '{scenario}' in PD template")
            return pd.DataFrame()
    else:
        scenario_template = pd_template.copy()
        
    # Get time step columns
    time_step_columns = get_time_step_columns(pd_template)
    
    # Select relevant columns (all driver columns + time step columns)
    summary_columns = driver_columns + time_step_columns
    available_columns = [col for col in summary_columns if col in scenario_template.columns]
    summary_df = scenario_template[available_columns].copy()
    
    # Sort by driver columns
    if driver_columns:
        sort_columns = [col for col in driver_columns if col in summary_df.columns]
        if sort_columns:
            summary_df = summary_df.sort_values(sort_columns).reset_index(drop=True)
    
    logger.info(f"Generated PD summary for {len(summary_df)} driver combinations")
    
    return summary_df


# Factory functions for convenience
def get_available_segments_for_operation(ecl_operation_data: cst.ECLOperationData) -> List[str]:
    """
    Get list of available PD segments from the template data for a specific operation.
    Factory function for convenience.
    
    Args:
        ecl_operation_data: ECL operation data containing simulation data and template data
        
    Returns:
        List[str]: List of available segments in the PD template
    """
    return get_available_segments(
        template_data=ecl_operation_data.template_data,
        operation_type=ecl_operation_data.operation_type,
        operation_status=ecl_operation_data.operation_status
    )


def get_available_scenarios_for_operation(ecl_operation_data: cst.ECLOperationData) -> List[str]:
    """
    Get list of available scenarios from the template data for a specific operation.
    Factory function for convenience.
    
    Args:
        ecl_operation_data: ECL operation data containing simulation data and template data
        
    Returns:
        List[str]: List of available scenarios in the PD template
    """
    return get_available_scenarios(
        template_data=ecl_operation_data.template_data,
        operation_type=ecl_operation_data.operation_type,
        operation_status=ecl_operation_data.operation_status
    )


def get_available_ratings_for_operation(ecl_operation_data: cst.ECLOperationData) -> List[str]:
    """
    Get list of available ratings from the template data for a specific operation.
    Factory function for convenience.
    
    Args:
        ecl_operation_data: ECL operation data containing simulation data and template data
        
    Returns:
        List[str]: List of available ratings in the PD template
    """
    return get_available_ratings(
        template_data=ecl_operation_data.template_data,
        operation_type=ecl_operation_data.operation_type,
        operation_status=ecl_operation_data.operation_status
    )


# Example usage functions
def get_pd_for_simulation_data(ecl_operation_data: cst.ECLOperationData,
                              driver_mappings: Dict[str, str] = None,
                              default_values: Dict[str, str] = None) -> pd.DataFrame:
    """
    Convenience function to get PD values for simulation data using flexible drivers.
    
    Args:
        ecl_operation_data: Container with operation details, simulation data, and template data
        driver_mappings: Dictionary mapping template driver columns to simulation columns
        default_values: Dictionary of default values for each driver
        
    Returns:
        pd.DataFrame: DataFrame with PD values mapped for all contracts
    """
    return map_pd_segments(
        simulation_df=ecl_operation_data.df,
        template_data=ecl_operation_data.template_data,
        operation_type=ecl_operation_data.operation_type,
        operation_status=ecl_operation_data.operation_status,
        driver_mappings=driver_mappings,
        default_values=default_values
    )


def get_pd_for_simulation_data_legacy(ecl_operation_data: cst.ECLOperationData,
                                     segment_column: str = 'CALCULATION_RATING',
                                     scenario: str = 'BASE',
                                     default_segment: str = None) -> pd.DataFrame:
    """
    Legacy convenience function for backward compatibility with the original API.
    
    Args:
        ecl_operation_data: Container with operation details, simulation data, and template data
        segment_column: Column name containing segment information
        scenario: Scenario to use for PD lookup
        default_segment: Default segment to use if no match is found
        
    Returns:
        pd.DataFrame: DataFrame with PD values mapped for all contracts
    """
    return map_pd_segments_legacy(
        simulation_df=ecl_operation_data.df,
        template_data=ecl_operation_data.template_data,
        operation_type=ecl_operation_data.operation_type,
        operation_status=ecl_operation_data.operation_status,
        segment_column=segment_column,
        scenario=scenario,
        default_segment=default_segment
    )


if __name__ == "__main__":
    # Example usage
    print("=== PD Segment Mapper Example ===")
    
    # This would typically be called with real ECLOperationData
    # For testing purposes, you would need to load actual data
    """
    # Example usage:
    
    # 1. Create ECL operation data with simulation data and template data
    ecl_data = cst.ECLOperationData(
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        template_file_path="path/to/template.xlsx",
        data_file_path="path/to/simulation_data.xlsx"
    )
    
    # Load simulation data and template data (using your existing loaders)
    # ecl_data.df = load_simulation_data(ecl_data)
    # ecl_data.template_data = load_template_data(ecl_data)
    
    # 2. Get available segments and scenarios using functional approach
    print("Available segments:", get_available_segments_for_operation(ecl_data))
    print("Available scenarios:", get_available_scenarios_for_operation(ecl_data))
    
    # 3. Map PD segments for all contracts using flexible drivers
    pd_results = get_pd_for_simulation_data(
        ecl_data,
        driver_mappings={'SEGMENT': 'CALCULATION_RATING', 'SCENARIO': None},
        default_values={'SCENARIO': 'BASE', 'SEGMENT': 'INVESTMENT_GRADE'}
    )
    
    # 4. Get PD values for specific contracts
    specific_pd = get_pd_for_specific_contracts(
        simulation_df=ecl_data.df,
        template_data=ecl_data.template_data,
        operation_type=ecl_data.operation_type,
        operation_status=ecl_data.operation_status,
        contract_ids=['C001', 'C002'],
        driver_mappings={'SCENARIO': None},
        default_values={'SCENARIO': 'OPTIMISTIC'}
    )
    
    # 5. Get PD summary by driver combinations
    pd_summary = get_pd_summary_by_drivers(
        template_data=ecl_data.template_data,
        operation_type=ecl_data.operation_type,
        operation_status=ecl_data.operation_status,
        scenario='BASE'
    )
    
    print(f"Mapped PD values for {len(pd_results)} contracts")
    """
    
    print("PD Segment Mapper module loaded successfully")
