"""
Data processing modules with database integration.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import os
from pathlib import Path

from ..database.operations import DatasetOperations, ProcessingJobOperations


class BaseProcessor:
    """Base class for data processors."""
    
    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.parameters = {}
    
    def process(self, data: Any, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process data. Should be implemented by subclasses."""
        raise NotImplementedError
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate processing parameters."""
        return True
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for this processor."""
        return {}


class DataCleaningProcessor(BaseProcessor):
    """Processor for data cleaning operations."""
    
    def __init__(self):
        super().__init__("Data Cleaning")
        self.description = "Clean data by handling missing values, duplicates, and outliers"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'remove_duplicates': True,
            'handle_missing': 'drop',  # 'drop', 'fill_mean', 'fill_median', 'fill_mode', 'forward_fill'
            'remove_outliers': False,
            'outlier_method': 'iqr',  # 'iqr', 'zscore'
            'outlier_threshold': 3.0,
            'columns_to_process': 'all'  # 'all' or list of column names
        }
    
    def process(self, data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Clean the data based on parameters."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            cleaned_data = data.copy()
            operations_performed = []
            
            # Select columns to process
            if parameters.get('columns_to_process') == 'all':
                cols_to_process = cleaned_data.columns.tolist()
            else:
                cols_to_process = parameters.get('columns_to_process', [])
                cols_to_process = [col for col in cols_to_process if col in cleaned_data.columns]
            
            original_shape = cleaned_data.shape
            
            # Remove duplicates
            if parameters.get('remove_duplicates', True):
                before_count = len(cleaned_data)
                cleaned_data = cleaned_data.drop_duplicates()
                after_count = len(cleaned_data)
                if before_count != after_count:
                    operations_performed.append(f"Removed {before_count - after_count} duplicate rows")
            
            # Handle missing values
            missing_method = parameters.get('handle_missing', 'drop')
            if missing_method != 'none':
                missing_before = cleaned_data.isnull().sum().sum()
                
                if missing_method == 'drop':
                    cleaned_data = cleaned_data.dropna(subset=cols_to_process)
                elif missing_method == 'fill_mean':
                    numeric_cols = cleaned_data[cols_to_process].select_dtypes(include=[np.number]).columns
                    cleaned_data[numeric_cols] = cleaned_data[numeric_cols].fillna(cleaned_data[numeric_cols].mean())
                elif missing_method == 'fill_median':
                    numeric_cols = cleaned_data[cols_to_process].select_dtypes(include=[np.number]).columns
                    cleaned_data[numeric_cols] = cleaned_data[numeric_cols].fillna(cleaned_data[numeric_cols].median())
                elif missing_method == 'fill_mode':
                    for col in cols_to_process:
                        if col in cleaned_data.columns:
                            mode_value = cleaned_data[col].mode()
                            if len(mode_value) > 0:
                                cleaned_data[col] = cleaned_data[col].fillna(mode_value[0])
                elif missing_method == 'forward_fill':
                    cleaned_data[cols_to_process] = cleaned_data[cols_to_process].fillna(method='ffill')
                
                missing_after = cleaned_data.isnull().sum().sum()
                if missing_before != missing_after:
                    operations_performed.append(f"Handled {missing_before - missing_after} missing values using {missing_method}")
            
            # Remove outliers
            if parameters.get('remove_outliers', False):
                outlier_method = parameters.get('outlier_method', 'iqr')
                threshold = parameters.get('outlier_threshold', 3.0)
                
                numeric_cols = cleaned_data[cols_to_process].select_dtypes(include=[np.number]).columns
                before_count = len(cleaned_data)
                
                for col in numeric_cols:
                    if outlier_method == 'iqr':
                        Q1 = cleaned_data[col].quantile(0.25)
                        Q3 = cleaned_data[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        cleaned_data = cleaned_data[(cleaned_data[col] >= lower_bound) & (cleaned_data[col] <= upper_bound)]
                    elif outlier_method == 'zscore':
                        z_scores = np.abs((cleaned_data[col] - cleaned_data[col].mean()) / cleaned_data[col].std())
                        cleaned_data = cleaned_data[z_scores <= threshold]
                
                after_count = len(cleaned_data)
                if before_count != after_count:
                    operations_performed.append(f"Removed {before_count - after_count} outliers using {outlier_method} method")
            
            # Calculate statistics
            final_shape = cleaned_data.shape
            statistics = {
                'original_shape': original_shape,
                'final_shape': final_shape,
                'rows_removed': original_shape[0] - final_shape[0],
                'operations_performed': operations_performed,
                'missing_values_remaining': cleaned_data.isnull().sum().to_dict(),
                'data_types': cleaned_data.dtypes.to_dict()
            }
            
            return {
                'success': True,
                'data': cleaned_data,
                'statistics': statistics,
                'message': f'Data cleaning completed. {len(operations_performed)} operations performed.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Data cleaning failed: {str(e)}'
            }


class SmoothingProcessor(BaseProcessor):
    """Processor for data smoothing operations."""
    
    def __init__(self):
        super().__init__("Smoothing")
        self.description = "Apply smoothing filters to reduce noise in data"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'method': 'rolling_mean',  # 'rolling_mean', 'rolling_median', 'exponential', 'savgol'
            'window_size': 5,
            'alpha': 0.3,  # For exponential smoothing
            'poly_order': 2,  # For Savitzky-Golay filter
            'columns_to_smooth': 'numeric'  # 'numeric', 'all', or list of column names
        }
    
    def process(self, data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Smooth the data based on parameters."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            smoothed_data = data.copy()
            operations_performed = []
            
            # Select columns to smooth
            if parameters.get('columns_to_smooth') == 'numeric':
                cols_to_smooth = smoothed_data.select_dtypes(include=[np.number]).columns.tolist()
            elif parameters.get('columns_to_smooth') == 'all':
                cols_to_smooth = smoothed_data.columns.tolist()
            else:
                cols_to_smooth = parameters.get('columns_to_smooth', [])
                cols_to_smooth = [col for col in cols_to_smooth if col in smoothed_data.columns]
            
            method = parameters.get('method', 'rolling_mean')
            window_size = parameters.get('window_size', 5)
            
            for col in cols_to_smooth:
                if smoothed_data[col].dtype in [np.number, 'float64', 'int64']:
                    original_col = f"{col}_original"
                    smoothed_data[original_col] = smoothed_data[col].copy()
                    
                    if method == 'rolling_mean':
                        smoothed_data[col] = smoothed_data[col].rolling(window=window_size, center=True).mean()
                    elif method == 'rolling_median':
                        smoothed_data[col] = smoothed_data[col].rolling(window=window_size, center=True).median()
                    elif method == 'exponential':
                        alpha = parameters.get('alpha', 0.3)
                        smoothed_data[col] = smoothed_data[col].ewm(alpha=alpha).mean()
                    elif method == 'savgol':
                        try:
                            from scipy.signal import savgol_filter
                            poly_order = min(parameters.get('poly_order', 2), window_size - 1)
                            smoothed_values = savgol_filter(smoothed_data[col].dropna(), window_size, poly_order)
                            smoothed_data.loc[smoothed_data[col].notna(), col] = smoothed_values
                        except ImportError:
                            # Fallback to rolling mean if scipy not available
                            smoothed_data[col] = smoothed_data[col].rolling(window=window_size, center=True).mean()
                    
                    operations_performed.append(f"Applied {method} smoothing to column '{col}' with window size {window_size}")
            
            # Calculate statistics
            statistics = {
                'method_used': method,
                'window_size': window_size,
                'columns_processed': cols_to_smooth,
                'operations_performed': operations_performed
            }
            
            return {
                'success': True,
                'data': smoothed_data,
                'statistics': statistics,
                'message': f'Smoothing completed using {method} method on {len(cols_to_smooth)} columns.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Smoothing failed: {str(e)}'
            }


class FilteringProcessor(BaseProcessor):
    """Processor for data filtering operations."""
    
    def __init__(self):
        super().__init__("Filtering")
        self.description = "Filter data based on various criteria"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'filter_type': 'range',  # 'range', 'threshold', 'percentile', 'condition'
            'column': None,  # Column to filter on
            'min_value': None,
            'max_value': None,
            'threshold': None,
            'threshold_operator': 'greater',  # 'greater', 'less', 'equal'
            'percentile_low': 5,
            'percentile_high': 95,
            'custom_condition': None  # String condition like "column > 10 & column < 100"
        }
    
    def process(self, data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Filter the data based on parameters."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            filtered_data = data.copy()
            operations_performed = []
            original_count = len(filtered_data)
            
            filter_type = parameters.get('filter_type', 'range')
            column = parameters.get('column')
            
            if not column or column not in filtered_data.columns:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Column "{column}" not found in data'
                }
            
            if filter_type == 'range':
                min_val = parameters.get('min_value')
                max_val = parameters.get('max_value')
                
                if min_val is not None:
                    filtered_data = filtered_data[filtered_data[column] >= min_val]
                if max_val is not None:
                    filtered_data = filtered_data[filtered_data[column] <= max_val]
                
                operations_performed.append(f"Applied range filter on '{column}': [{min_val}, {max_val}]")
                
            elif filter_type == 'threshold':
                threshold = parameters.get('threshold')
                operator = parameters.get('threshold_operator', 'greater')
                
                if threshold is not None:
                    if operator == 'greater':
                        filtered_data = filtered_data[filtered_data[column] > threshold]
                    elif operator == 'less':
                        filtered_data = filtered_data[filtered_data[column] < threshold]
                    elif operator == 'equal':
                        filtered_data = filtered_data[filtered_data[column] == threshold]
                    
                    operations_performed.append(f"Applied threshold filter on '{column}': {operator} {threshold}")
                
            elif filter_type == 'percentile':
                low_perc = parameters.get('percentile_low', 5)
                high_perc = parameters.get('percentile_high', 95)
                
                low_val = filtered_data[column].quantile(low_perc / 100)
                high_val = filtered_data[column].quantile(high_perc / 100)
                
                filtered_data = filtered_data[
                    (filtered_data[column] >= low_val) & 
                    (filtered_data[column] <= high_val)
                ]
                
                operations_performed.append(f"Applied percentile filter on '{column}': {low_perc}% to {high_perc}%")
                
            elif filter_type == 'condition':
                condition = parameters.get('custom_condition')
                if condition:
                    # Note: This is potentially unsafe - in production, you'd want to sanitize this
                    filtered_data = filtered_data.query(condition)
                    operations_performed.append(f"Applied custom condition: {condition}")
            
            final_count = len(filtered_data)
            removed_count = original_count - final_count
            
            # Calculate statistics
            statistics = {
                'original_count': original_count,
                'final_count': final_count,
                'removed_count': removed_count,
                'removal_percentage': (removed_count / original_count) * 100 if original_count > 0 else 0,
                'filter_type': filter_type,
                'operations_performed': operations_performed
            }
            
            return {
                'success': True,
                'data': filtered_data,
                'statistics': statistics,
                'message': f'Filtering completed. Removed {removed_count} rows ({statistics["removal_percentage"]:.1f}%).'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Filtering failed: {str(e)}'
            }


class StatisticalAnalysisProcessor(BaseProcessor):
    """Processor for statistical analysis operations."""
    
    def __init__(self):
        super().__init__("Statistical Analysis")
        self.description = "Perform statistical analysis and generate summary statistics"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'include_correlations': True,
            'correlation_method': 'pearson',  # 'pearson', 'spearman', 'kendall'
            'include_distributions': True,
            'confidence_level': 0.95,
            'columns_to_analyze': 'numeric'  # 'numeric', 'all', or list of column names
        }
    
    def process(self, data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform statistical analysis on the data."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            # Select columns to analyze
            if parameters.get('columns_to_analyze') == 'numeric':
                cols_to_analyze = data.select_dtypes(include=[np.number]).columns.tolist()
            elif parameters.get('columns_to_analyze') == 'all':
                cols_to_analyze = data.columns.tolist()
            else:
                cols_to_analyze = parameters.get('columns_to_analyze', [])
                cols_to_analyze = [col for col in cols_to_analyze if col in data.columns]
            
            analysis_results = {}
            
            # Basic descriptive statistics
            numeric_cols = [col for col in cols_to_analyze if data[col].dtype in [np.number, 'float64', 'int64']]
            if numeric_cols:
                analysis_results['descriptive_stats'] = data[numeric_cols].describe().to_dict()
                
                # Additional statistics
                analysis_results['additional_stats'] = {}
                for col in numeric_cols:
                    col_data = data[col].dropna()
                    analysis_results['additional_stats'][col] = {
                        'variance': col_data.var(),
                        'skewness': col_data.skew(),
                        'kurtosis': col_data.kurtosis(),
                        'missing_count': data[col].isnull().sum(),
                        'missing_percentage': (data[col].isnull().sum() / len(data)) * 100
                    }
            
            # Correlation analysis
            if parameters.get('include_correlations', True) and len(numeric_cols) > 1:
                method = parameters.get('correlation_method', 'pearson')
                correlation_matrix = data[numeric_cols].corr(method=method)
                analysis_results['correlations'] = correlation_matrix.to_dict()
                
                # Find strong correlations
                strong_correlations = []
                for i in range(len(correlation_matrix.columns)):
                    for j in range(i+1, len(correlation_matrix.columns)):
                        corr_val = correlation_matrix.iloc[i, j]
                        if abs(corr_val) > 0.7:  # Strong correlation threshold
                            strong_correlations.append({
                                'column1': correlation_matrix.columns[i],
                                'column2': correlation_matrix.columns[j],
                                'correlation': corr_val
                            })
                
                analysis_results['strong_correlations'] = strong_correlations
            
            # Distribution analysis
            if parameters.get('include_distributions', True):
                analysis_results['distributions'] = {}
                for col in numeric_cols:
                    col_data = data[col].dropna()
                    if len(col_data) > 0:
                        analysis_results['distributions'][col] = {
                            'histogram_bins': 20,
                            'histogram_range': [col_data.min(), col_data.max()],
                            'quartiles': {
                                'Q1': col_data.quantile(0.25),
                                'Q2': col_data.quantile(0.5),
                                'Q3': col_data.quantile(0.75)
                            },
                            'outlier_bounds': {
                                'lower': col_data.quantile(0.25) - 1.5 * (col_data.quantile(0.75) - col_data.quantile(0.25)),
                                'upper': col_data.quantile(0.75) + 1.5 * (col_data.quantile(0.75) - col_data.quantile(0.25))
                            }
                        }
            
            # Categorical analysis for non-numeric columns
            categorical_cols = [col for col in cols_to_analyze if col not in numeric_cols]
            if categorical_cols:
                analysis_results['categorical_analysis'] = {}
                for col in categorical_cols:
                    value_counts = data[col].value_counts()
                    analysis_results['categorical_analysis'][col] = {
                        'unique_count': data[col].nunique(),
                        'most_frequent': value_counts.index[0] if len(value_counts) > 0 else None,
                        'most_frequent_count': value_counts.iloc[0] if len(value_counts) > 0 else 0,
                        'value_counts': value_counts.head(10).to_dict()  # Top 10 values
                    }
            
            # Overall data quality metrics
            analysis_results['data_quality'] = {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'numeric_columns': len(numeric_cols),
                'categorical_columns': len(categorical_cols),
                'total_missing_values': data.isnull().sum().sum(),
                'missing_percentage': (data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100,
                'duplicate_rows': data.duplicated().sum()
            }
            
            return {
                'success': True,
                'data': data,  # Original data unchanged
                'statistics': analysis_results,
                'message': f'Statistical analysis completed for {len(cols_to_analyze)} columns.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Statistical analysis failed: {str(e)}'
            }


class DataProcessingManager:
    """Manager class for coordinating different data processors."""
    
    def __init__(self):
        self.processors = {
            'Data Cleaning': DataCleaningProcessor(),
            'Smoothing': SmoothingProcessor(),
            'Filtering': FilteringProcessor(),
            'Statistical Analysis': StatisticalAnalysisProcessor()
        }
    
    def get_processor(self, processor_name: str) -> Optional[BaseProcessor]:
        """Get processor by name."""
        return self.processors.get(processor_name)
    
    def get_available_processors(self) -> List[str]:
        """Get list of available processor names."""
        return list(self.processors.keys())
    
    def process_dataset(self, dataset_id: int, processor_name: str, job_name: str,
                       parameters: Dict[str, Any] = None, 
                       progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process a dataset with specified processor and save results."""
        try:
            # Update progress
            if progress_callback:
                progress_callback(10.0)
            
            # Get dataset
            dataset = DatasetOperations.get_dataset(dataset_id)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset with ID {dataset_id} not found'
                }
            
            # Update progress
            if progress_callback:
                progress_callback(20.0)
            
            # Load data (this would need to be implemented based on file format)
            # For now, we'll assume CSV format
            if dataset.file_format == 'csv':
                data = pd.read_csv(dataset.file_path)
            else:
                return {
                    'success': False,
                    'message': f'Unsupported file format: {dataset.file_format}'
                }
            
            # Update progress
            if progress_callback:
                progress_callback(40.0)
            
            # Get processor
            processor = self.get_processor(processor_name)
            if not processor:
                return {
                    'success': False,
                    'message': f'Processor "{processor_name}" not found'
                }
            
            # Update progress
            if progress_callback:
                progress_callback(50.0)
            
            # Process data
            result = processor.process(data, parameters)
            
            # Update progress
            if progress_callback:
                progress_callback(80.0)
            
            if result['success']:
                # Save processed data
                output_dir = "data/processed"
                os.makedirs(output_dir, exist_ok=True)
                
                output_filename = f"{job_name}_{dataset.name}_processed.csv"
                output_path = os.path.join(output_dir, output_filename)
                
                if result['data'] is not None:
                    result['data'].to_csv(output_path, index=False)
                    result['output_path'] = output_path
                
                # Update progress
                if progress_callback:
                    progress_callback(100.0)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Processing failed: {str(e)}'
            }
