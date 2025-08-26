"""
Complete example demonstrating PD segment mapping integration with ECL calculation.

This example shows the full workflow:
1. Load simulation data and template data
2. Map PD segments between simulation and template data
3. Extract PD values for each time step
4. Create expanded dataset for ECL calculation
5. Validate and analyze results
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
from src.ecl_calculation.ecl_calculator_with_pd import create_ecl_calculator_with_pd
from src.ecl_calculation.get_terms import create_pd_segment_mapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_ecl_operation_data() -> cst.ECLOperationData:
    """
    Set up ECL operation data with paths to sample files.
    
    Returns:
        cst.ECLOperationData: Configured operation data container
    """
    # Define paths to sample files
    template_path = project_root / "sample" / "templates" / "Template_outil_V1.xlsx"
    data_path = project_root / "sample" / "data" / "sample_non_retail.xlsx"
    
    # Create ECL operation data container
    ecl_data = cst.ECLOperationData(
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        template_file_path=str(template_path),
        data_file_path=str(data_path)
    )
    
    logger.info(f"ECL Operation Data configured:")
    logger.info(f"  Operation Type: {ecl_data.operation_type.value}")
    logger.info(f"  Operation Status: {ecl_data.operation_status.value}")
    logger.info(f"  Template File: {ecl_data.template_file_path}")
    logger.info(f"  Data File: {ecl_data.data_file_path}")
    
    return ecl_data


def load_all_data(ecl_data: cst.ECLOperationData) -> cst.ECLOperationData:
    """
    Load both simulation data and template data.
    
    Args:
        ecl_data: ECL operation data container
        
    Returns:
        cst.ECLOperationData: Container with loaded data
    """
    try:
        # Load simulation data
        logger.info("Loading simulation data...")
        data_loader = DataLoaderFactory.get_data_loader(ecl_data)
        ecl_data.df = data_loader.load_data()
        
        if ecl_data.df is not None:
            logger.info(f"Loaded simulation data: {len(ecl_data.df)} records")
            logger.info(f"Simulation data columns: {list(ecl_data.df.columns)}")
        else:
            logger.error("Failed to load simulation data")
            return ecl_data
        
        # Load template data
        logger.info("Loading template data...")
        template_loader = TemplateLoaderFactory.get_template_loader(ecl_data)
        template_loader.import_template()
        
        if ecl_data.template_data:
            logger.info(f"Loaded template data: {len(ecl_data.template_data)} sheets")
            logger.info(f"Template sheets: {list(ecl_data.template_data.keys())}")
        else:
            logger.error("Failed to load template data")
            return ecl_data
        
        return ecl_data
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


def demonstrate_pd_mapping_workflow(ecl_data: cst.ECLOperationData):
    """
    Demonstrate the complete PD mapping workflow.
    
    Args:
        ecl_data: ECL operation data container with loaded data
    """
    print("\n" + "="*80)
    print("PD MAPPING WORKFLOW DEMONSTRATION")
    print("="*80)
    
    try:
        # Step 1: Create PD segment mapper
        logger.info("Step 1: Creating PD segment mapper...")
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        # Explore available segments and scenarios
        print(f"\nAvailable PD Segments: {pd_mapper.get_available_segments()}")
        print(f"Available Scenarios: {pd_mapper.get_available_scenarios()}")
        
        # Step 2: Map PD segments
        logger.info("Step 2: Mapping PD segments...")
        pd_results = pd_mapper.map_pd_segments(
            segment_column='CALCULATION_RATING',
            scenario='BASE',
            default_segment='INVESTMENT_GRADE'
        )
        
        if not pd_results.empty:
            print(f"\nPD Mapping Results: {len(pd_results)} contracts mapped")
            
            # Show sample results
            print("\nSample PD mapping results (first 3 rows):")
            display_columns = ['CONTRACT_ID', 'SEGMENT_ORIGINAL', 'SEGMENT_MAPPED', 'RATING', 'SCENARIO']
            pd_columns = [col for col in pd_results.columns if col.startswith('PD_')][:3]
            sample_columns = display_columns + pd_columns
            available_columns = [col for col in sample_columns if col in pd_results.columns]
            print(pd_results[available_columns].head(3).to_string(index=False))
            
            # Show PD statistics
            pd_columns_all = [col for col in pd_results.columns if col.startswith('PD_')]
            print(f"\nTotal PD time step columns: {len(pd_columns_all)}")
            
            if pd_columns_all:
                first_pd_col = pd_columns_all[0]
                pd_values = pd_results[first_pd_col].dropna()
                if len(pd_values) > 0:
                    print(f"Statistics for {first_pd_col}:")
                    print(f"  Count: {len(pd_values)}")
                    print(f"  Mean: {pd_values.mean():.6f}")
                    print(f"  Min: {pd_values.min():.6f}")
                    print(f"  Max: {pd_values.max():.6f}")
        else:
            print("No PD mapping results generated")
            
    except Exception as e:
        logger.error(f"Error in PD mapping workflow: {e}")
        print(f"Error: {e}")


def demonstrate_ecl_calculator_with_pd(ecl_data: cst.ECLOperationData):
    """
    Demonstrate the enhanced ECL calculator with PD mapping.
    
    Args:
        ecl_data: ECL operation data container with loaded data
    """
    print("\n" + "="*80)
    print("ECL CALCULATOR WITH PD MAPPING DEMONSTRATION")
    print("="*80)
    
    try:
        # Create enhanced ECL calculator
        logger.info("Creating enhanced ECL calculator with PD mapping...")
        ecl_calculator = create_ecl_calculator_with_pd(ecl_data)
        
        # Step 1: Validate PD mapping
        logger.info("Step 1: Validating PD mapping...")
        validation_results = ecl_calculator.validate_pd_mapping(
            segment_column='CALCULATION_RATING',
            scenario='BASE'
        )
        
        print("\nValidation Results:")
        if validation_results['errors']:
            print(f"  Errors: {validation_results['errors']}")
        if validation_results['warnings']:
            print(f"  Warnings: {validation_results['warnings']}")
        if validation_results['info']:
            print(f"  Info: {validation_results['info']}")
        
        # Step 2: Get PD statistics
        logger.info("Step 2: Getting PD statistics...")
        pd_stats = ecl_calculator.get_pd_statistics(
            segment_column='CALCULATION_RATING',
            scenario='BASE'
        )
        
        if pd_stats:
            print(f"\nPD Statistics Summary:")
            if 'overall' in pd_stats:
                overall = pd_stats['overall']
                print(f"  Total PD values: {overall['total_values']}")
                print(f"  Overall mean PD: {overall['mean']:.6f}")
                print(f"  Overall PD range: {overall['min']:.6f} - {overall['max']:.6f}")
            
            if 'by_segment' in pd_stats:
                print(f"\nPD by Segment:")
                for segment, stats in pd_stats['by_segment'].items():
                    print(f"  {segment}: {stats['contracts']} contracts, "
                          f"mean PD: {stats['mean_pd']:.6f}")
        
        # Step 3: Calculate ECL with PD mapping (for Non-Retail)
        if isinstance(ecl_calculator, type(ecl_calculator)) and hasattr(ecl_calculator, 'calculate_ecl_with_pd'):
            logger.info("Step 3: Calculating ECL with PD mapping...")
            expanded_dataset = ecl_calculator.calculate_ecl_with_pd(
                segment_column='CALCULATION_RATING',
                scenario='BASE',
                default_segment='INVESTMENT_GRADE'
            )
            
            if not expanded_dataset.empty:
                print(f"\nExpanded Dataset for ECL Calculation:")
                print(f"  Total rows: {len(expanded_dataset)}")
                print(f"  Unique contracts: {expanded_dataset['CONTRACT_ID'].nunique()}")
                print(f"  Average time steps per contract: {len(expanded_dataset) / expanded_dataset['CONTRACT_ID'].nunique():.1f}")
                
                # Show sample of expanded dataset
                print(f"\nSample of expanded dataset (first 5 rows):")
                sample_columns = ['CONTRACT_ID', 'TIME_STEP', 'TIME_STEP_MONTHS', 'PD_VALUE', 'SEGMENT_MAPPED']
                available_sample_columns = [col for col in sample_columns if col in expanded_dataset.columns]
                print(expanded_dataset[available_sample_columns].head().to_string(index=False))
                
                # Show time step distribution
                if 'TIME_STEP' in expanded_dataset.columns:
                    time_step_counts = expanded_dataset['TIME_STEP'].value_counts().sort_index()
                    print(f"\nTime Step Distribution:")
                    for step, count in time_step_counts.head(10).items():
                        print(f"  Step {step}: {count} records")
                        
            else:
                print("No expanded dataset generated")
        else:
            print("Advanced ECL calculation not available for this operation type")
            
    except Exception as e:
        logger.error(f"Error in ECL calculator demonstration: {e}")
        print(f"Error: {e}")


def demonstrate_scenario_comparison(ecl_data: cst.ECLOperationData):
    """
    Demonstrate comparing PD values across different scenarios.
    
    Args:
        ecl_data: ECL operation data container with loaded data
    """
    print("\n" + "="*80)
    print("SCENARIO COMPARISON DEMONSTRATION")
    print("="*80)
    
    try:
        # Create PD mapper
        pd_mapper = create_pd_segment_mapper(ecl_data)
        
        # Get available scenarios
        available_scenarios = pd_mapper.get_available_scenarios()
        print(f"Available scenarios for comparison: {available_scenarios}")
        
        scenarios_to_compare = ['BASE', 'OPTIMISTIC', 'PESSIMISTIC']
        scenario_results = {}
        
        # Map PD for each scenario
        for scenario in scenarios_to_compare:
            if scenario.upper() in [s.upper() for s in available_scenarios]:
                logger.info(f"Mapping PD for scenario: {scenario}")
                
                pd_results = pd_mapper.map_pd_segments(
                    segment_column='CALCULATION_RATING',
                    scenario=scenario,
                    default_segment='INVESTMENT_GRADE'
                )
                
                if not pd_results.empty:
                    # Get PD columns and calculate statistics
                    pd_columns = [col for col in pd_results.columns if col.startswith('PD_')]
                    if pd_columns:
                        first_pd_col = pd_columns[0]
                        pd_values = pd_results[first_pd_col].dropna()
                        
                        scenario_results[scenario] = {
                            'contracts': len(pd_results),
                            'mean_pd': pd_values.mean() if len(pd_values) > 0 else np.nan,
                            'min_pd': pd_values.min() if len(pd_values) > 0 else np.nan,
                            'max_pd': pd_values.max() if len(pd_values) > 0 else np.nan
                        }
                else:
                    scenario_results[scenario] = {'contracts': 0, 'mean_pd': np.nan, 'min_pd': np.nan, 'max_pd': np.nan}
            else:
                print(f"Scenario '{scenario}' not available in template")
        
        # Display comparison
        if scenario_results:
            print(f"\nScenario Comparison (first time step):")
            print("-" * 60)
            print(f"{'Scenario':<12} {'Contracts':<10} {'Mean PD':<12} {'Min PD':<12} {'Max PD':<12}")
            print("-" * 60)
            
            for scenario, stats in scenario_results.items():
                mean_str = f"{stats['mean_pd']:.6f}" if not np.isnan(stats['mean_pd']) else "N/A"
                min_str = f"{stats['min_pd']:.6f}" if not np.isnan(stats['min_pd']) else "N/A"
                max_str = f"{stats['max_pd']:.6f}" if not np.isnan(stats['max_pd']) else "N/A"
                
                print(f"{scenario:<12} {stats['contracts']:<10} {mean_str:<12} {min_str:<12} {max_str:<12}")
        
    except Exception as e:
        logger.error(f"Error in scenario comparison: {e}")
        print(f"Error: {e}")


def main():
    """
    Main function to run the complete PD mapping workflow demonstration.
    """
    print("IFRS9 ECL CALCULATION WITH PD SEGMENT MAPPING")
    print("=" * 80)
    print("Complete workflow demonstration")
    print("=" * 80)
    
    try:
        # Step 1: Setup ECL operation data
        logger.info("Setting up ECL operation data...")
        ecl_data = setup_ecl_operation_data()
        
        # Step 2: Load all required data
        logger.info("Loading simulation and template data...")
        ecl_data = load_all_data(ecl_data)
        
        # Check if data was loaded successfully
        if ecl_data.df is None or ecl_data.template_data is None:
            print("Failed to load required data. Please check file paths and data availability.")
            return
        
        # Step 3: Demonstrate PD mapping workflow
        demonstrate_pd_mapping_workflow(ecl_data)
        
        # Step 4: Demonstrate enhanced ECL calculator
        demonstrate_ecl_calculator_with_pd(ecl_data)
        
        # Step 5: Demonstrate scenario comparison
        demonstrate_scenario_comparison(ecl_data)
        
        print("\n" + "="*80)
        print("COMPLETE WORKFLOW DEMONSTRATION FINISHED")
        print("="*80)
        print("\nSummary of what was demonstrated:")
        print("✓ ECL operation data setup and configuration")
        print("✓ Simulation and template data loading")
        print("✓ PD segment mapping between simulation and template data")
        print("✓ PD values extraction for different time steps")
        print("✓ Enhanced ECL calculator with integrated PD mapping")
        print("✓ Validation and statistics of PD mapping results")
        print("✓ Scenario comparison across different economic scenarios")
        print("✓ Expanded dataset creation for ECL calculation")
        
    except FileNotFoundError as e:
        logger.error(f"Required files not found: {e}")
        print(f"\nError: Required sample files not found.")
        print("Please ensure the following files exist:")
        print("- sample/templates/Template_outil_V1.xlsx")
        print("- sample/data/sample_non_retail.xlsx")
        
    except KeyboardInterrupt:
        print("\nDemonstration interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nUnexpected error occurred: {e}")


if __name__ == "__main__":
    main()
