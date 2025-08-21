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
