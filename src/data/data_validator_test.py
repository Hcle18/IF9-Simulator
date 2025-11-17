# Global import
from src.core.librairies import *

# Local import
from src.core import config as cst
from src.core import base_data as bcls
from src.core import base_template as tplm
from src.utils.mapping_columns import mapping_columns, normalize_field_name

logger = logging.getLogger(__name__)
# ========================================
# 1. Non Retail S1+S2 data validation
# ========================================
class NRS1S2DataValidator(bcls.BaseValidator):
    '''
    Custom class for Non Retail S1+S2 data validation
    '''
    def __init__(self, simu_data: bcls.OperationData, template_data: tplm.TemplateData):
        super().__init__(simu_data, template_data)
        self.validation_errors = []
        self.validation_warnings = []
        self.field_mapping_dict = self._get_mapping_dict()

    def _get_mapping_dict(self) -> Dict[str, str]:
        """
        Extract field mapping from the F1-Mapping fields Non Retail template sheet.
        Maps SIMULATION_DATA_COLUMN_NAME to CALCULATOR_COLUMN_NAME.
        """
        if not self.template_data or "F1-Mapping fields Non Retail" not in self.template_data:
            logger.warning("Template mapping data not available, using fallback mapping")
            return self._get_fallback_field_mapping()
        
        try:
            mapping_df = self.template_data["F1-Mapping fields Non Retail"]
            
            # Verify required columns exist
            required_cols = ["CALCULATOR_COLUMN_NAME", "SIMULATION_DATA_COLUMN_NAME"]
            if not all(col in mapping_df.columns for col in required_cols):
                logger.error(f"Required mapping columns not found: {required_cols}")
            
            # Create mapping dictionary from template
            # Key: simulation data column name -> Value: calculator standard column name
            
            field_mapping = dict(zip(mapping_df['Field_application'], mapping_df['Field_input']))

            logger.info("Successfully extracted %d field mappings from template", len(field_mapping))
            return field_mapping
            
        except Exception as e:
            logger.error(f"Error extracting field mapping from template: {str(e)}")
            raise

    def _get_fallback_field_mapping(self) -> Dict[str, str]:
        """
        Fallback field mapping for Non-Retail S1+S2 operations when template is not available.
        This should match your expected field names from the template.
        """
        self.logger.info("Using fallback field mapping")
        return {
            # Core identification fields
            'OPERATION_ID': 'ID_OPERATION',
            'CONTRACT_NUMBER': 'NUMERO_CONTRAT', 
            'COUNTERPARTY_ID': 'ID_CONTREPARTIE',
            'COUNTERPARTY_NAME': 'NOM_CONTREPARTIE',
            'CLIENT_CODE': 'CODE_CLIENT',
            
            # Financial exposure fields
            'OUTSTANDING_AMOUNT': 'ENCOURS_COMPTABLE',
            'TOTAL_EXPOSURE': 'ENCOURS_TOTAL',
            'UNUSED_COMMITMENT': 'ENGAGEMENT_NON_UTILISE',
            'CREDIT_LIMIT': 'LIMITE_ACCORDEE',
            'GUARANTEED_AMOUNT': 'MONTANT_GARANTI',
            
            # Product and classification
            'PRODUCT_TYPE': 'TYPE_PRODUIT',
            'PRODUCT_CODE': 'CODE_PRODUIT',
            'SEGMENT': 'SEGMENT',
            'PORTFOLIO': 'PORTEFEUILLE',
            'BUSINESS_LINE': 'LIGNE_METIER',
            'ACTIVITY_CODE': 'CODE_ACTIVITE',
            
            # Risk parameters
            'INTERNAL_RATING': 'NOTATION_INTERNE',
            'EXTERNAL_RATING': 'NOTATION_EXTERNE',
            'PD_RATE': 'TAUX_PD',
            'LGD_RATE': 'TAUX_LGD', 
            'CCF_RATE': 'TAUX_CCF',
            'EAD_AMOUNT': 'MONTANT_EAD',
            
            # Dates
            'ORIGINATION_DATE': 'DATE_OCTROI',
            'MATURITY_DATE': 'DATE_ECHEANCE',
            'LAST_REVIEW_DATE': 'DATE_DERNIERE_REVISION',
            'REPORTING_DATE': 'DATE_ARRETE',
            
            # Currency and geography  
            'CURRENCY': 'DEVISE',
            'COUNTRY': 'PAYS',
            'ECONOMIC_SECTOR': 'SECTEUR_ECONOMIQUE',
            
            # IFRS9 specific
            'IFRS9_STAGE': 'STAGE_IFRS9',
            'SICR_FLAG': 'INDICATEUR_DETERIORATION',
            'DEFAULT_FLAG': 'INDICATEUR_DEFAUT',
            'FORBEARANCE_FLAG': 'INDICATEUR_FORBEARANCE',
            'MODEL_CODE': 'CODE_MODELE_IFRS9'
        }

    def mapping_fields(self) -> pd.DataFrame:
        """
        Map client field names to simulator standard field names using template mapping.
        :return: DataFrame with mapped field names
        """
        try:
            self.logger.info("Starting field mapping for Non-Retail S1+S2 data using template mapping")
            
            if not self.field_mapping_dict:
                self.logger.warning("No field mapping available, returning original data")
                return self.df.copy()
            
            # Apply field mapping using the mapping_columns utility function
            # Note: mapping_columns expects mapping in format {standard_name: client_name}
            # Our template gives us {standard_name: client_name}, so we use it directly
            mapped_df = mapping_columns(self.df, self.field_mapping_dict)
            
            # Log mapping results
            original_cols = set(self.df.columns)
            mapped_cols = set(mapped_df.columns)
            newly_mapped_cols = mapped_cols - original_cols
            
            if newly_mapped_cols:
                self.logger.info(f"Successfully mapped {len(newly_mapped_cols)} columns: {list(newly_mapped_cols)}")
            else:
                self.logger.warning("No columns were mapped - check field mapping configuration")
            
            # Add derived fields specific to Non-Retail S1+S2
            mapped_df = self._add_derived_fields(mapped_df)
            
            # Standardize data types
            mapped_df = self._standardize_data_types(mapped_df)
            
            self.logger.info(f"Field mapping completed. Final dataset has {len(mapped_df.columns)} columns")
            return mapped_df
            
        except Exception as e:
            error_msg = f"Error during field mapping: {str(e)}"
            self.validation_errors.append(error_msg)
            self.logger.error(error_msg)
            return self.df.copy()

    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add derived fields specific to Non-Retail S1+S2 operations.
        """
        try:
            # Calculate residual maturity in months
            if 'MATURITY_DATE' in df.columns and 'REPORTING_DATE' in df.columns:
                df['MATURITY_DATE'] = pd.to_datetime(df['MATURITY_DATE'], errors='coerce')
                df['REPORTING_DATE'] = pd.to_datetime(df['REPORTING_DATE'], errors='coerce') 
                df['RESIDUAL_MATURITY_MONTHS'] = (
                    (df['MATURITY_DATE'] - df['REPORTING_DATE']).dt.days / 30.44
                ).clip(lower=0)
            elif 'MATURITY_DATE' in df.columns:
                # Use current date if reporting date not available
                df['MATURITY_DATE'] = pd.to_datetime(df['MATURITY_DATE'], errors='coerce')
                df['RESIDUAL_MATURITY_MONTHS'] = (
                    (df['MATURITY_DATE'] - pd.Timestamp.now()).dt.days / 30.44
                ).clip(lower=0)

            # Calculate credit utilization rate
            if 'OUTSTANDING_AMOUNT' in df.columns and 'CREDIT_LIMIT' in df.columns:
                df['UTILIZATION_RATE'] = np.where(
                    df['CREDIT_LIMIT'] > 0,
                    df['OUTSTANDING_AMOUNT'] / df['CREDIT_LIMIT'],
                    0
                )

            # Calculate total exposure at default (EAD)
            if all(col in df.columns for col in ['OUTSTANDING_AMOUNT', 'UNUSED_COMMITMENT', 'CCF_RATE']):
                df['CALCULATED_EAD'] = (
                    df['OUTSTANDING_AMOUNT'] + (df['UNUSED_COMMITMENT'] * df['CCF_RATE'])
                )
            elif 'OUTSTANDING_AMOUNT' in df.columns:
                df['CALCULATED_EAD'] = df['OUTSTANDING_AMOUNT']

            # Determine IFRS9 stage if not provided
            if 'IFRS9_STAGE' not in df.columns:
                if 'SICR_FLAG' in df.columns:
                    df['IFRS9_STAGE'] = np.where(df['SICR_FLAG'] == 1, 2, 1)
                else:
                    df['IFRS9_STAGE'] = 1  # Default to Stage 1 for S1+S2

            # Risk category based on internal rating
            if 'INTERNAL_RATING' in df.columns:
                df['RISK_CATEGORY'] = df['INTERNAL_RATING'].apply(self._categorize_risk)

            self.logger.info("Derived fields added successfully")
            return df

        except Exception as e:
            warning_msg = f"Error adding derived fields: {str(e)}"
            self.validation_warnings.append(warning_msg)
            self.logger.warning(warning_msg)
            return df

    def _categorize_risk(self, rating: str) -> str:
        """Categorize internal ratings into risk levels for Non-Retail."""
        if pd.isna(rating):
            return 'Not Rated'
        
        rating_str = str(rating).upper().strip()
        
        # Investment grade ratings
        if rating_str in ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-']:
            return 'Investment Grade'
        # Speculative grade but not high risk
        elif rating_str in ['BB+', 'BB', 'BB-', 'B+']:
            return 'Speculative Grade'
        # High risk ratings
        elif rating_str in ['B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C']:
            return 'High Risk'
        # Default
        elif rating_str in ['D', 'DEFAULT']:
            return 'Default'
        else:
            return 'Unclassified'

    def _standardize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data types for Non-Retail operations."""
        try:
            # Define expected data types
            type_mapping = {
                # Text fields
                'OPERATION_ID': 'str',
                'CONTRACT_NUMBER': 'str', 
                'COUNTERPARTY_ID': 'str',
                'COUNTERPARTY_NAME': 'str',
                'PRODUCT_TYPE': 'str',
                'SEGMENT': 'str',
                'PORTFOLIO': 'str',
                'CURRENCY': 'str',
                'COUNTRY': 'str',
                'INTERNAL_RATING': 'str',
                'RISK_CATEGORY': 'str',
                
                # Numeric fields
                'OUTSTANDING_AMOUNT': 'float64',
                'TOTAL_EXPOSURE': 'float64', 
                'UNUSED_COMMITMENT': 'float64',
                'CREDIT_LIMIT': 'float64',
                'PD_RATE': 'float64',
                'LGD_RATE': 'float64',
                'CCF_RATE': 'float64',
                'UTILIZATION_RATE': 'float64',
                'RESIDUAL_MATURITY_MONTHS': 'float64',
                'CALCULATED_EAD': 'float64',
                
                # Integer fields
                'IFRS9_STAGE': 'int64',
                'SICR_FLAG': 'int64',
                'DEFAULT_FLAG': 'int64',
                'FORBEARANCE_FLAG': 'int64'
            }

            for column, dtype in type_mapping.items():
                if column in df.columns:
                    try:
                        if dtype == 'float64':
                            df[column] = pd.to_numeric(df[column], errors='coerce')
                        elif dtype == 'int64':
                            df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0).astype('int64')
                        elif dtype == 'str':
                            df[column] = df[column].astype('str').replace('nan', '')
                    except Exception as e:
                        self.validation_warnings.append(f"Could not convert {column} to {dtype}: {str(e)}")

            self.logger.info("Data types standardized successfully")
            return df

        except Exception as e:
            warning_msg = f"Error standardizing data types: {str(e)}"
            self.validation_warnings.append(warning_msg)
            self.logger.warning(warning_msg)
            return df

    def data_validator(self, simu_data: bcls.OperationData) -> bcls.OperationData:
        """
        Comprehensive validation for Non-Retail S1+S2 data.
        :param simu_data: OperationData instance to validate
        :return: Updated OperationData with validation results
        """
        self.logger.info("Starting comprehensive data validation for Non-Retail S1+S2")
        
        validation_results = {
            'validation_type': 'Non-Retail S1+S2',
            'timestamp': pd.Timestamp.now(),
            'total_records': len(simu_data.data),
            'errors': [],
            'warnings': [],
            'data_quality_metrics': {},
            'validation_summary': {}
        }

        try:
            # 1. Required fields validation
            self._validate_required_fields(simu_data.data, validation_results)
            
            # 2. Data completeness validation  
            self._validate_data_completeness(simu_data.data, validation_results)
            
            # 3. Data quality and consistency checks
            self._validate_data_quality(simu_data.data, validation_results)
            
            # 4. Business rules validation
            self._validate_business_rules(simu_data.data, validation_results)
            
            # 5. Non-Retail specific validations
            self._validate_non_retail_specific(simu_data.data, validation_results)
            
            # 6. IFRS9 S1+S2 compliance validation
            self._validate_ifrs9_s1s2_compliance(simu_data.data, validation_results)
            
            # 7. Calculate overall data quality score
            validation_results['data_quality_score'] = self._calculate_data_quality_score(validation_results)
            
            # 8. Generate validation summary
            self._generate_validation_summary(validation_results)

            # Add accumulated errors and warnings
            validation_results['errors'].extend(self.validation_errors)
            validation_results['warnings'].extend(self.validation_warnings)

            # Log validation results
            self.logger.info(f"Validation completed - Score: {validation_results['data_quality_score']:.2%}")
            self.logger.info(f"Errors: {len(validation_results['errors'])}, Warnings: {len(validation_results['warnings'])}")

            # Create updated OperationData with validation results
            validated_data = bcls.OperationData(
                data=simu_data.data,
                operation_type=simu_data.operation_type,
                operation_status=simu_data.operation_status
            )
            
            # Store validation results (assuming OperationData supports this)
            validated_data.validation_results = validation_results
            
            return validated_data

        except Exception as e:
            critical_error = f"Critical validation error: {str(e)}"
            validation_results['errors'].append(critical_error)
            self.logger.error(critical_error)
            return simu_data

    def _validate_required_fields(self, df: pd.DataFrame, results: Dict):
        """Validate presence of required fields for Non-Retail S1+S2."""
        required_fields = [
            'OPERATION_ID',
            'COUNTERPARTY_ID', 
            'OUTSTANDING_AMOUNT',
            'PRODUCT_TYPE',
            'SEGMENT',
            'CURRENCY',
            'MATURITY_DATE'
        ]
        
        missing_fields = [field for field in required_fields if field not in df.columns]
        
        if missing_fields:
            results['errors'].append(f"Missing critical required fields: {missing_fields}")
        
        results['data_quality_metrics']['required_fields_coverage'] = (
            len(required_fields) - len(missing_fields)
        ) / len(required_fields)

    def _validate_data_completeness(self, df: pd.DataFrame, results: Dict):
        """Validate data completeness (null values, empty strings)."""
        completeness_issues = {}
        
        critical_fields = ['OPERATION_ID', 'COUNTERPARTY_ID', 'OUTSTANDING_AMOUNT']
        
        for field in critical_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                empty_count = (df[field].astype(str).str.strip() == '').sum()
                total_missing = null_count + empty_count
                
                if total_missing > 0:
                    completeness_issues[field] = {
                        'null_count': int(null_count),
                        'empty_count': int(empty_count), 
                        'total_missing': int(total_missing),
                        'completeness_rate': (len(df) - total_missing) / len(df)
                    }
        
        if completeness_issues:
            results['warnings'].append(f"Data completeness issues found: {list(completeness_issues.keys())}")
        
        results['data_quality_metrics']['completeness_issues'] = completeness_issues

    def _validate_data_quality(self, df: pd.DataFrame, results: Dict):
        """Validate data quality (ranges, formats, consistency)."""
        quality_issues = []

        # Validate numeric ranges
        if 'OUTSTANDING_AMOUNT' in df.columns:
            negative_amounts = (df['OUTSTANDING_AMOUNT'] < 0).sum()
            zero_amounts = (df['OUTSTANDING_AMOUNT'] == 0).sum()
            
            if negative_amounts > 0:
                quality_issues.append(f"Found {negative_amounts} negative outstanding amounts")
            if zero_amounts > len(df) * 0.1:  # More than 10% zero amounts is suspicious
                quality_issues.append(f"High number of zero outstanding amounts: {zero_amounts}")

        # Validate rate fields (should be between 0 and 1)
        rate_fields = ['PD_RATE', 'LGD_RATE', 'CCF_RATE']
        for field in rate_fields:
            if field in df.columns:
                invalid_rates = ((df[field] < 0) | (df[field] > 1)).sum()
                if invalid_rates > 0:
                    quality_issues.append(f"Found {invalid_rates} invalid {field} values (outside 0-1 range)")

        # Validate date consistency
        if all(field in df.columns for field in ['ORIGINATION_DATE', 'MATURITY_DATE']):
            date_inconsistencies = (
                pd.to_datetime(df['MATURITY_DATE']) <= pd.to_datetime(df['ORIGINATION_DATE'])
            ).sum()
            if date_inconsistencies > 0:
                quality_issues.append(f"Found {date_inconsistencies} operations with maturity <= origination date")

        results['warnings'].extend(quality_issues)
        results['data_quality_metrics']['quality_issues_count'] = len(quality_issues)

    def _validate_business_rules(self, df: pd.DataFrame, results: Dict):
        """Validate Non-Retail business rules."""
        business_violations = []

        # Rule 1: Outstanding should not exceed credit limit (with tolerance)
        if all(field in df.columns for field in ['OUTSTANDING_AMOUNT', 'CREDIT_LIMIT']):
            tolerance = 1.05  # 5% tolerance
            violations = (df['OUTSTANDING_AMOUNT'] > df['CREDIT_LIMIT'] * tolerance).sum()
            if violations > 0:
                business_violations.append(f"Found {violations} operations exceeding credit limit (>5% tolerance)")

        # Rule 2: Non-Retail minimum exposure threshold
        if 'OUTSTANDING_AMOUNT' in df.columns:
            min_threshold = 100000  # 100K minimum for Non-Retail
            below_threshold = (df['OUTSTANDING_AMOUNT'] < min_threshold).sum()
            if below_threshold > len(df) * 0.05:  # More than 5% below threshold
                business_violations.append(f"High number of operations below Non-Retail threshold: {below_threshold}")

        # Rule 3: PD rates should be reasonable for S1+S2
        if 'PD_RATE' in df.columns:
            high_pd_performing = (df['PD_RATE'] > 0.15).sum()  # 15% seems high for performing
            if high_pd_performing > 0:
                business_violations.append(f"Found {high_pd_performing} S1+S2 operations with suspiciously high PD (>15%)")

        results['warnings'].extend(business_violations)
        results['data_quality_metrics']['business_violations_count'] = len(business_violations)

    def _validate_non_retail_specific(self, df: pd.DataFrame, results: Dict):
        """Non-Retail specific validations."""
        nr_specific_issues = []

        # Check segment consistency for Non-Retail
        if 'SEGMENT' in df.columns:
            valid_nr_segments = ['CORPORATE', 'SME', 'LARGE_CORPORATE', 'FINANCIAL_INSTITUTIONS']
            invalid_segments = (~df['SEGMENT'].str.upper().isin(valid_nr_segments)).sum()
            if invalid_segments > 0:
                nr_specific_issues.append(f"Found {invalid_segments} operations with non-standard Non-Retail segments")

        # Check currency concentration (Non-Retail should be more diversified)
        if 'CURRENCY' in df.columns:
            currency_concentration = df['CURRENCY'].value_counts(normalize=True).iloc[0]
            if currency_concentration > 0.8:  # More than 80% in single currency
                nr_specific_issues.append(f"High currency concentration: {currency_concentration:.1%} in main currency")

        results['warnings'].extend(nr_specific_issues)
        results['data_quality_metrics']['non_retail_issues_count'] = len(nr_specific_issues)

    def _validate_ifrs9_s1s2_compliance(self, df: pd.DataFrame, results: Dict):
        """Validate IFRS9 Stage 1+2 specific requirements."""
        ifrs9_issues = []

        # Ensure all operations are in Stage 1 or 2
        if 'IFRS9_STAGE' in df.columns:
            invalid_stages = (~df['IFRS9_STAGE'].isin([1, 2])).sum()
            if invalid_stages > 0:
                ifrs9_issues.append(f"Found {invalid_stages} operations not in Stage 1 or 2 (should be S1+S2 only)")

        # Check SICR consistency
        if all(field in df.columns for field in ['IFRS9_STAGE', 'SICR_FLAG']):
            # Stage 2 should have SICR flag = 1
            stage2_without_sicr = ((df['IFRS9_STAGE'] == 2) & (df['SICR_FLAG'] != 1)).sum()
            if stage2_without_sicr > 0:
                ifrs9_issues.append(f"Found {stage2_without_sicr} Stage 2 operations without SICR flag")

        # Default flag should be 0 for S1+S2
        if 'DEFAULT_FLAG' in df.columns:
            defaulted_in_s1s2 = (df['DEFAULT_FLAG'] == 1).sum()
            if defaulted_in_s1s2 > 0:
                ifrs9_issues.append(f"Found {defaulted_in_s1s2} operations with default flag in S1+S2 dataset")

        results['warnings'].extend(ifrs9_issues)
        results['data_quality_metrics']['ifrs9_compliance_issues'] = len(ifrs9_issues)

    def _calculate_data_quality_score(self, results: Dict) -> float:
        """Calculate overall data quality score (0-1)."""
        metrics = results['data_quality_metrics']
        
        # Weight factors for different validation aspects
        weights = {
            'required_fields_coverage': 0.25,
            'completeness': 0.20,
            'quality': 0.20,
            'business_rules': 0.15,
            'non_retail_specific': 0.10,
            'ifrs9_compliance': 0.10
        }
        
        score = 0.0
        
        # Required fields coverage (direct score)
        score += metrics.get('required_fields_coverage', 0) * weights['required_fields_coverage']
        
        # Completeness score (average completeness rate)
        completeness_issues = metrics.get('completeness_issues', {})
        if completeness_issues:
            avg_completeness = np.mean([issue['completeness_rate'] for issue in completeness_issues.values()])
            score += avg_completeness * weights['completeness']
        else:
            score += 1.0 * weights['completeness']  # Perfect if no issues
        
        # Quality, business rules, and compliance scores (inverse of issue counts)
        issue_types = ['quality_issues_count', 'business_violations_count', 
                      'non_retail_issues_count', 'ifrs9_compliance_issues']
        weight_keys = ['quality', 'business_rules', 'non_retail_specific', 'ifrs9_compliance']
        
        for issue_type, weight_key in zip(issue_types, weight_keys):
            issue_count = metrics.get(issue_type, 0)
            max_acceptable = 10  # Maximum acceptable issues
            issue_score = max(0, 1 - (issue_count / max_acceptable))
            score += issue_score * weights[weight_key]
        
        return min(1.0, max(0.0, score))

    def _generate_validation_summary(self, results: Dict):
        """Generate a comprehensive validation summary."""
        total_records = results['total_records']
        quality_score = results['data_quality_score']
        
        # Determine overall status
        if quality_score >= 0.9:
            status = "EXCELLENT"
        elif quality_score >= 0.8:
            status = "GOOD"  
        elif quality_score >= 0.7:
            status = "ACCEPTABLE"
        elif quality_score >= 0.6:
            status = "POOR"
        else:
            status = "CRITICAL"
            
        summary = {
            'total_records': total_records,
            'data_quality_score': quality_score,
            'quality_status': status,
            'total_errors': len(results['errors']),
            'total_warnings': len(results['warnings']),
            'validation_timestamp': results['timestamp'],
            'key_metrics': {
                'required_fields_coverage': results['data_quality_metrics'].get('required_fields_coverage', 0),
                'completeness_issues_count': len(results['data_quality_metrics'].get('completeness_issues', {})),
                'quality_issues_count': results['data_quality_metrics'].get('quality_issues_count', 0),
                'business_violations_count': results['data_quality_metrics'].get('business_violations_count', 0)
            }
        }
        
        results['validation_summary'] = summary


# ========================================
# 2. Retail S1+S2 data validation
# ========================================
class RetailS1S2DataValidator(bcls.BaseValidator):
    def mapping_fields(self):
        pass

    def data_validator(self):
        pass