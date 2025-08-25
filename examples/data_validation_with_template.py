"""
Example usage of NRS1S2DataValidator with template mapping integration.

This demonstrates how to use the validator with template data from template_loader.
"""

import pandas as pd
import logging
from typing import Dict

# Local imports
from src.core import config as cst
from src.core import base_data as bcls
from src.templates import template_loader as tpl
from src.data import data_loader as dl
from src.data.data_validator import NRS1S2DataValidator
from src.utils.logging_config import setup_logging

# Setup logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)


def example_non_retail_validation_with_template():
    """
    Complete example of Non-Retail S1+S2 data validation using template mapping.
    """
    logger.info("=" * 80)
    logger.info("Non-Retail S1+S2 Data Validation with Template Mapping Example")
    logger.info("=" * 80)
    
    try:
        # Step 1: Load template to get field mappings
        logger.info("Step 1: Loading template for field mappings...")
        
        template_path = "sample/templates/Template_outil_V1.xlsx"
        template_loader = tpl.template_loader(
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING,
            template_file_path=template_path
        )
        
        # Import and validate template
        template_data = template_loader.template_importer()
        template_validation = template_loader.validate_template(template_data)
        
        if not template_validation.is_valid:
            logger.error("Template validation failed:")
            for error in template_validation.errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("Template loaded and validated successfully")
        logger.info(f"Available template sheets: {list(template_data.template.keys())}")
        
        # Step 2: Load simulation data
        logger.info("Step 2: Loading simulation data...")
        
        data_path = "sample/data/sample_non_retail.zip"
        data_importer = dl.get_importer(
            file_path=data_path,
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING
        )
        
        raw_data = dl.data_loader(data_importer)
        logger.info(f"Raw data loaded. Shape: {raw_data.shape}")
        logger.info(f"Original columns: {list(raw_data.columns)}")
        
        # Create OperationData
        operation_data = bcls.OperationData(
            data=raw_data,
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING
        )
        
        # Step 3: Initialize validator with template data
        logger.info("Step 3: Initializing validator with template mapping...")
        
        validator = NRS1S2DataValidator(
            simu_data=operation_data,
            template_data=template_data.template  # Pass template data for mapping
        )
        
        # Check if field mapping was extracted successfully
        if validator.field_mapping_dict:
            logger.info(f"Field mapping extracted: {len(validator.field_mapping_dict)} mappings")
            logger.info("Sample mappings:")
            for i, (calc_field, sim_field) in enumerate(list(validator.field_mapping_dict.items())[:5]):
                logger.info(f"  {calc_field} -> {sim_field}")
        else:
            logger.warning("No field mapping extracted from template")
        
        # Step 4: Apply field mapping
        logger.info("Step 4: Applying field mapping...")
        
        mapped_df = validator.mapping_fields()
        logger.info(f"Mapped data shape: {mapped_df.shape}")
        logger.info(f"Mapped columns: {list(mapped_df.columns)}")
        
        # Update operation data with mapped fields
        operation_data.data = mapped_df
        
        # Step 5: Perform comprehensive validation
        logger.info("Step 5: Performing comprehensive data validation...")
        
        validated_data = validator.data_validator(operation_data)
        
        # Step 6: Display validation results
        logger.info("Step 6: Validation Results Summary")
        logger.info("-" * 50)
        
        validation_results = validated_data.validation_results
        summary = validation_results['validation_summary']
        
        logger.info(f"Total Records: {summary['total_records']}")
        logger.info(f"Data Quality Score: {summary['data_quality_score']:.2%}")
        logger.info(f"Quality Status: {summary['quality_status']}")
        logger.info(f"Total Errors: {summary['total_errors']}")
        logger.info(f"Total Warnings: {summary['total_warnings']}")
        
        # Display key metrics
        logger.info("Key Quality Metrics:")
        key_metrics = summary['key_metrics']
        for metric, value in key_metrics.items():
            logger.info(f"  - {metric}: {value}")
        
        # Display errors and warnings (first 5 of each)
        if validation_results['errors']:
            logger.info("Top Errors:")
            for error in validation_results['errors'][:5]:
                logger.error(f"  - {error}")
        
        if validation_results['warnings']:
            logger.info("Top Warnings:")
            for warning in validation_results['warnings'][:5]:
                logger.warning(f"  - {warning}")
        
        # Step 7: Export results if quality is acceptable
        if summary['data_quality_score'] >= 0.7:  # 70% threshold
            logger.info("Step 7: Exporting validated data...")
            
            # Export mapped and validated data
            output_path = "output/validated_non_retail_data.xlsx"
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                validated_data.data.to_excel(writer, sheet_name='Validated_Data', index=False)
                
                # Export validation summary
                summary_df = pd.DataFrame([summary])
                summary_df.to_excel(writer, sheet_name='Validation_Summary', index=False)
                
                # Export detailed metrics
                metrics_df = pd.DataFrame([validation_results['data_quality_metrics']])
                metrics_df.to_excel(writer, sheet_name='Quality_Metrics', index=False)
            
            logger.info(f"Validated data exported to: {output_path}")
        else:
            logger.warning("Data quality too low for export - address validation issues first")
        
        logger.info("Non-Retail S1+S2 validation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during validation process: {str(e)}")
        return False


def show_field_mapping_from_template(template_path: str):
    """
    Utility function to display the field mapping extracted from template.
    """
    logger.info("=" * 60)
    logger.info("Field Mapping Extraction from Template")
    logger.info("=" * 60)
    
    try:
        # Load template
        template_loader = tpl.template_loader(
            operation_type=cst.OperationType.NON_RETAIL,
            operation_status=cst.OperationStatus.PERFORMING,
            template_file_path=template_path
        )
        
        template_data = template_loader.template_importer()
        
        if "F1-Mapping fields Non Retail" not in template_data.template:
            logger.error("F1-Mapping fields Non Retail sheet not found in template")
            return
        
        mapping_df = template_data.template["F1-Mapping fields Non Retail"]
        logger.info(f"Mapping sheet shape: {mapping_df.shape}")
        logger.info(f"Mapping sheet columns: {list(mapping_df.columns)}")
        
        # Display the mapping table
        if all(col in mapping_df.columns for col in ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME"]):
            logger.info("Field Mappings from Template:")
            logger.info("-" * 80)
            logger.info(f"{'Calculator Field':<30} | {'Simulation Data Field':<30}")
            logger.info("-" * 80)
            
            for _, row in mapping_df.iterrows():
                calc_col = row.get("CALCULATOR_COLUMN_NAME", "")
                sim_col = row.get("SIMULATION_DATA_COLUMN_NAME", "")
                
                if pd.notna(calc_col) and pd.notna(sim_col):
                    logger.info(f"{str(calc_col):<30} | {str(sim_col):<30}")
        else:
            logger.error("Expected mapping columns not found in template")
            
    except Exception as e:
        logger.error(f"Error extracting field mapping: {str(e)}")


if __name__ == "__main__":
    """
    Run the complete example
    """
    # Create output directory
    from pathlib import Path
    Path("output").mkdir(exist_ok=True)
    
    # Show field mapping from template
    template_path = "sample/templates/Template_outil_V1.xlsx"
    show_field_mapping_from_template(template_path)
    
    # Run complete validation example
    example_non_retail_validation_with_template()
