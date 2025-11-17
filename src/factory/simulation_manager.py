"""
Simulation Manager for handling multiple ECL simulations with shared data optimization.

This module provides a manager class that allows running multiple simulations
while intelligently sharing data loading steps when simulations use the same input data.
"""

from src.core.librairies import *
from src.core import config as cst
from src.factory import operation_factory as opf
from src.utils import get_data_identifier

logger = logging.getLogger(__name__)


@dataclass
class SharedDataContext:
    """
    Context for shared data between simulations.
    
    Attributes:
        data_identifier: Identifier for the data (e.g., uploaded file name)
        data_file_path: Path to the data file
        list_jarvis_file_path: List of jarvis parameter file paths (can be empty)
        df: Loaded and processed DataFrame
        simulations: List of simulation names using this data
        is_loaded: Whether data has been loaded
        is_mapped: Whether data has been mapped
        is_validated: Whether data has been validated
    """
    data_identifier: str
    data_file_path: Any
    list_jarvis_file_path: List[Any] = field(default_factory=list)
    df: pd.DataFrame = None
    simulations: List[str] = field(default_factory=list)
    is_loaded: bool = False
    is_mapped: bool = False
    is_validated: bool = False

class SimulationManager:
    """
    Manager for handling multiple ECL simulations with shared data optimization.
    
    This class allows running multiple simulations while avoiding redundant
    data loading, mapping, and validation steps when simulations share the same input data.

    """
    
    def __init__(self):
        """
        Initialize the SimulationManager.
        
        Simulations are grouped by data identifier and jarvis parameters.
        Simulations with the same data_identifier AND list_jarvis_file_path share the loaded data.
        """
        self.simulations: Dict[str, opf.OperationFactory] = {}
        self.shared_data_contexts: Dict[str, SharedDataContext] = {}  # Key = sharing_key (data_id + jarvis)
        self._prepared_simulations: set = set()  # Track which simulations are prepared
        self._temp_files_cache: Dict[str, str] = {}  # Cache: original_name -> temp_path
        
        logger.info("SimulationManager initialized")
    
    def add_simulation(
        self,
        simulation_name: str,
        operation_type: cst.OperationType,
        operation_status: cst.OperationStatus,
        data_path: Any,
        template_path: Any,
        list_jarvis_file_path: Optional[List[Any]] = None
    ) -> None:
        """
        Add a simulation to the manager using individual parameters.
        
        Accepts both file paths (str) and Streamlit UploadedFile objects.
        Simulations with the same data_identifier AND list_jarvis_file_path will share loaded data.

        """
        # Check for duplicate simulation name
        if simulation_name in self.simulations:
            raise ValueError(f"Simulation '{simulation_name}' already exists")
        
        data_identifier = get_data_identifier(data_path)

        # Process jarvis files (optional)
        if list_jarvis_file_path is None:
            list_jarvis_file_path = []
        
        jarvis_paths = []
        for jarvis_file in list_jarvis_file_path:
            jarvis_path = get_data_identifier(jarvis_file)
            jarvis_paths.append(jarvis_path)
                
        # Create sharing key: combine data_identifier + sorted jarvis file paths
        if jarvis_paths:
            jarvis_key = "|".join(sorted([p for p in jarvis_paths]))
            sharing_key = f"{data_identifier}::{jarvis_key}"
        else:
            # No jarvis files - use only data_identifier
            sharing_key = f"{data_identifier}::NO_JARVIS"
        
        # Create the OperationFactory (without loading data yet)
        factory = opf.OperationFactory(
            operation_type=operation_type,
            operation_status=operation_status,
            data_file_path=data_path,
            template_file_path=template_path,
            list_jarvis_file_paths=jarvis_paths,
            simulation_name=simulation_name
        )
        
        # Store the factory
        self.simulations[simulation_name] = factory
        
        # Track shared data context using sharing_key
        if sharing_key not in self.shared_data_contexts:
            self.shared_data_contexts[sharing_key] = SharedDataContext(
                data_identifier=data_identifier,
                data_file_path=data_path,
                list_jarvis_file_path=jarvis_paths,
                simulations=[]
            )
        
        self.shared_data_contexts[sharing_key].simulations.append(simulation_name)
    
    def _prepare_shared_data(
        self,
        sharing_key: str,
        operation_type: cst.OperationType,
        operation_status: cst.OperationStatus
    ) -> pd.DataFrame:
        """
        Prepare shared data by loading, mapping, and validating once.
        
        Args:
            sharing_key: Key to the shared data context (data_identifier::jarvis_key)
            operation_type: Type of operation (for data loading config)
            operation_status: Status of operation (for data loading config)
            
        Returns:
            Prepared DataFrame
        """
        context = self.shared_data_contexts[sharing_key]
        
        if context.is_loaded and context.is_mapped and context.is_validated:
            logger.info(f"Using cached data for '{context.data_identifier}'")
            return context.df.copy()

        # Create a temporary OperationFactory to load and process data
        temp_factory = opf.OperationFactory(
            operation_type=operation_type,
            operation_status=operation_status,
            data_file_path=context.data_file_path,
            template_file_path=None,  # No template needed for shared data loading
            list_jarvis_file_paths=context.list_jarvis_file_path,
            simulation_name="_temp_data_loader"
        )
        
        # Load data
        if not context.is_loaded:
            logger.info(f"Loading data from '{context.data_file_path}'...")
            temp_factory.load_data()
            context.is_loaded = True
            logger.info(f"Data loaded. Shape: {temp_factory.ecl_operation_data.df.shape}")
        
        # Map fields
        if not context.is_mapped:
            logger.info("Mapping data fields...")
            temp_factory.data_mapping_fields()
            context.is_mapped = True
            logger.info("Data fields mapped")
        
        # Validate data
        if not context.is_validated:
            logger.info("Validating data...")
            temp_factory.validate_data()
            context.is_validated = True
            logger.info("Data validated")
        
        # Store the processed DataFrame
        context.df = temp_factory.ecl_operation_data.df.copy()
        
        logger.info(f"Shared data prepared successfully. Shape: {context.df.shape}")
        
        return context.df.copy()
    
    def prepare_simulation(self, simulation_name: str) -> opf.OperationFactory:
        """
        Prepare a single simulation by name.
        
        Args:
            simulation_name: Name of the simulation to prepare
            
        Returns:
            OperationFactory instance ready for calculation
            
        Raises:
            ValueError: If simulation name doesn't exist
        """
        if simulation_name not in self.simulations:
            raise ValueError(f"Simulation '{simulation_name}' not found")
        
        if simulation_name in self._prepared_simulations:
            logger.info(f"Simulation '{simulation_name}' already prepared")
            return self.simulations[simulation_name]
        
        factory = self.simulations[simulation_name]
        
        logger.info(f"Preparing simulation '{simulation_name}'...")
        
        # Import and validate templates (always simulation-specific)
        logger.info(f"[{simulation_name}] Importing templates...")
        factory.import_templates()
        factory.validate_templates()
        
        # Find which data context this simulation belongs to
        sharing_key = None
        for key, context in self.shared_data_contexts.items():
            if simulation_name in context.simulations:
                sharing_key = key
                break
        
        if sharing_key is None:
            raise ValueError(f"Could not find data context for simulation '{simulation_name}'")
        
        context = self.shared_data_contexts[sharing_key]
        
        # Check if data is shared
        if len(context.simulations) > 1:
            logger.info(
                f"[{simulation_name}] Using shared data optimization for '{context.data_identifier}' "
                f"({len(context.simulations)} simulations share this data+params)"
            )
        
        # Prepare shared data if not already done
        prepared_df = self._prepare_shared_data(
            sharing_key=sharing_key,
            operation_type=factory.ecl_operation_data.operation_type,
            operation_status=factory.ecl_operation_data.operation_status
        )
        
        # Inject the prepared data into the factory
        factory.ecl_operation_data.df = prepared_df
        
        logger.info(f"[{simulation_name}] Data injected. Shape: {prepared_df.shape}")
        
        # Mark as prepared
        self._prepared_simulations.add(simulation_name)
        
        logger.info(f"Simulation '{simulation_name}' prepared successfully")
        
        return factory
    
    def prepare_all_simulations(self) -> Dict[str, opf.OperationFactory]:
        """
        Prepare all simulations efficiently.
        
        This method optimizes data loading by grouping simulations
        that share the same data file.
        
        Returns:
            Dictionary mapping simulation names to their OperationFactory instances
        """
        logger.info(f"Preparing {len(self.simulations)} simulation(s)...")
               
        # Prepare each simulation
        for sim_name in self.simulations.keys():
            self.prepare_simulation(sim_name)
        
        logger.info("All simulations prepared successfully")
        
        return self.simulations
    
    def get_simulation(self, simulation_name: str) -> opf.OperationFactory:
        """
        Get a prepared simulation by name.
        
        Args:
            simulation_name: Name of the simulation
            
        Returns:
            OperationFactory instance
            
        Raises:
            ValueError: If simulation not found or not prepared
        """
        if simulation_name not in self.simulations:
            raise ValueError(
                f"Simulation '{simulation_name}' not found or not prepared. "
                "Call prepare_simulation() or prepare_all_simulations() first."
            )
        
        return self.simulations[simulation_name]
    
    def list_simulations(self) -> List[str]:
        """
        List all registered simulation names.
        
        Returns:
            List of simulation names
        """
        return list(self.simulations.keys())
    
    def get_sharing_summary(self) -> Dict[str, List[str]]:
        """
        Get a summary of data sharing between simulations.
        
        Returns:
            Dictionary mapping data identifiers to lists of simulations using them.
        """
        return {
            identifier: context.simulations 
            for identifier, context in self.shared_data_contexts.items()
        }
    
    def run_simulation(self, simulation_name: str) -> pd.DataFrame:
        """
        Run ECL calculation for a single simulation.
        
        The simulation must be prepared first using prepare_simulation() or prepare_all_simulations().
        
        Args:
            simulation_name: Name of the simulation to run
            
        Returns:
            DataFrame with ECL calculation results
            
        Raises:
            ValueError: If simulation not found or not prepared
            
        Example:
            >>> manager.prepare_simulation("scenario_1")
            >>> results = manager.run_simulation("scenario_1")
        """
        if simulation_name not in self._prepared_simulations:
            raise ValueError(
                f"Simulation '{simulation_name}' must be prepared before running. "
                "Call prepare_simulation() or prepare_all_simulations() first."
            )
        
        factory = self.simulations[simulation_name]
        
        logger.info(f"Running ECL calculation for '{simulation_name}'...")
        
        # Run the ECL calculation steps
        factory.get_time_steps()
        factory.get_scenarios()
        factory.create_segment_by_rules()
        factory.get_amortization_type()
        factory.calcul_ecl()
        factory.calcul_staging()
        
        logger.info(f"ECL calculation completed for '{simulation_name}'")
        
        return factory.ecl_operation_data.df
    
    def run_all_simulations(self) -> Dict[str, pd.DataFrame]:
        """
        Run ECL calculations for all prepared simulations.
        
        Returns:
            Dictionary mapping simulation names to their result DataFrames
            
        Example:
            >>> manager.prepare_all_simulations()
            >>> results = manager.run_all_simulations()
            >>> print(results["scenario_1"].head())
        """
        results = {}
        
        logger.info(f"Running ECL calculations for {len(self._prepared_simulations)} simulation(s)...")
        
        for sim_name in self._prepared_simulations:
            results[sim_name] = self.run_simulation(sim_name)
        
        logger.info("All ECL calculations completed successfully")
        
        return results
    
    def get_results(self, simulation_name: str) -> pd.DataFrame:
        """
        Get the results DataFrame for a simulation.
        
        Args:
            simulation_name: Name of the simulation
            
        Returns:
            DataFrame with calculation results
            
        Raises:
            ValueError: If simulation not found
        """
        if simulation_name not in self.simulations:
            raise ValueError(f"Simulation '{simulation_name}' not found")
        
        return self.simulations[simulation_name].ecl_operation_data.df
    
    def clear(self) -> None:
        """Clear all simulations and shared data contexts."""
        self.simulations.clear()
        self.shared_data_contexts.clear()
        self._prepared_simulations.clear()
        self._temp_files_cache.clear()
        logger.info("SimulationManager cleared")


if __name__ == "__main__":
    # Example usage
    
    # Create manager
    manager = SimulationManager()
    
    # Simulate uploaded files with same name (data_identifier)
    data_file_1 = r"sample\data\sample_non_retail.zip"
    data_file_2 = r"sample\data\copy_of_sample_non_retail.zip"  # Different path, same logical data
    
    # Add simulations - first 2 share same data_identifier
    manager.add_simulation(
        simulation_name="scenario_1",
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        data_file_path=data_file_1,
        template_file_path=r"sample\templates\Template_scenario1.xlsx",
        data_identifier="my_data.zip"  # Explicit identifier (like uploaded_file.name)
    )
    
    manager.add_simulation(
        simulation_name="scenario_2",
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        data_file_path=data_file_2,  # Different path
        template_file_path=r"sample\templates\Template_scenario2.xlsx",
        data_identifier="my_data.zip"  # Same identifier → data sharing!
    )
    
    # Add simulation with different data
    manager.add_simulation(
        simulation_name="scenario_3",
        operation_type=cst.OperationType.NON_RETAIL,
        operation_status=cst.OperationStatus.PERFORMING,
        data_file_path=r"sample\data\other_data.zip",
        template_file_path=r"sample\templates\Template_scenario3.xlsx",
        data_identifier="other_data.zip"  # Different data
    )
    
    # Display sharing summary
    print("\nData Sharing Summary:")
    summary = manager.get_sharing_summary()
    for data_id, sims in summary.items():
        print(f"  {data_id}: {sims}")
    
    # Prepare all simulations
    print("\nPreparing simulations...")
    manager.prepare_all_simulations()
    
    # Get individual simulations
    factory_1 = manager.get_simulation("scenario_1")
    factory_2 = manager.get_simulation("scenario_2")
    factory_3 = manager.get_simulation("scenario_3")
    
    print(f"\n✅ All simulations ready!")
    print(f"   - scenario_1: {factory_1.ecl_operation_data.df.shape}")
    print(f"   - scenario_2: {factory_2.ecl_operation_data.df.shape} (shared with scenario_1)")
    print(f"   - scenario_3: {factory_3.ecl_operation_data.df.shape}")
