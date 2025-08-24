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
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process with processor-specific progress updates. Should be implemented by subclasses."""
        raise NotImplementedError
    
    def get_progress_steps(self) -> List[str]:
        """Return list of progress step descriptions for this processor."""
        return ["Processing..."]
    
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
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Matrix Extraction."""
        return [
            "Loading dataset file",
            "Parsing matrix ranges", 
            "Extracting matrix data",
            "Extracting labels",
            "Saving matrix files",
            "Completed"
        ]
    
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
        row_labels_path = os.path.join(output_dir, f"{matrix_name}_row_labels_and_indices.csv")
        pd.DataFrame({'row_labels': row_labels}).to_csv(row_labels_path, index=False)
        
        # Save column labels as CSV
        col_labels_path = os.path.join(output_dir, f"{matrix_name}_column_labels_and_indices.csv")
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
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the dataset and extract matrix with labels."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        def update_progress(percent: float):
            if progress_callback:
                progress_callback(percent)
        
        try:
            # Step 1: Load dataset file (10%)
            update_progress(10.0)
            dataset_path = parameters.get('dataset_path')
            dataset_format = parameters.get('dataset_format')
            
            if not dataset_path:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': 'Dataset path not provided'
                }
            
            # Load data based on file format
            if dataset_format == 'csv':
                data = pd.read_csv(dataset_path, header=None)
            elif dataset_format in ['xlsx', 'xls']:
                data = pd.read_excel(dataset_path, header=None)
            else:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Unsupported file format: {dataset_format}'
                }
            
            # Step 2: Parse matrix ranges (25%)
            update_progress(25.0)
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
            
            # Step 3: Extract matrix data (50%)
            update_progress(50.0)
            matrix = self._extract_matrix_data(data, matrix_indices)
            
            # Step 4: Extract labels (70%)
            update_progress(70.0)
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
            
            # Step 5: Save matrix files (90%)
            update_progress(90.0)
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
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
            
            # Step 6: Completed (100%)
            update_progress(100.0)
            
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


class MatrixModificationProcessor(BaseProcessor):
    """Processor for applying mathematical operations to existing processed matrices."""
    
    def __init__(self):
        super().__init__("Matrix Modification")
        self.description = "Apply mathematical operations to existing processed matrices"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'matrix': None,  # Will be populated dynamically from available matrices
            'operation': 'Z-scoring',
            'output_filename': '',  # Will be auto-generated based on matrix + operation
            'fileformat': '.npy'
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Matrix Modification."""
        return [
            "Validating matrix file",
            "Loading matrix data",
            "Applying operation",
            "Saving modified matrix",
            "Completed"
        ]
    
    def get_available_operations(self) -> List[str]:
        """Get list of available matrix operations."""
        return ['Z-scoring', '[0,1] normalization']
    
    def find_matrix_files(self, dataset_name: str) -> List[str]:
        """Find all .npy files in the dataset's processed/matrices folder."""
        matrices_path = os.path.join("data", "datasets", dataset_name, "processed", "matrices")
        
        if not os.path.exists(matrices_path):
            return []
        
        matrix_files = []
        for file in os.listdir(matrices_path):
            if file.endswith('.npy'):
                # Remove .npy extension: "Raster_matrix.npy" -> "Raster_matrix"
                base_name = file[:-4]  # Remove last 4 characters (.npy)
                matrix_files.append(base_name)
        
        return sorted(matrix_files)  # Sort alphabetically
    
    def generate_output_filename(self, matrix_name: str, operation: str) -> str:
        """Generate default output filename based on matrix name and operation."""
        operation_suffixes = {
            'Z-scoring': 'zscore',
            '[0,1] normalization': 'norm01'
        }
        suffix = operation_suffixes.get(operation, 'modified')
        return f"{matrix_name}_{suffix}"
    
    def apply_zscore_rowwise(self, matrix_data: np.ndarray) -> np.ndarray:
        """Apply Z-score normalization per row: (x - row_mean) / row_std."""
        # Calculate mean and std per row (axis=1), keep dimensions for broadcasting
        row_mean = np.mean(matrix_data, axis=1, keepdims=True)
        row_std = np.std(matrix_data, axis=1, keepdims=True)
        
        # Handle rows with zero standard deviation (constant values)
        row_std = np.where(row_std == 0, 1, row_std)
        
        return (matrix_data - row_mean) / row_std
    
    def apply_01_normalization_rowwise(self, matrix_data: np.ndarray) -> np.ndarray:
        """Apply [0,1] normalization per row: (x - row_min) / (row_max - row_min)."""
        # Calculate min and max per row (axis=1), keep dimensions for broadcasting
        row_min = np.min(matrix_data, axis=1, keepdims=True)
        row_max = np.max(matrix_data, axis=1, keepdims=True)
        
        # Handle rows with zero range (constant values)
        row_range = row_max - row_min
        row_range = np.where(row_range == 0, 1, row_range)
        
        return (matrix_data - row_min) / row_range
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the matrix with the specified operation."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        def update_progress(percent: float):
            if progress_callback:
                progress_callback(percent)
        
        try:
            # Step 1: Validate matrix file (20%)
            update_progress(20.0)
            # Get parameters
            matrix_name = parameters.get('matrix')
            operation = parameters.get('operation', 'Z-scoring')
            output_filename = parameters.get('output_filename', '')
            fileformat = parameters.get('fileformat', '.npy')
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            if not matrix_name:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': 'No matrix selected for modification'
                }
            
            # Construct matrix file path
            matrix_file_path = os.path.join("data", "datasets", dataset_name, "processed", "matrices", f"{matrix_name}.npy")
            
            # Validate matrix file exists
            if not os.path.exists(matrix_file_path):
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Matrix file not found: {matrix_file_path}'
                }
            
            # Step 2: Load matrix data (40%)
            update_progress(40.0)
            matrix_data = np.load(matrix_file_path)
            
            # Validate matrix is 2D
            if len(matrix_data.shape) != 2:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Matrix must be 2D, got shape: {matrix_data.shape}'
                }
            
            # Step 3: Apply operation (60%)
            update_progress(60.0)
            if operation == 'Z-scoring':
                modified_matrix = self.apply_zscore_rowwise(matrix_data)
                operation_desc = "Z-score normalization (row-wise)"
            elif operation == '[0,1] normalization':
                modified_matrix = self.apply_01_normalization_rowwise(matrix_data)
                operation_desc = "[0,1] normalization (row-wise)"
            else:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Unknown operation: {operation}'
                }
            
            # Generate output filename if not provided
            if not output_filename:
                output_filename = self.generate_output_filename(matrix_name, operation)
            
            # Step 4: Save modified matrix (80%)
            update_progress(80.0)
            output_dir = os.path.join("data", "datasets", dataset_name, "processed", "matrices")
            os.makedirs(output_dir, exist_ok=True)
            
            # Save modified matrix
            if fileformat == '.npy':
                output_path = os.path.join(output_dir, f"{output_filename}.npy")
                np.save(output_path, modified_matrix)
            elif fileformat == '.csv':
                output_path = os.path.join(output_dir, f"{output_filename}.csv")
                pd.DataFrame(modified_matrix).to_csv(output_path, index=False, header=False)
            else:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Unsupported file format: {fileformat}'
                }
            
            # Calculate statistics
            statistics = {
                'original_matrix_shape': matrix_data.shape,
                'modified_matrix_shape': modified_matrix.shape,
                'operation_applied': operation_desc,
                'original_matrix_stats': {
                    'mean': float(np.mean(matrix_data)),
                    'std': float(np.std(matrix_data)),
                    'min': float(np.min(matrix_data)),
                    'max': float(np.max(matrix_data))
                },
                'modified_matrix_stats': {
                    'mean': float(np.mean(modified_matrix)),
                    'std': float(np.std(modified_matrix)),
                    'min': float(np.min(modified_matrix)),
                    'max': float(np.max(modified_matrix))
                },
                'output_file': output_path,
                'output_format': fileformat
            }
            
            # Step 5: Completed (100%)
            update_progress(100.0)
            
            return {
                'success': True,
                'data': modified_matrix,
                'statistics': statistics,
                'output_path': output_path,
                'message': f'{operation_desc} completed. Output saved to: {output_path}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Matrix modification failed: {str(e)}'
            }


class DataAnnotationProcessor(BaseProcessor):
    """Processor for creating binary annotation vectors based on stimulation periods."""
    
    def __init__(self):
        super().__init__("Data Annotation")
        self.description = "Create binary annotation vectors indicating stimulation periods"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'annotation_name': 'annotation_vector',
            'vector_dimension': 'rows',  # 'rows' or 'columns'
            'framerate': 10.02,
            'stimulation_periods': []  # List of (start, end) tuples in seconds
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Data Annotation."""
        return [
            "Validating parameters",
            "Determining vector dimensions", 
            "Creating annotation vector",
            "Processing stimulation periods",
            "Saving annotation file",
            "Completed"
        ]
    
    def find_matrix_files(self, dataset_name: str) -> Dict[str, tuple]:
        """Find all .npy matrix files and return their dimensions."""
        matrices_path = os.path.join("data", "datasets", dataset_name, "processed", "matrices")
        
        if not os.path.exists(matrices_path):
            return {}
        
        matrix_dimensions = {}
        for file in os.listdir(matrices_path):
            if file.endswith('.npy'):
                try:
                    file_path = os.path.join(matrices_path, file)
                    matrix_data = np.load(file_path)
                    if len(matrix_data.shape) == 2:  # Only 2D matrices
                        base_name = file[:-4]  # Remove .npy extension
                        matrix_dimensions[base_name] = matrix_data.shape
                except Exception as e:
                    print(f"Warning: Could not read matrix file {file}: {e}")
                    continue
        
        return matrix_dimensions
    
    def get_vector_length(self, dataset_name: str, dimension_choice: str) -> int:
        """Get vector length based on dimension choice and existing matrices."""
        matrix_dimensions = self.find_matrix_files(dataset_name)
        
        if not matrix_dimensions:
            # Fallback: try to read from dataset file directly
            return self._get_fallback_dimensions(dataset_name, dimension_choice)
        
        # Use the first available matrix to determine dimensions
        first_matrix_shape = next(iter(matrix_dimensions.values()))
        
        if dimension_choice.startswith('rows'):
            return first_matrix_shape[0]  # Number of rows
        elif dimension_choice.startswith('columns'):
            return first_matrix_shape[1]  # Number of columns
        else:
            raise ValueError(f"Invalid dimension choice: {dimension_choice}")
    
    def _get_fallback_dimensions(self, dataset_name: str, dimension_choice: str) -> int:
        """Fallback method to get dimensions from original dataset file."""
        # This is a simplified fallback - in practice, you might want to 
        # load the actual dataset file and determine dimensions
        # For now, return a reasonable default
        if dimension_choice.startswith('rows'):
            return 1215  # Based on the example matrix range
        else:
            return 1000  # Reasonable default for columns
    
    def create_annotation_vector(self, vector_length: int, stimulation_periods: List[tuple], 
                                framerate: float) -> np.ndarray:
        """Create binary annotation vector from stimulation periods."""
        # Initialize vector with zeros
        annotation_vector = np.zeros(vector_length, dtype=int)
        
        # Process each stimulation period
        for start_time, end_time in stimulation_periods:
            if start_time < 0 or end_time < 0:
                continue  # Skip invalid periods
            if start_time >= end_time:
                continue  # Skip invalid periods
            
            # Convert time to indices
            start_idx = int(round(start_time * framerate))
            end_idx = int(round(end_time * framerate))
            
            # Clamp to vector bounds
            start_idx = max(0, min(start_idx, vector_length - 1))
            end_idx = max(0, min(end_idx, vector_length - 1))
            
            # Set stimulation period to 1
            if start_idx <= end_idx:
                annotation_vector[start_idx:end_idx + 1] = 1
        
        return annotation_vector
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple:
        """Validate processing parameters. Returns (is_valid, error_message)."""
        annotation_name = parameters.get('annotation_name', '').strip()
        if not annotation_name:
            return False, "Annotation name cannot be empty"
        
        framerate = parameters.get('framerate', 0)
        try:
            framerate = float(framerate)
            if framerate <= 0:
                return False, "Frame rate must be greater than 0"
        except (ValueError, TypeError):
            return False, "Frame rate must be a valid number"
        
        vector_dimension = parameters.get('vector_dimension', '')
        if not vector_dimension or not (vector_dimension.startswith('rows') or vector_dimension.startswith('columns')):
            return False, "Please select a valid vector dimension"
        
        stimulation_periods = parameters.get('stimulation_periods', [])
        if not stimulation_periods:
            return False, "At least one stimulation period must be specified"
        
        # Validate stimulation periods
        for i, period in enumerate(stimulation_periods):
            if len(period) != 2:
                return False, f"Stimulation period {i+1} must have start and end times"
            
            try:
                start_time, end_time = float(period[0]), float(period[1])
                if start_time < 0 or end_time < 0:
                    return False, f"Stimulation period {i+1} times must be non-negative"
                if start_time >= end_time:
                    return False, f"Stimulation period {i+1} start time must be less than end time"
            except (ValueError, TypeError):
                return False, f"Stimulation period {i+1} times must be valid numbers"
        
        return True, ""
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the dataset and create annotation vector."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        def update_progress(percent: float):
            if progress_callback:
                progress_callback(percent)
        
        try:
            # Step 1: Validate parameters (20%)
            update_progress(20.0)
            is_valid, error_msg = self.validate_parameters(parameters)
            if not is_valid:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Parameter validation failed: {error_msg}'
                }
            
            # Get parameters
            annotation_name = parameters.get('annotation_name').strip()
            vector_dimension = parameters.get('vector_dimension')
            framerate = float(parameters.get('framerate'))
            stimulation_periods = parameters.get('stimulation_periods', [])
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            # Step 2: Determine vector dimensions (40%)
            update_progress(40.0)
            try:
                vector_length = self.get_vector_length(dataset_name, vector_dimension)
            except Exception as e:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Failed to determine vector dimensions: {str(e)}'
                }
            
            # Step 3: Create annotation vector (60%)
            update_progress(60.0)
            annotation_vector = self.create_annotation_vector(vector_length, stimulation_periods, framerate)
            
            # Step 4: Process stimulation periods statistics (80%)
            update_progress(80.0)
            total_stimulation_samples = np.sum(annotation_vector)
            stimulation_percentage = (total_stimulation_samples / vector_length) * 100
            
            # Step 5: Save annotation file (90%)
            update_progress(90.0)
            output_dir = os.path.join("data", "datasets", dataset_name, "processed", "matrices")
            os.makedirs(output_dir, exist_ok=True)
            
            # Save as CSV file
            output_path = os.path.join(output_dir, f"{annotation_name}.csv")
            annotation_df = pd.DataFrame({annotation_name: annotation_vector})
            annotation_df.to_csv(output_path, index=False)
            
            # Calculate statistics
            statistics = {
                'annotation_name': annotation_name,
                'vector_length': vector_length,
                'vector_dimension': vector_dimension,
                'framerate': framerate,
                'stimulation_periods_count': len(stimulation_periods),
                'stimulation_periods': stimulation_periods,
                'total_stimulation_samples': int(total_stimulation_samples),
                'stimulation_percentage': round(stimulation_percentage, 2),
                'output_file': output_path
            }
            
            # Step 6: Completed (100%)
            update_progress(100.0)
            
            return {
                'success': True,
                'data': annotation_vector,
                'statistics': statistics,
                'output_path': output_path,
                'message': f'Data annotation completed. Vector length: {vector_length}, Stimulation: {stimulation_percentage:.1f}%. File saved to: {output_path}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Data annotation failed: {str(e)}'
            }


class IndexingProcessor(BaseProcessor):
    """Processor for generating sorting indices for matrix rows and columns."""
    
    def __init__(self):
        super().__init__("Indexing")
        self.description = "Generate sorting indices for matrix rows and columns"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'indexing_type': 'Row Indexing',
            'selected_file': '',
            'vector_column': '',
            'column_name': ''
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Indexing."""
        return [
            "Loading source CSV file",
            "Generating indices from vector data",
            "Checking for column name conflicts",
            "Saving index column to target file",
            "Completed"
        ]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate indexing parameters."""
        required_params = ['indexing_type', 'selected_file', 'vector_column', 'column_name', 'dataset_name']
        for param in required_params:
            if param not in parameters or not parameters[param]:
                return False
        
        # Check if indexing type is valid
        if parameters['indexing_type'] not in ['Row Indexing', 'Column Indexing']:
            return False
        
        return True
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the indexing operation."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        def update_progress(percent: float):
            if progress_callback:
                progress_callback(percent)
        
        try:
            # Step 1: Loading source CSV file (20%)
            update_progress(20.0)
            
            dataset_name = parameters['dataset_name']
            selected_file = parameters['selected_file']
            vector_column = parameters['vector_column']
            column_name = parameters['column_name']
            indexing_type = parameters['indexing_type']
            
            # Load the source CSV file
            if not os.path.exists(selected_file):
                raise FileNotFoundError(f"Source CSV file not found: {selected_file}")
            
            source_df = pd.read_csv(selected_file)
            
            # Check if the specified column exists
            if vector_column not in source_df.columns:
                raise ValueError(f"Column '{vector_column}' not found in {selected_file}")
            
            # Step 2: Generating indices from vector data (40%)
            update_progress(40.0)
            
            # Extract the vector data
            vector_data = source_df[vector_column]
            
            # Convert to numeric, handling any non-numeric values
            try:
                vector_numeric = pd.to_numeric(vector_data, errors='coerce')
            except Exception:
                raise ValueError(f"Column '{vector_column}' contains non-numeric data that cannot be converted")
            
            # Check for NaN values after conversion
            if vector_numeric.isna().any():
                raise ValueError(f"Column '{vector_column}' contains non-numeric values that cannot be processed")
            
            # Generate indices: highest value gets index 1, second highest gets index 2, etc.
            # Use rank with method='first' to handle ties consecutively
            indices = vector_numeric.rank(method='first', ascending=False).astype(int)
            
            # Step 3: Checking for column name conflicts (60%)
            update_progress(60.0)
            
            # Determine target file path
            if indexing_type == 'Row Indexing':
                target_file = f"Raster_row_labels_and_indices.csv"
            else:  # Column Indexing
                target_file = f"Raster_column_labels_and_indices.csv"
            
            target_path = os.path.join("data", "datasets", dataset_name, "processed", "matrices", target_file)
            
            # Check if target file exists and load it
            if os.path.exists(target_path):
                target_df = pd.read_csv(target_path)
                
                # Check if column name already exists
                if column_name in target_df.columns:
                    # This should be handled by the GUI, but we'll note it here
                    print(f"Warning: Column '{column_name}' already exists in {target_file}")
            else:
                # Create new target file with appropriate structure
                if indexing_type == 'Row Indexing':
                    target_df = pd.DataFrame({'row_labels': [f'C{i:03d}' for i in range(len(indices))]})
                else:
                    target_df = pd.DataFrame({'column_labels': range(len(indices))})
            
            # Step 4: Saving index column to target file (80%)
            update_progress(80.0)
            
            # Add the new index column
            target_df[column_name] = indices
            
            # Ensure the target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Save the updated file
            target_df.to_csv(target_path, index=False)
            
            # Step 5: Completed (100%)
            update_progress(100.0)
            
            # Prepare preview data for potential preview window
            preview_data = pd.DataFrame({
                'Original_Values': vector_numeric,
                'Indices': indices,
                'Sorted_Values': vector_numeric.iloc[indices.argsort()]
            })
            
            return {
                'success': True,
                'data': preview_data,
                'statistics': {
                    'indexing_type': indexing_type,
                    'source_file': selected_file,
                    'vector_column': vector_column,
                    'column_name': column_name,
                    'target_file': target_path,
                    'vector_length': len(vector_numeric),
                    'unique_values': len(vector_numeric.unique())
                },
                'output_path': target_path,
                'message': f'Indexing completed successfully. Added column "{column_name}" to {target_file}'
            }
            
        except FileNotFoundError as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'File not found: {str(e)}'
            }
        except ValueError as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Data validation error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Indexing failed: {str(e)}'
            }


class DataProcessingManager:
    """Manager class for coordinating different data processors."""
    
    def __init__(self):
        self.processors = {
            'Matrix Extraction': MatrixExtractionProcessor(),
            'Matrix Modification': MatrixModificationProcessor(),
            'Data Annotation': DataAnnotationProcessor(),
            'Indexing': IndexingProcessor()
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
        """Process a dataset with specified processor."""
        try:
            # Get dataset information
            dataset = DatasetOperations.get_dataset(dataset_id)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset with ID {dataset_id} not found'
                }
            
            # Get processor
            processor = self.get_processor(processor_name)
            if not processor:
                return {
                    'success': False,
                    'message': f'Processor "{processor_name}" not found'
                }
            
            # Prepare parameters with dataset information
            if parameters is None:
                parameters = {}
            parameters['dataset_name'] = dataset.name
            parameters['dataset_path'] = dataset.file_path
            parameters['dataset_format'] = dataset.file_format
            parameters['job_name'] = job_name
            
            # Let processor handle everything including progress
            result = processor.process_with_progress(parameters, progress_callback)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Processing failed: {str(e)}'
            }
