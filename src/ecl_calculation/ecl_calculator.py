"""
Main ECL Calculator orchestrator that handles the complete ECL calculation workflow.

This class serves as the main entry point and orchestrates:
- Template import and validation
- Simulation data import and validation  
- ECL computation using appropriate strategy based on operation type and status
"""

# Global import
from src.core.librairies import *

# Local imports
from src.core import config as cst
from src.templates import template_loader as tpl
from src.data import data_loader as dl
from core.base_ecl_calculator import ECLCalculationInputs, ECLCalculationResults
from src.ecl_calculation.ecl_calculator_factory import create_ecl_calculator

logger = logging.getLogger(__name__)


class ECLCalculator:
    """
    Main class for ECL computation orchestration.

    The class handles:
    - Templates import and validation
    - Simulation data import and validation
    - ECL computation based on templates and simulation data using appropriate strategy
    """
    
    def __init__(self, operation_type: cst.OperationType, operation_status: cst.OperationStatus):
        """
        Initialize the ECL Calculator.
        
        Args:
            operation_type: Type of operation (RETAIL, NON_RETAIL)
            operation_status: Status of operation (PERFORMING, DEFAULTED)
        """
        self.operation_type = operation_type
        self.operation_status = operation_status
        self.logger = logging.getLogger(f"{__name__}.ECLCalculator")
        
        # Initialize components
        self.template_loader = None
        self.data_importer = None
        self.ecl_calculator_strategy = None
        
        # Data storage
        self.template_data = None
        self.simulation_data = None
        self.ecl_results = None
    
    def load_template(self, template_file_path: str) -> bool:
        """
        Load and validate template file.
        
        Args:
            template_file_path: Path to the template file
            
        Returns:
            bool: True if template loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading template for {self.operation_type.value} - {self.operation_status.value}")
            
            # Get template loader
            self.template_loader = tpl.template_loader(
                self.operation_type, 
                self.operation_status, 
                template_file_path
            )
            
            # Import template
            template_data = self.template_loader.template_importer()
            
            # Validate template
            validation_result = self.template_loader.validate_template(template_data)
            
            if not validation_result.is_valid:
                self.logger.error("Template validation failed:")
                for error in validation_result.errors:
                    self.logger.error(f"  - {error}")
                return False
            
            if validation_result.warnings:
                self.logger.warning("Template validation warnings:")
                for warning in validation_result.warnings:
                    self.logger.warning(f"  - {warning}")
            
            self.template_data = template_data.template
            self.logger.info("Template loaded and validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading template: {e}")
            return False
    
    def load_simulation_data(self, data_file_path: str) -> bool:
        """
        Load and validate simulation data.
        
        Args:
            data_file_path: Path to the simulation data file
            
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading simulation data from: {data_file_path}")
            
            # Get data importer
            self.data_importer = dl.get_importer(
                data_file_path, 
                self.operation_type, 
                self.operation_status
            )
            
            # Load data
            self.simulation_data = dl.data_loader(self.data_importer)
            
            self.logger.info(f"Simulation data loaded successfully. Shape: {self.simulation_data.shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading simulation data: {e}")
            return False
    
    def calculate_ecl(self, as_of_date: pd.Timestamp, scenarios: List[str]) -> ECLCalculationResults:
        """
        Calculate ECL using the appropriate strategy.
        
        Args:
            as_of_date: The calculation date
            scenarios: List of scenarios to calculate
            
        Returns:
            ECLCalculationResults: Complete ECL calculation results
            
        Raises:
            ValueError: If template or simulation data not loaded
        """
        if self.template_data is None:
            raise ValueError("Template data not loaded. Call load_template() first.")
        
        if self.simulation_data is None:
            raise ValueError("Simulation data not loaded. Call load_simulation_data() first.")
        
        try:
            self.logger.info(f"Starting ECL calculation for {self.operation_type.value} - {self.operation_status.value}")
            
            # Create ECL calculator strategy
            self.ecl_calculator_strategy = create_ecl_calculator(
                self.operation_type, 
                self.operation_status
            )
            
            # Prepare inputs
            calculation_inputs = ECLCalculationInputs(
                simulation_data=self.simulation_data,
                template_data=self.template_data,
                as_of_date=as_of_date,
                scenarios=scenarios,
                operation_type=self.operation_type,
                operation_status=self.operation_status
            )
            
            # Calculate ECL
            self.ecl_results = self.ecl_calculator_strategy.calculate_ecl(calculation_inputs)
            
            self.logger.info("ECL calculation completed successfully")
            return self.ecl_results
            
        except Exception as e:
            self.logger.error(f"Error during ECL calculation: {e}")
            raise
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the ECL calculation.
        
        Returns:
            Dictionary with calculation summary
        """
        if self.ecl_results is None:
            return {"status": "No calculation performed"}
        
        return {
            "operation_type": self.operation_type.value,
            "operation_status": self.operation_status.value,
            "calculator_used": self.ecl_calculator_strategy.__class__.__name__,
            "total_exposures": len(self.simulation_data),
            "template_sheets_used": list(self.template_data.keys()),
            "calculation_details": self.ecl_results.calculation_details
        }
    
    def export_results(self, output_path: str, format: str = 'excel') -> bool:
        """
        Export ECL calculation results to file.
        
        Args:
            output_path: Path where to save the results
            format: Export format ('excel', 'csv')
            
        Returns:
            bool: True if export successful, False otherwise
        """
        if self.ecl_results is None:
            self.logger.error("No ECL results to export. Run calculation first.")
            return False
        
        try:
            if format.lower() == 'excel':
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    self.ecl_results.ecl_by_exposure.to_excel(writer, sheet_name='ECL_by_Exposure', index=False)
                    self.ecl_results.ecl_summary.to_excel(writer, sheet_name='ECL_Summary', index=False)
                    self.ecl_results.residual_maturity.to_excel(writer, sheet_name='Residual_Maturity', index=False)
                    self.ecl_results.ead_amortization.to_excel(writer, sheet_name='EAD_Amortization', index=False)
                    
            elif format.lower() == 'csv':
                # Export main results to CSV
                base_path = output_path.replace('.csv', '')
                self.ecl_results.ecl_by_exposure.to_csv(f"{base_path}_ecl_by_exposure.csv", index=False)
                self.ecl_results.ecl_summary.to_csv(f"{base_path}_ecl_summary.csv", index=False)
            
            self.logger.info(f"ECL results exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            return False