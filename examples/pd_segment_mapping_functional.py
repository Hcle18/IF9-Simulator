"""
PD Segment Mapping Examples - Functional Approach

This module demonstrates how to use the functional approach for PD segment mapping
in the IFRS9 ECL calculation system. All functions work without classes.

Author: ECL Team
Date: 2024
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.core import config as cst
from src.ecl_calculation.get_terms import (
    get_driver_columns,
    get_unique_values_for_driver,
    map_pd_segments,
    map_pd_segments_legacy,
    get_pd_for_specific_contracts,
    get_pd_summary_by_drivers,
    auto_detect_driver_mappings,
    get_available_segments_for_operation,
    get_available_scenarios_for_operation,
    get_pd_for_simulation_data,
    get_pd_for_simulation_data_legacy
)


def create_sample_simulation_data() -> pd.DataFrame:
    """Create sample simulation data for testing."""
    np.random.seed(42)
    
    data = {
        'CONTRACT_ID': [f'C{str(i).zfill(3)}' for i in range(1, 101)],
        'CALCULATION_RATING': np.random.choice(['A', 'BBB', 'BB', 'B'], 100),
        'ECONOMIC_SCENARIO': np.random.choice(['BASE', 'OPTIMISTIC', 'PESSIMISTIC'], 100),
        'SECTOR': np.random.choice(['FINANCIAL', 'MANUFACTURING', 'RETAIL'], 100),
        'REGION': np.random.choice(['EUROPE', 'ASIA', 'AMERICA'], 100),
        'EXPOSURE_VALUE': np.random.uniform(1000, 100000, 100)
    }
    
    return pd.DataFrame(data)


def create_sample_template_data() -> Dict[str, pd.DataFrame]:
    """Create sample template data with flexible drivers."""
    # Create PD template with multiple drivers
    template_combinations = []
    
    # Generate all combinations of drivers
    segments = ['A', 'BBB', 'BB', 'B']
    scenarios = ['BASE', 'OPTIMISTIC', 'PESSIMISTIC']
    sectors = ['FINANCIAL', 'MANUFACTURING', 'RETAIL']
    
    for segment in segments:
        for scenario in scenarios:
            for sector in sectors:
                # Create PD values for 120 time steps (10 years monthly)
                base_pd = {'A': 0.001, 'BBB': 0.005, 'BB': 0.02, 'B': 0.05}[segment]
                scenario_mult = {'BASE': 1.0, 'OPTIMISTIC': 0.8, 'PESSIMISTIC': 1.5}[scenario]
                sector_mult = {'FINANCIAL': 1.2, 'MANUFACTURING': 1.0, 'RETAIL': 0.9}[sector]
                
                row = {
                    'SEGMENT': segment,
                    'SCENARIO': scenario,
                    'SECTOR': sector
                }
                
                # Add time step columns with term structure
                for i in range(1, 121):  # 120 months
                    term_mult = 1 + (i / 120) * 0.5  # Increasing with term
                    pd_value = base_pd * scenario_mult * sector_mult * term_mult
                    row[f'Time_step_{i}'] = round(pd_value, 6)
                
                template_combinations.append(row)
    
    pd_template = pd.DataFrame(template_combinations)
    
    return {
        'PD_NON_RETAIL_PERFORMING': pd_template
    }


def example_1_basic_functional_usage():
    """Example 1: Basic functional usage without classes."""
    print("=== Example 1: Basic Functional Usage ===")
    
    # Create sample data
    simulation_df = create_sample_simulation_data()
    template_data = create_sample_template_data()
    
    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING
    
    # 1. Get driver columns from template
    print("1. Getting driver columns...")
    driver_columns = get_driver_columns(template_data, operation_type, operation_status)
    print(f"Driver columns: {driver_columns}")
    
    # 2. Get unique values for each driver
    print("\n2. Getting unique values for each driver...")
    for driver in driver_columns:
        unique_values = get_unique_values_for_driver(template_data, operation_type, operation_status, driver)
        print(f"{driver}: {unique_values}")
    
    # 3. Auto-detect driver mappings
    print("\n3. Auto-detecting driver mappings...")
    auto_mappings = auto_detect_driver_mappings(simulation_df, template_data, operation_type, operation_status)
    print(f"Auto-detected mappings: {auto_mappings}")
    
    # 4. Map PD segments with flexible drivers
    print("\n4. Mapping PD segments...")
    driver_mappings = {
        'SEGMENT': 'CALCULATION_RATING',
        'SCENARIO': 'ECONOMIC_SCENARIO',
        'SECTOR': 'SECTOR'
    }
    
    result_df = map_pd_segments(
        simulation_df=simulation_df,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        driver_mappings=driver_mappings
    )
    
    print(f"Mapped PD values for {len(result_df)} contracts")
    print(f"Result columns: {result_df.columns.tolist()}")
    print(f"Sample result:\n{result_df.head()}")
    
    return result_df


def example_2_legacy_compatibility():
    """Example 2: Legacy compatibility function usage."""
    print("\n=== Example 2: Legacy Compatibility ===")
    
    # Create sample data
    simulation_df = create_sample_simulation_data()
    template_data = create_sample_template_data()
    
    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING
    
    # Use legacy function for backward compatibility
    result_df = map_pd_segments_legacy(
        simulation_df=simulation_df,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        segment_column='CALCULATION_RATING',
        scenario='BASE',
        default_segment='BBB'
    )
    
    print(f"Legacy mapping result for {len(result_df)} contracts")
    print(f"Result columns: {result_df.columns.tolist()}")
    
    return result_df


def example_3_specific_contracts():
    """Example 3: Get PD values for specific contracts."""
    print("\n=== Example 3: Specific Contracts ===")
    
    # Create sample data
    simulation_df = create_sample_simulation_data()
    template_data = create_sample_template_data()
    
    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING
    
    # Get PD values for specific contracts
    specific_contracts = ['C001', 'C002', 'C010', 'C020']
    
    driver_mappings = {
        'SEGMENT': 'CALCULATION_RATING',
        'SCENARIO': 'ECONOMIC_SCENARIO',
        'SECTOR': 'SECTOR'
    }
    
    result_df = get_pd_for_specific_contracts(
        simulation_df=simulation_df,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        contract_ids=specific_contracts,
        driver_mappings=driver_mappings
    )
    
    print(f"PD values for {len(result_df)} specific contracts")
    print(f"Result:\n{result_df}")
    
    return result_df


def example_4_pd_summary():
    """Example 4: Get PD summary by driver combinations."""
    print("\n=== Example 4: PD Summary by Drivers ===")
    
    # Create sample data
    template_data = create_sample_template_data()
    
    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING
    
    # Get PD summary for all driver combinations
    summary_df = get_pd_summary_by_drivers(
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        scenario='BASE'
    )
    
    print(f"PD summary for {len(summary_df)} driver combinations")
    print(f"Summary columns: {summary_df.columns.tolist()}")
    print(f"Sample summary:\n{summary_df.head()}")
    
    return summary_df


def example_5_convenience_functions():
    """Example 5: Using convenience functions with ECLOperationData."""
    print("\n=== Example 5: Convenience Functions ===")
    
    # Create sample data
    simulation_df = create_sample_simulation_data()
    template_data = create_sample_template_data()
    
    # Create ECL operation data container
    ecl_data = cst.ECLOperationData(
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING
    )
    ecl_data.df = simulation_df
    ecl_data.template_data = template_data
    
    # Use convenience functions
    print("Available segments:", get_available_segments_for_operation(ecl_data))
    print("Available scenarios:", get_available_scenarios_for_operation(ecl_data))
    
    # Get PD for all simulation data using flexible approach
    driver_mappings = {
        'SEGMENT': 'CALCULATION_RATING',
        'SCENARIO': 'ECONOMIC_SCENARIO',
        'SECTOR': 'SECTOR'
    }
    
    result_df = get_pd_for_simulation_data(
        ecl_operation_data=ecl_data,
        driver_mappings=driver_mappings
    )
    
    print(f"Convenience function mapped {len(result_df)} contracts")
    
    # Legacy convenience function
    legacy_result_df = get_pd_for_simulation_data_legacy(
        ecl_operation_data=ecl_data,
        segment_column='CALCULATION_RATING',
        scenario='OPTIMISTIC'
    )
    
    print(f"Legacy convenience function mapped {len(legacy_result_df)} contracts")
    
    return result_df, legacy_result_df


def example_6_custom_default_values():
    """Example 6: Using custom default values for unmapped drivers."""
    print("\n=== Example 6: Custom Default Values ===")
    
    # Create sample data with some missing values
    simulation_df = create_sample_simulation_data()
    # Remove SECTOR column to test default values
    simulation_df = simulation_df.drop('SECTOR', axis=1)
    
    template_data = create_sample_template_data()
    
    operation_type = cst.OperationType.NON_RETAIL
    operation_status = cst.OperationStatus.PERFORMING
    
    # Define mappings and custom default values
    driver_mappings = {
        'SEGMENT': 'CALCULATION_RATING',
        'SCENARIO': 'ECONOMIC_SCENARIO',
        'SECTOR': None  # No mapping - will use default
    }
    
    default_values = {
        'SEGMENT': 'BBB',  # Default if no match
        'SCENARIO': 'BASE',  # Default scenario
        'SECTOR': 'MANUFACTURING'  # Default sector since column is missing
    }
    
    result_df = map_pd_segments(
        simulation_df=simulation_df,
        template_data=template_data,
        operation_type=operation_type,
        operation_status=operation_status,
        driver_mappings=driver_mappings,
        default_values=default_values
    )
    
    print(f"Mapped {len(result_df)} contracts with custom defaults")
    print("Sample results with defaults:")
    print(result_df[['CONTRACT_ID', 'SEGMENT_MAPPED', 'SCENARIO_MAPPED', 'SECTOR_MAPPED']].head())
    
    return result_df


def main():
    """Run all examples to demonstrate functional PD mapping."""
    print("PD Segment Mapping - Functional Approach Examples")
    print("=" * 60)
    
    # Run all examples
    try:
        example_1_basic_functional_usage()
        example_2_legacy_compatibility()
        example_3_specific_contracts()
        example_4_pd_summary()
        example_5_convenience_functions()
        example_6_custom_default_values()
        
        print("\n" + "=" * 60)
        print("All functional examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
