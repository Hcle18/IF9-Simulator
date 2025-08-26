"""
Example demonstrating the flexible PD template functionality where any column
that doesn't start with "Time_step_" is considered as a driver.

This example shows:
1. How to work with flexible PD templates
2. Dynamic driver detection and mapping
3. Custom driver mappings
4. Backward compatibility with legacy APIs
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.data.data_loader import DataLoaderFactory
from src.templates.template_loader import TemplateLoaderFactory
from src.ecl_calculation.get_terms import create_pd_segment_mapper, get_pd_for_simulation_data, get_pd_for_simulation_data_legacy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_flexible_pd_template() -> pd.DataFrame:
    """
    Create a sample flexible PD template to demonstrate the functionality.
    This template has multiple driver columns and time step columns.
    """
    # Sample data with multiple drivers
    data = {
        # Driver columns (any column that doesn't start with "Time_step_")
        'SEGMENT': ['CORPORATE', 'CORPORATE', 'CORPORATE', 'RETAIL', 'RETAIL', 'RETAIL',
                   'SME', 'SME', 'SME', 'SOVEREIGN', 'SOVEREIGN', 'SOVEREIGN'],
        'SCENARIO': ['BASE', 'OPTIMISTIC', 'PESSIMISTIC', 'BASE', 'OPTIMISTIC', 'PESSIMISTIC',
                    'BASE', 'OPTIMISTIC', 'PESSIMISTIC', 'BASE', 'OPTIMISTIC', 'PESSIMISTIC'],
        'RATING_GRADE': ['IG', 'IG', 'IG', 'IG', 'IG', 'IG',
                        'SIG', 'SIG', 'SIG', 'IG', 'IG', 'IG'],
        'GEOGRAPHY': ['EUR', 'EUR', 'EUR', 'EUR', 'EUR', 'EUR',
                     'US', 'US', 'US', 'GLOBAL', 'GLOBAL', 'GLOBAL'],
        
        # Time step columns (columns starting with "Time_step_")
        'Time_step_1': [0.001, 0.0008, 0.0015, 0.002, 0.0015, 0.003,
                       0.005, 0.004, 0.008, 0.0005, 0.0003, 0.001],
        'Time_step_2': [0.0012, 0.001, 0.0018, 0.0025, 0.002, 0.0035,
                       0.006, 0.005, 0.01, 0.0006, 0.0004, 0.0012],
        'Time_step_3': [0.0015, 0.0012, 0.002, 0.003, 0.0025, 0.004,
                       0.007, 0.006, 0.012, 0.0008, 0.0005, 0.0015],
        'Time_step_4': [0.002, 0.0015, 0.0025, 0.004, 0.003, 0.005,
                       0.008, 0.007, 0.015, 0.001, 0.0006, 0.002],
        'Time_step_5': [0.0025, 0.002, 0.003, 0.005, 0.004, 0.006,
                       0.01, 0.008, 0.018, 0.0012, 0.0008, 0.0025]
    }
    
    return pd.DataFrame(data)


def create_sample_simulation_data() -> pd.DataFrame:
    """
    Create sample simulation data to demonstrate mapping.
    """
    data = {
        'CONTRACT_ID': ['C001', 'C002', 'C003', 'C004', 'C005'],
        'BUSINESS_SEGMENT': ['CORPORATE', 'RETAIL', 'SME', 'SOVEREIGN', 'CORPORATE'],
        'CALCULATION_RATING': ['IG', 'IG', 'SIG', 'IG', 'IG'],
        'REGION': ['EUR', 'EUR', 'US', 'GLOBAL', 'EUR'],
        'ECONOMIC_SCENARIO': ['BASE', 'OPTIMISTIC', 'BASE', 'PESSIMISTIC', 'BASE'],
        'EXPOSURE_END_DATE': ['2026-12-31', '2025-06-30', '2027-03-15', '2025-12-31', '2026-06-30'],
        'AS_OF_DATE': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01']
    }
    
    return pd.DataFrame(data)


def setup_sample_ecl_data() -> cst.ECLOperationData:
    """
    Set up sample ECL operation data for testing.
    """
    # Create ECL operation data container
    ecl_data = cst.ECLOperationData(
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        template_file_path="sample_template.xlsx",
        data_file_path="sample_data.xlsx"
    )
    
    # Add sample data
    ecl_data.df = create_sample_simulation_data()
    
    # Create template data structure
    ecl_data.template_data = {
        "F6-PD S1S2 Non Retail": create_sample_flexible_pd_template()
    }
    
    logger.info("Sample ECL data created with flexible PD template")
    return ecl_data


def demonstrate_flexible_driver_detection():
    """
    Demonstrate automatic detection of driver columns in flexible PD templates.
    """
    print("\n" + "="*80)
    print("FLEXIBLE DRIVER DETECTION DEMONSTRATION")
    print("="*80)
    
    try:
        # Setup sample data
        ecl_data = setup_sample_ecl_data()
        
        # Create PD mapper
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        # Demonstrate driver detection
        print("\n1. Driver Column Detection:")
        driver_columns = pd_mapper.get_driver_columns()
        print(f"   Detected driver columns: {driver_columns}")
        
        print("\n2. Time Step Column Detection:")
        pd_template = ecl_data.template_data["F6-PD S1S2 Non Retail"]
        time_step_columns = pd_mapper._get_time_step_columns(pd_template)
        print(f"   Detected time step columns: {time_step_columns}")
        
        print("\n3. Driver Values Analysis:")
        for driver_col in driver_columns:
            unique_values = pd_mapper.get_unique_values_for_driver(driver_col)
            print(f"   {driver_col}: {unique_values}")
        
        print("\n4. All Driver Combinations:")
        driver_combinations = pd_mapper.get_all_driver_combinations()
        print(f"   Total unique combinations: {len(driver_combinations)}")
        print("   Sample combinations:")
        print(driver_combinations.head().to_string(index=False))
        
    except Exception as e:
        logger.error(f"Error in driver detection demonstration: {e}")
        print(f"Error: {e}")


def demonstrate_automatic_mapping():
    """
    Demonstrate automatic mapping with driver auto-detection.
    """
    print("\n" + "="*80)
    print("AUTOMATIC DRIVER MAPPING DEMONSTRATION")
    print("="*80)
    
    try:
        # Setup sample data
        ecl_data = setup_sample_ecl_data()
        
        # Create PD mapper
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        print("\n1. Automatic Driver Mapping:")
        
        # Let the system auto-detect mappings
        pd_results = pd_mapper.map_pd_segments()
        
        if not pd_results.empty:
            print(f"   Successfully mapped {len(pd_results)} contracts")
            print("\n2. Mapping Results (all columns):")
            print(pd_results.to_string(index=False))
            
            print("\n3. PD Values Summary:")
            pd_columns = [col for col in pd_results.columns if col.startswith('PD_')]
            print(f"   PD columns found: {pd_columns}")
            
            if pd_columns:
                for pd_col in pd_columns[:3]:  # Show first 3 PD columns
                    pd_values = pd_results[pd_col].dropna()
                    if len(pd_values) > 0:
                        print(f"   {pd_col}: mean={pd_values.mean():.6f}, "
                              f"min={pd_values.min():.6f}, max={pd_values.max():.6f}")
        else:
            print("   No mapping results generated")
            
    except Exception as e:
        logger.error(f"Error in automatic mapping demonstration: {e}")
        print(f"Error: {e}")


def demonstrate_custom_driver_mapping():
    """
    Demonstrate custom driver mappings with specific business logic.
    """
    print("\n" + "="*80)
    print("CUSTOM DRIVER MAPPING DEMONSTRATION")
    print("="*80)
    
    try:
        # Setup sample data
        ecl_data = setup_sample_ecl_data()
        
        # Create PD mapper
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        print("\n1. Custom Driver Mappings:")
        
        # Define custom mappings between template drivers and simulation columns
        custom_driver_mappings = {
            'SEGMENT': 'BUSINESS_SEGMENT',        # Map SEGMENT to BUSINESS_SEGMENT
            'SCENARIO': 'ECONOMIC_SCENARIO',      # Map SCENARIO to ECONOMIC_SCENARIO
            'RATING_GRADE': 'CALCULATION_RATING', # Map RATING_GRADE to CALCULATION_RATING
            'GEOGRAPHY': 'REGION'                 # Map GEOGRAPHY to REGION
        }
        
        # Define custom default values
        custom_default_values = {
            'SEGMENT': 'CORPORATE',
            'SCENARIO': 'BASE',
            'RATING_GRADE': 'IG',
            'GEOGRAPHY': 'EUR'
        }
        
        print(f"   Driver mappings: {custom_driver_mappings}")
        print(f"   Default values: {custom_default_values}")
        
        # Apply custom mapping
        pd_results = pd_mapper.map_pd_segments(
            driver_mappings=custom_driver_mappings,
            default_values=custom_default_values
        )
        
        if not pd_results.empty:
            print(f"\n2. Custom Mapping Results:")
            print(f"   Successfully mapped {len(pd_results)} contracts")
            
            # Show driver mapping results
            driver_columns = ['CONTRACT_ID']
            for driver in custom_driver_mappings.keys():
                original_col = f'{driver}_ORIGINAL'
                mapped_col = f'{driver}_MAPPED'
                if original_col in pd_results.columns:
                    driver_columns.append(original_col)
                if mapped_col in pd_results.columns:
                    driver_columns.append(mapped_col)
            
            # Add first few PD columns
            pd_columns = [col for col in pd_results.columns if col.startswith('PD_')][:2]
            display_columns = driver_columns + pd_columns
            available_columns = [col for col in display_columns if col in pd_results.columns]
            
            print("\n   Driver Mapping Details:")
            print(pd_results[available_columns].to_string(index=False))
        else:
            print("   No custom mapping results generated")
            
    except Exception as e:
        logger.error(f"Error in custom mapping demonstration: {e}")
        print(f"Error: {e}")


def demonstrate_partial_driver_mapping():
    """
    Demonstrate partial driver mapping where some drivers use auto-detection.
    """
    print("\n" + "="*80)
    print("PARTIAL DRIVER MAPPING DEMONSTRATION")
    print("="*80)
    
    try:
        # Setup sample data
        ecl_data = setup_sample_ecl_data()
        
        # Create PD mapper
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        print("\n1. Partial Driver Mapping:")
        
        # Define partial mappings - only specify some drivers
        partial_driver_mappings = {
            'SEGMENT': 'BUSINESS_SEGMENT',    # Explicitly map this
            'SCENARIO': None,                 # Use default value
            'RATING_GRADE': 'CALCULATION_RATING',  # Explicitly map this
            'GEOGRAPHY': None                 # Use default value
        }
        
        # Define partial default values
        partial_default_values = {
            'SCENARIO': 'BASE',      # Force all contracts to BASE scenario
            'GEOGRAPHY': 'EUR'       # Force all contracts to EUR geography
        }
        
        print(f"   Partial mappings: {partial_driver_mappings}")
        print(f"   Partial defaults: {partial_default_values}")
        
        # Apply partial mapping
        pd_results = pd_mapper.map_pd_segments(
            driver_mappings=partial_driver_mappings,
            default_values=partial_default_values
        )
        
        if not pd_results.empty:
            print(f"\n2. Partial Mapping Results:")
            print(f"   Successfully mapped {len(pd_results)} contracts")
            
            # Show how defaults were applied
            print("\n   How defaults were applied:")
            scenario_mapped = pd_results['SCENARIO_MAPPED'].unique()
            geography_mapped = pd_results['GEOGRAPHY_MAPPED'].unique()
            print(f"   All contracts mapped to scenario: {scenario_mapped}")
            print(f"   All contracts mapped to geography: {geography_mapped}")
            
            # Show sample results
            sample_columns = ['CONTRACT_ID', 'SEGMENT_ORIGINAL', 'SEGMENT_MAPPED', 
                            'SCENARIO_MAPPED', 'RATING_GRADE_ORIGINAL', 'RATING_GRADE_MAPPED']
            available_sample_columns = [col for col in sample_columns if col in pd_results.columns]
            print(f"\n   Sample mapping results:")
            print(pd_results[available_sample_columns].to_string(index=False))
        else:
            print("   No partial mapping results generated")
            
    except Exception as e:
        logger.error(f"Error in partial mapping demonstration: {e}")
        print(f"Error: {e}")


def demonstrate_backward_compatibility():
    """
    Demonstrate backward compatibility with the legacy API.
    """
    print("\n" + "="*80)
    print("BACKWARD COMPATIBILITY DEMONSTRATION")
    print("="*80)
    
    try:
        # Setup sample data
        ecl_data = setup_sample_ecl_data()
        
        print("\n1. Using Legacy API:")
        
        # Use legacy convenience function
        pd_results_legacy = get_pd_for_simulation_data_legacy(
            ecl_operation_data=ecl_data,
            segment_column='CALCULATION_RATING',
            scenario='BASE',
            default_segment='IG'
        )
        
        if not pd_results_legacy.empty:
            print(f"   Legacy API mapped {len(pd_results_legacy)} contracts")
            
            # Show legacy format results
            legacy_columns = ['CONTRACT_ID', 'SEGMENT_ORIGINAL', 'SEGMENT_MAPPED', 'SCENARIO']
            pd_columns = [col for col in pd_results_legacy.columns if col.startswith('PD_')][:2]
            display_columns = legacy_columns + pd_columns
            available_columns = [col for col in display_columns if col in pd_results_legacy.columns]
            
            print("   Legacy format results:")
            print(pd_results_legacy[available_columns].to_string(index=False))
        
        print("\n2. Using New Flexible API:")
        
        # Use new flexible API
        pd_results_new = get_pd_for_simulation_data(
            ecl_operation_data=ecl_data,
            driver_mappings={'SEGMENT': 'BUSINESS_SEGMENT', 'SCENARIO': None},
            default_values={'SCENARIO': 'BASE'}
        )
        
        if not pd_results_new.empty:
            print(f"   New API mapped {len(pd_results_new)} contracts")
            print("   New flexible format provides more detailed driver information")
        
        print("\n3. Comparison:")
        print(f"   Legacy API results: {len(pd_results_legacy)} contracts")
        print(f"   New API results: {len(pd_results_new)} contracts")
        print("   Both APIs can work with the same flexible PD template!")
        
    except Exception as e:
        logger.error(f"Error in backward compatibility demonstration: {e}")
        print(f"Error: {e}")


def main():
    """
    Main function to run all flexible PD template demonstrations.
    """
    print("FLEXIBLE PD TEMPLATE DEMONSTRATIONS")
    print("=" * 80)
    print("Demonstrating how any column not starting with 'Time_step_' can be a driver")
    print("=" * 80)
    
    try:
        # Run all demonstrations
        demonstrate_flexible_driver_detection()
        demonstrate_automatic_mapping()
        demonstrate_custom_driver_mapping()
        demonstrate_partial_driver_mapping()
        demonstrate_backward_compatibility()
        
        print("\n" + "="*80)
        print("ALL FLEXIBLE PD TEMPLATE DEMONSTRATIONS COMPLETED")
        print("="*80)
        
        print("\nKey Features Demonstrated:")
        print("✓ Automatic detection of driver columns (non-Time_step_ columns)")
        print("✓ Flexible mapping between template drivers and simulation data")
        print("✓ Support for multiple driver types (segment, scenario, rating, geography, etc.)")
        print("✓ Auto-detection of column mappings based on naming patterns")
        print("✓ Custom driver mappings for specific business logic")
        print("✓ Partial mappings with default values")
        print("✓ Backward compatibility with legacy APIs")
        print("✓ Support for any number of driver combinations")
        
    except KeyboardInterrupt:
        print("\nDemonstration interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nUnexpected error occurred: {e}")


if __name__ == "__main__":
    main()
