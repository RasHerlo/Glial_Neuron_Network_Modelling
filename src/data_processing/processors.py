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


class MatrixExtractionProcessor(BaseProcessor):
    """Processor for extracting matrices with labels from CSV files."""
    
    def __init__(self):
        super().__init__("Matrix Extraction")
        self.description = "Extract matrices with row and column labels from CSV files"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'matrix_name': 'extracted_matrix',
            'matrix_range': 'B3:AJW1217',
            'column_labels_range': 'B1:AJW1',
            'row_labels_range': 'A3:A1217',
            'transpose_matrix': False,
            'auto_detect': False
        }
    
    def _excel_column_to_index(self, col_str: str) -> int:
        """Convert Excel column (A, B, AA, etc.) to 0-based index."""
        result = 0
        for char in col_str.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1
    
    def _parse_excel_range(self, range_str: str) -> tuple:
        """Parse Excel range like 'B3:AJW1217' to (start_row, end_row, start_col, end_col)."""
        try:
            start_cell, end_cell = range_str.split(':')
            
            # Parse start cell
            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            
            # Parse end cell
            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            
            start_row = int(start_row_str) - 1  # Convert to 0-based
            end_row = int(end_row_str) - 1
            start_col = self._excel_column_to_index(start_col_str)
            end_col = self._excel_column_to_index(end_col_str)
            
            return start_row, end_row + 1, start_col, end_col + 1
            
        except Exception as e:
            raise ValueError(f"Invalid Excel range format '{range_str}': {str(e)}")
    
    def _auto_detect_matrix_range(self, data: pd.DataFrame) -> tuple:
        """Auto-detect the largest rectangular region of numeric data."""
        # Find all numeric cells
        numeric_mask = data.applymap(lambda x: pd.api.types.is_numeric_dtype(type(x)) or 
                                   (isinstance(x, str) and x.replace('.', '').replace('-', '').isdigit()))
        
        # Find the largest rectangular region
        max_area = 0
        best_range = (0, data.shape[0], 0, data.shape[1])
        
        # Simple approach: find largest contiguous numeric block
        for start_row in range(data.shape[0]):
            for start_col in range(data.shape[1]):
                if numeric_mask.iloc[start_row, start_col]:
                    # Expand from this point
                    end_row = start_row
                    end_col = start_col
                    
                    # Find maximum width at this row
                    while end_col < data.shape[1] - 1 and numeric_mask.iloc[start_row, end_col + 1]:
                        end_col += 1
                    
                    # Find maximum height with this width
                    while end_row < data.shape[0] - 1:
                        # Check if next row maintains the width
                        if all(numeric_mask.iloc[end_row + 1, start_col:end_col + 1]):
                            end_row += 1
                        else:
                            break
                    
                    area = (end_row - start_row + 1) * (end_col - start_col + 1)
                    if area > max_area:
                        max_area = area
                        best_range = (start_row, end_row + 1, start_col, end_col + 1)
        
        return best_range
    
    def _extract_matrix_data(self, data: pd.DataFrame, range_indices: tuple) -> pd.DataFrame:
        """Extract matrix data from specified range and convert to float64."""
        start_row, end_row, start_col, end_col = range_indices
        
        # Check bounds
        if end_row > data.shape[0] or end_col > data.shape[1]:
            raise ValueError(f"Range extends beyond file dimensions ({data.shape[0]}x{data.shape[1]})")
        
        # Extract the range
        matrix_data = data.iloc[start_row:end_row, start_col:end_col].copy()
        
        # Convert to numeric, replacing non-numeric with NaN
        for col in matrix_data.columns:
            matrix_data[col] = pd.to_numeric(matrix_data[col], errors='coerce')
        
        # Convert to float64
        matrix_data = matrix_data.astype('float64')
        
        return matrix_data
    
    def _extract_labels(self, data: pd.DataFrame, range_indices: tuple) -> List[str]:
        """Extract labels from specified range."""
        start_row, end_row, start_col, end_col = range_indices
        
        # Check bounds
        if end_row > data.shape[0] or end_col > data.shape[1]:
            raise ValueError(f"Label range extends beyond file dimensions ({data.shape[0]}x{data.shape[1]})")
        
        # Extract labels
        labels_data = data.iloc[start_row:end_row, start_col:end_col]
        
        # Convert to list of strings
        if labels_data.shape[1] == 1:  # Single column (row labels)
            labels = labels_data.iloc[:, 0].astype(str).tolist()
        else:  # Single row (column labels)
            labels = labels_data.iloc[0, :].astype(str).tolist()
        
        return labels
    
    def _transpose_if_needed(self, matrix: pd.DataFrame, row_labels: List[str], 
                           col_labels: List[str], transpose: bool) -> tuple:
        """Transpose matrix and swap labels if needed."""
        if transpose:
            matrix_t = matrix.T
            return matrix_t, col_labels, row_labels
        return matrix, row_labels, col_labels
    
    def _save_matrix_files(self, matrix: pd.DataFrame, row_labels: List[str], 
                          col_labels: List[str], dataset_name: str, matrix_name: str) -> str:
        """Save matrix files in the appropriate directory structure."""
        # Create output directory
        output_dir = os.path.join("data", "datasets", dataset_name, "processed", "matrices")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save matrix with labels as CSV
        matrix_with_labels = matrix.copy()
        matrix_with_labels.index = row_labels
        matrix_with_labels.columns = col_labels
        
        csv_path = os.path.join(output_dir, f"{matrix_name}_with_labels.csv")
        matrix_with_labels.to_csv(csv_path, index=True)
        
        # Save matrix alone as NPY
        npy_path = os.path.join(output_dir, f"{matrix_name}_matrix.npy")
        np.save(npy_path, matrix.values)
        
        # Save row labels as CSV
        row_labels_path = os.path.join(output_dir, f"{matrix_name}_row_labels.csv")
        pd.DataFrame({'row_labels': row_labels}).to_csv(row_labels_path, index=False)
        
        # Save column labels as CSV
        col_labels_path = os.path.join(output_dir, f"{matrix_name}_column_labels.csv")
        pd.DataFrame({'column_labels': col_labels}).to_csv(col_labels_path, index=False)
        
        return output_dir
    
    def get_preview(self, data: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a preview of the matrix extraction (10x10 window)."""
        try:
            # Get parameters
            auto_detect = parameters.get('auto_detect', False)
            matrix_range = parameters.get('matrix_range', 'B3:AJW1217')
            col_labels_range = parameters.get('column_labels_range', 'B1:AJW1')
            row_labels_range = parameters.get('row_labels_range', 'A3:A1217')
            transpose = parameters.get('transpose_matrix', False)
            matrix_name = parameters.get('matrix_name', 'extracted_matrix')
            
            # Determine matrix range
            if auto_detect:
                matrix_indices = self._auto_detect_matrix_range(data)
                # Update label ranges based on detected matrix
                start_row, end_row, start_col, end_col = matrix_indices
                # Assume labels are one row above and one column to the left
                col_indices = (max(0, start_row - 1), start_row, start_col, end_col)
                row_indices = (start_row, end_row, max(0, start_col - 1), start_col)
            else:
                matrix_indices = self._parse_excel_range(matrix_range)
                col_indices = self._parse_excel_range(col_labels_range)
                row_indices = self._parse_excel_range(row_labels_range)
            
            # Extract full data
            matrix = self._extract_matrix_data(data, matrix_indices)
            col_labels = self._extract_labels(data, col_indices)
            row_labels = self._extract_labels(data, row_indices)
            
            # Apply transposition
            matrix, row_labels, col_labels = self._transpose_if_needed(
                matrix, row_labels, col_labels, transpose)
            
            # Create 10x10 preview
            preview_size = min(10, matrix.shape[0], matrix.shape[1])
            preview_matrix = matrix.iloc[:preview_size, :preview_size].copy()
            preview_row_labels = row_labels[:preview_size]
            preview_col_labels = col_labels[:preview_size]
            
            # Set proper labels for preview
            preview_matrix.index = preview_row_labels
            preview_matrix.columns = preview_col_labels
            
            return {
                'success': True,
                'matrix_name': matrix_name,
                'full_shape': matrix.shape,
                'preview_shape': preview_matrix.shape,
                'transposed': transpose,
                'preview_matrix': preview_matrix,
                'message': f'Preview generated successfully for {matrix_name}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Preview generation failed: {str(e)}'
            }
    
    def process(self, data: pd.DataFrame, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process the dataset and extract matrix with labels."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            # Get parameters
            auto_detect = parameters.get('auto_detect', False)
            matrix_range = parameters.get('matrix_range', 'B3:AJW1217')
            col_labels_range = parameters.get('column_labels_range', 'B1:AJW1')
            row_labels_range = parameters.get('row_labels_range', 'A3:A1217')
            transpose = parameters.get('transpose_matrix', False)
            matrix_name = parameters.get('matrix_name', 'extracted_matrix')
            
            # Determine matrix range
            if auto_detect:
                matrix_indices = self._auto_detect_matrix_range(data)
                # Update label ranges based on detected matrix
                start_row, end_row, start_col, end_col = matrix_indices
                col_indices = (max(0, start_row - 1), start_row, start_col, end_col)
                row_indices = (start_row, end_row, max(0, start_col - 1), start_col)
            else:
                matrix_indices = self._parse_excel_range(matrix_range)
                col_indices = self._parse_excel_range(col_labels_range)
                row_indices = self._parse_excel_range(row_labels_range)
            
            # Extract data
            matrix = self._extract_matrix_data(data, matrix_indices)
            col_labels = self._extract_labels(data, col_indices)
            row_labels = self._extract_labels(data, row_indices)
            
            # Validate dimensions
            if len(row_labels) != matrix.shape[0]:
                raise ValueError(f"Row labels count ({len(row_labels)}) doesn't match matrix rows ({matrix.shape[0]})")
            if len(col_labels) != matrix.shape[1]:
                raise ValueError(f"Column labels count ({len(col_labels)}) doesn't match matrix columns ({matrix.shape[1]})")
            
            # Apply transposition
            matrix, row_labels, col_labels = self._transpose_if_needed(
                matrix, row_labels, col_labels, transpose)
            
            # Count non-numeric values that were converted to NaN
            nan_count = matrix.isna().sum().sum()
            if nan_count > 0:
                print(f"Warning: {nan_count} non-numeric values were converted to NaN")
            
            # Dataset name should be passed from the manager
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            # Save files
            output_dir = self._save_matrix_files(matrix, row_labels, col_labels, dataset_name, matrix_name)
            
            # Calculate statistics
            statistics = {
                'matrix_shape': matrix.shape,
                'matrix_name': matrix_name,
                'transposed': transpose,
                'auto_detected': auto_detect,
                'nan_values_count': nan_count,
                'output_directory': output_dir,
                'files_created': [
                    f"{matrix_name}_with_labels.csv",
                    f"{matrix_name}_matrix.npy", 
                    f"{matrix_name}_row_labels.csv",
                    f"{matrix_name}_column_labels.csv"
                ]
            }
            
            return {
                'success': True,
                'data': matrix,  # Return the processed matrix
                'statistics': statistics,
                'output_path': output_dir,
                'message': f'Matrix extraction completed. Shape: {matrix.shape}, Files saved to: {output_dir}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Matrix extraction failed: {str(e)}'
            }


class DataProcessingManager:
    """Manager class for coordinating different data processors."""
    
    def __init__(self):
        self.processors = {
            'Data Cleaning': DataCleaningProcessor(),
            'Smoothing': SmoothingProcessor(),
            'Filtering': FilteringProcessor(),
            'Statistical Analysis': StatisticalAnalysisProcessor(),
            'Matrix Extraction': MatrixExtractionProcessor()
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
            # Load CSV files without headers to match GUI preview behavior
            if dataset.file_format == 'csv':
                data = pd.read_csv(dataset.file_path, header=None)
            elif dataset.file_format in ['xlsx', 'xls']:
                data = pd.read_excel(dataset.file_path, header=None)
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
            
            # Add dataset name to parameters for matrix extraction
            if parameters is None:
                parameters = {}
            parameters['dataset_name'] = dataset.name
            
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
