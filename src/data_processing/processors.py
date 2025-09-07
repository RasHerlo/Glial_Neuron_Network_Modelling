"""
Data processing modules with database integration.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import os
import json
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from ..database.operations import DatasetOperations, ProcessingJobOperations
from ..utils.folder_manager import DatasetFolderManager


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
        # Get workspace-aware output directory
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            raise ValueError(f"Dataset '{dataset_name}' not found")
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            raise ValueError(f"Dataset folder not found for '{dataset_name}'")
        
        output_dir = folder_manager.get_processed_data_path(dataset_folder, "matrices")
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
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return []
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return []
        
        matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
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
            
            # Construct matrix file path using workspace-aware folder manager
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            matrix_file_path = os.path.join(matrices_path, f"{matrix_name}.npy")
            
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
            output_dir = matrices_path  # Use the same workspace-aware path we already resolved
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
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return {}
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return {}
        
        matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
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
        """Get vector length based on dimension choice from dropdown selection."""
        # Parse the vector length directly from the dropdown selection
        # Expected format: "rows = 958" or "columns = 2476"
        if '=' in dimension_choice:
            try:
                # Extract the number after the '=' sign
                vector_length = int(dimension_choice.split('=')[1].strip())
                return vector_length
            except (ValueError, IndexError) as e:
                raise ValueError(f"Could not parse vector length from dimension choice '{dimension_choice}': {e}")
        
        # Fallback to original logic if no '=' found (for backwards compatibility)
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
            # Get workspace-aware output directory
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            output_dir = folder_manager.get_processed_data_path(dataset_folder, "matrices")
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
            
            # Get workspace-aware target path
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            target_path = os.path.join(matrices_path, target_file)
            
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


class RuzickaSimilarityProcessor(BaseProcessor):
    """Processor for calculating Ruzicka similarity matrices between neurons."""
    
    def __init__(self):
        super().__init__("Ruzicka Similarity")
        self.description = "Calculate Ruzicka similarity matrix between neurons"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'matrix': None,  # Will be populated dynamically from available matrices
            'matrix_name': 'Ruzicka Matrix'  # Default output name
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Ruzicka Similarity."""
        return [
            "Validating matrix file",
            "Loading matrix data",
            "Calculating Ruzicka similarities",
            "Saving similarity matrix",
            "Completed"
        ]
    
    def find_matrix_files(self, dataset_name: str) -> List[str]:
        """Find all .npy files in the dataset's processed/matrices folder."""
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return []
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return []
        
        matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
        if not os.path.exists(matrices_path):
            return []
        
        matrix_files = []
        for file in os.listdir(matrices_path):
            if file.endswith('.npy'):
                # Remove .npy extension: "Raster_matrix.npy" -> "Raster_matrix"
                base_name = file[:-4]  # Remove last 4 characters (.npy)
                matrix_files.append(base_name)
        
        return sorted(matrix_files)  # Sort alphabetically
    
    def calculate_ruzicka_similarity(self, neuron1: np.ndarray, neuron2: np.ndarray) -> float:
        """Calculate Ruzicka similarity between two neurons.
        
        Ruzicka similarity = sum(min(neuron1, neuron2)) / sum(max(neuron1, neuron2))
        """
        # Handle NaN values - if either neuron has NaN, return NaN
        if np.any(np.isnan(neuron1)) or np.any(np.isnan(neuron2)):
            return np.nan
        
        # Calculate min and max for each pair of values
        min_vals = np.minimum(neuron1, neuron2)
        max_vals = np.maximum(neuron1, neuron2)
        
        # Sum the mins and maxes
        sum_min = np.sum(min_vals)
        sum_max = np.sum(max_vals)
        
        # Avoid division by zero
        if sum_max == 0:
            return 0.0
        
        return sum_min / sum_max
    
    def calculate_ruzicka_matrix(self, matrix_data: np.ndarray) -> np.ndarray:
        """Calculate Ruzicka similarity matrix for all pairs of neurons.
        
        Args:
            matrix_data: 2D array where rows are neurons and columns are time points
            
        Returns:
            2D array where (i,j) contains Ruzicka similarity between neuron i and neuron j
        """
        n_neurons = matrix_data.shape[0]
        similarity_matrix = np.zeros((n_neurons, n_neurons))
        
        # Calculate similarity for each pair of neurons
        for i in range(n_neurons):
            for j in range(n_neurons):
                similarity_matrix[i, j] = self.calculate_ruzicka_similarity(
                    matrix_data[i, :], matrix_data[j, :]
                )
        
        return similarity_matrix
    
    def get_preview(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a preview of the Ruzicka similarity matrix."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        try:
            # Get parameters
            matrix_name = parameters.get('matrix')
            output_matrix_name = parameters.get('matrix_name', 'Ruzicka Matrix')
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            if not matrix_name:
                return {
                    'success': False,
                    'message': 'No matrix selected for Ruzicka similarity calculation'
                }
            
            # Construct matrix file path using workspace-aware folder manager
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            matrix_file_path = os.path.join(matrices_path, f"{matrix_name}.npy")
            
            # Validate matrix file exists
            if not os.path.exists(matrix_file_path):
                return {
                    'success': False,
                    'message': f'Matrix file not found: {matrix_file_path}'
                }
            
            # Load matrix data
            matrix_data = np.load(matrix_file_path)
            
            # Validate matrix is 2D
            if len(matrix_data.shape) != 2:
                return {
                    'success': False,
                    'message': f'Matrix must be 2D, got shape: {matrix_data.shape}'
                }
            
            # Calculate Ruzicka similarity matrix
            similarity_matrix = self.calculate_ruzicka_matrix(matrix_data)
            
            # Generate output filename with matrix suffix
            matrix_suffix = matrix_name.split('_')[-1] if '_' in matrix_name else matrix_name
            output_filename = f"{output_matrix_name}_{matrix_suffix}"
            
            # Create preview (show first 10x10 elements)
            preview_size = min(10, similarity_matrix.shape[0], similarity_matrix.shape[1])
            preview_matrix = similarity_matrix[:preview_size, :preview_size]
            
            # Convert to DataFrame for better display
            import pandas as pd
            preview_df = pd.DataFrame(preview_matrix)
            
            return {
                'success': True,
                'matrix_name': output_filename,
                'full_shape': similarity_matrix.shape,
                'preview_shape': preview_matrix.shape,
                'preview_matrix': preview_df,
                'transposed': False,
                'message': f'Ruzicka similarity matrix preview generated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to generate Ruzicka similarity preview: {str(e)}'
            }
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the matrix to calculate Ruzicka similarity matrix."""
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
            output_matrix_name = parameters.get('matrix_name', 'Ruzicka Matrix')
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            if not matrix_name:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': 'No matrix selected for Ruzicka similarity calculation'
                }
            
            # Construct matrix file path using workspace-aware folder manager
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            matrix_file_path = os.path.join(matrices_path, f"{matrix_name}.npy")
            
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
            
            # Step 3: Calculate Ruzicka similarity matrix (70%)
            update_progress(70.0)
            similarity_matrix = self.calculate_ruzicka_matrix(matrix_data)
            
            # Generate output filename with matrix suffix
            matrix_suffix = matrix_name.split('_')[-1] if '_' in matrix_name else matrix_name
            output_filename = f"{output_matrix_name}_{matrix_suffix}"
            
            # Step 4: Save similarity matrix (90%)
            update_progress(90.0)
            output_dir = matrices_path  # Use the same workspace-aware path we already resolved
            os.makedirs(output_dir, exist_ok=True)
            
            # Save as .npy file
            output_path = os.path.join(output_dir, f"{output_filename}.npy")
            np.save(output_path, similarity_matrix)
            
            # Calculate statistics
            statistics = {
                'input_matrix_shape': matrix_data.shape,
                'similarity_matrix_shape': similarity_matrix.shape,
                'input_matrix_name': matrix_name,
                'output_matrix_name': output_filename,
                'similarity_matrix_stats': {
                    'mean': float(np.nanmean(similarity_matrix)),
                    'std': float(np.nanstd(similarity_matrix)),
                    'min': float(np.nanmin(similarity_matrix)),
                    'max': float(np.nanmax(similarity_matrix)),
                    'nan_count': int(np.isnan(similarity_matrix).sum())
                },
                'output_file': output_path,
                'output_format': '.npy'
            }
            
            # Step 5: Completed (100%)
            update_progress(100.0)
            
            return {
                'success': True,
                'data': similarity_matrix,
                'statistics': statistics,
                'output_path': output_path,
                'message': f'Ruzicka similarity matrix calculated successfully. Output saved to: {output_path}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Ruzicka similarity calculation failed: {str(e)}'
            }


class HierarchicalClusteringProcessor(BaseProcessor):
    """Processor for performing hierarchical clustering on matrices."""
    
    def __init__(self):
        super().__init__("Hierarchical Clustering")
        self.description = "Perform agglomerative hierarchical clustering on matrix data"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'matrix': None,  # Will be populated dynamically from available matrices
            'clustering_method': 'ward',
            'distance_metric': 'euclidean',
            'clustering_dimension': 'Cluster Rows (Neurons)',
            'output_name_prefix': 'HAC'  # Will be auto-generated with matrix suffix
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Hierarchical Clustering."""
        return [
            "Validating matrix file",
            "Loading matrix data", 
            "Preparing data for clustering",
            "Performing hierarchical clustering",
            "Saving clustering results",
            "Completed"
        ]
    
    def find_matrix_files(self, dataset_name: str) -> List[str]:
        """Find all .npy files in the dataset's processed/matrices folder."""
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return []
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return []
        
        matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
        if not os.path.exists(matrices_path):
            return []
        
        matrix_files = []
        for file in os.listdir(matrices_path):
            if file.endswith('.npy'):
                # Remove .npy extension: "Raster_matrix.npy" -> "Raster_matrix"
                base_name = file[:-4]  # Remove last 4 characters (.npy)
                matrix_files.append(base_name)
        
        return sorted(matrix_files)  # Sort alphabetically
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple:
        """Validate clustering parameters. Returns (is_valid, error_message)."""
        matrix_name = parameters.get('matrix', '').strip()
        if not matrix_name:
            return False, "No matrix selected for clustering"
        
        clustering_method = parameters.get('clustering_method', '')
        valid_methods = ['ward', 'complete', 'average', 'single']
        if clustering_method not in valid_methods:
            return False, f"Invalid clustering method. Must be one of: {valid_methods}"
        
        distance_metric = parameters.get('distance_metric', '')
        valid_metrics = ['euclidean', 'correlation', 'cosine', 'manhattan']
        if distance_metric not in valid_metrics:
            return False, f"Invalid distance metric. Must be one of: {valid_metrics}"
        
        clustering_dimension = parameters.get('clustering_dimension', '')
        valid_dimensions = ['Cluster Rows (Neurons)', 'Cluster Columns (Time Points)']
        if clustering_dimension not in valid_dimensions:
            return False, f"Invalid clustering dimension. Must be one of: {valid_dimensions}"
        
        # Note: output_name_prefix is auto-generated, so no validation needed
        
        return True, ""
    
    def generate_output_prefix(self, matrix_name: str) -> str:
        """Generate output prefix: HAC + matrix suffix (e.g., HAC_norm01)."""
        matrix_suffix = matrix_name.split('_')[-1] if '_' in matrix_name else matrix_name
        return f"HAC_{matrix_suffix}"
    
    def generate_folder_name(self, clustering_method: str, distance_metric: str) -> str:
        """Generate folder name: HAC + method + first 4 letters of metric (e.g., HAC_ward_eucl)."""
        metric_abbrev = distance_metric[:4]  # First 4 letters
        return f"HAC_{clustering_method}_{metric_abbrev}"
    
    def convert_clustering_to_ranking(self, cluster_indices: np.ndarray) -> np.ndarray:
        """Convert hierarchical clustering indices to ranking format for Figure Generation GUI.
        
        Hierarchical clustering returns positional indices [2, 0, 1] meaning:
        - Item at position 2 should be first
        - Item at position 0 should be second  
        - Item at position 1 should be third
        
        Figure Generation GUI expects ranking format [2, 3, 1] meaning:
        - Item at position 0 gets rank 2
        - Item at position 1 gets rank 3
        - Item at position 2 gets rank 1
        
        Args:
            cluster_indices: Array of positional indices from hierarchical clustering
            
        Returns:
            Array of ranking values compatible with Figure Generation GUI
        """
        ranking = np.zeros(len(cluster_indices), dtype=int)
        for rank, original_pos in enumerate(cluster_indices):
            ranking[original_pos] = rank + 1  # +1 because rankings start at 1
        return ranking
    
    def add_clustering_to_labels_file(self, dataset_name: str, folder_name: str, 
                                    cluster_indices: np.ndarray, cluster_rows: bool):
        """Add clustering indices as a column to the relevant labels_and_indices file.
        
        Args:
            dataset_name: Name of the dataset
            folder_name: Name of the clustering folder (e.g., HAC_ward_eucl)
            cluster_indices: Array of clustering indices (will be converted to ranking format)
            cluster_rows: If True, update row labels file; if False, update column labels file
        """
        # Determine which labels file to update
        if cluster_rows:
            labels_filename = "Raster_row_labels_and_indices.csv"
        else:
            labels_filename = "Raster_column_labels_and_indices.csv"
        
        labels_file_path = os.path.join("data", "datasets", dataset_name, "processed", "matrices", labels_filename)
        
        try:
            # Convert clustering indices to ranking format for GUI compatibility
            ranking_indices = self.convert_clustering_to_ranking(cluster_indices)
            
            # Check if labels file exists
            if os.path.exists(labels_file_path):
                # Load existing labels file
                labels_df = pd.read_csv(labels_file_path)
                
                # Verify the number of indices matches the file length
                if len(ranking_indices) != len(labels_df):
                    print(f"Warning: Clustering indices length ({len(ranking_indices)}) doesn't match labels file length ({len(labels_df)})")
                    return
                
                # Add the clustering column (use folder name as column name)
                labels_df[folder_name] = ranking_indices
                
                # Save the updated file
                labels_df.to_csv(labels_file_path, index=False)
                print(f"Added clustering column '{folder_name}' to {labels_filename}")
                
            else:
                # Create new labels file if it doesn't exist
                print(f"Labels file {labels_filename} not found. Creating new file.")
                
                if cluster_rows:
                    # Create row labels file
                    labels_df = pd.DataFrame({
                        'row_labels': [f'Neuron_{i:04d}' for i in range(len(ranking_indices))],
                        folder_name: ranking_indices
                    })
                else:
                    # Create column labels file
                    labels_df = pd.DataFrame({
                        'column_labels': [f'Time_{i:04d}' for i in range(len(ranking_indices))],
                        folder_name: ranking_indices
                    })
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(labels_file_path), exist_ok=True)
                
                # Save the new file
                labels_df.to_csv(labels_file_path, index=False)
                print(f"Created new {labels_filename} with clustering column '{folder_name}'")
                
        except Exception as e:
            print(f"Error updating labels file {labels_filename}: {str(e)}")
            # Don't fail the entire clustering process if labels file update fails
    
    def perform_hierarchical_clustering(self, matrix_data: np.ndarray, method: str, 
                                      metric: str, cluster_rows: bool) -> tuple:
        """Perform hierarchical clustering and return linkage matrix and indices.
        
        Args:
            matrix_data: 2D numpy array
            method: Clustering method ('ward', 'complete', 'average', 'single')
            metric: Distance metric ('euclidean', 'correlation', 'cosine', 'manhattan')
            cluster_rows: If True, cluster rows; if False, cluster columns
            
        Returns:
            tuple: (linkage_matrix, cluster_indices)
        """
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import pdist
        
        # Prepare data for clustering
        if cluster_rows:
            # Cluster rows (neurons) - each row is a data point
            data_for_clustering = matrix_data
        else:
            # Cluster columns (time points) - transpose so each column becomes a row
            data_for_clustering = matrix_data.T
        
        # Handle special case for ward method (only works with euclidean)
        if method == 'ward' and metric != 'euclidean':
            print(f"Warning: Ward clustering is incompatible with {metric} distance.")
            print(f"Ward method requires Euclidean distance for proper variance calculations.")
            print(f"Automatically switching to Euclidean distance.")
            metric = 'euclidean'
        
        # Calculate pairwise distances
        if metric == 'correlation':
            # Use 1 - correlation as distance
            distances = pdist(data_for_clustering, metric='correlation')
        else:
            distances = pdist(data_for_clustering, metric=metric)
        
        # Perform hierarchical clustering
        linkage_matrix = linkage(distances, method=method)
        
        # Get the order of indices from the clustering
        from scipy.cluster.hierarchy import leaves_list
        cluster_indices = leaves_list(linkage_matrix)
        
        return linkage_matrix, cluster_indices
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process the matrix with hierarchical clustering."""
        if parameters is None:
            parameters = self.get_default_parameters()
        
        def update_progress(percent: float):
            if progress_callback:
                progress_callback(percent)
        
        try:
            # Step 1: Validate parameters and matrix file (20%)
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
            matrix_name = parameters.get('matrix')
            clustering_method = parameters.get('clustering_method', 'ward')
            distance_metric = parameters.get('distance_metric', 'euclidean')
            clustering_dimension = parameters.get('clustering_dimension', 'Cluster Rows (Neurons)')
            dataset_name = parameters.get('dataset_name', 'unknown_dataset')
            
            # Generate output prefix and folder name
            output_prefix = self.generate_output_prefix(matrix_name)
            folder_name = self.generate_folder_name(clustering_method, distance_metric)
            
            # Determine if clustering rows or columns
            cluster_rows = clustering_dimension == 'Cluster Rows (Neurons)'
            
            # Construct matrix file path using workspace-aware folder manager
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            matrix_file_path = os.path.join(matrices_path, f"{matrix_name}.npy")
            
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
            
            # Step 3: Prepare data for clustering (50%)
            update_progress(50.0)
            # Check for NaN values and handle them
            if np.any(np.isnan(matrix_data)):
                nan_count = np.sum(np.isnan(matrix_data))
                print(f"Warning: {nan_count} NaN values detected in matrix. These will affect clustering results.")
            
            # Step 4: Perform hierarchical clustering (70%)
            update_progress(70.0)
            try:
                linkage_matrix, cluster_indices = self.perform_hierarchical_clustering(
                    matrix_data, clustering_method, distance_metric, cluster_rows
                )
            except Exception as e:
                return {
                    'success': False,
                    'data': None,
                    'statistics': None,
                    'message': f'Clustering failed: {str(e)}'
                }
            
            # Step 5: Save clustering results (90%)
            update_progress(90.0)
            # Create output directory with folder structure: {workspace}/datasets/{dataset}/processed/matrices/{HAC_method_metric}/
            base_matrices_dir = matrices_path  # Use the same workspace-aware path we already resolved
            output_dir = os.path.join(base_matrices_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filenames
            linkage_output_path = os.path.join(output_dir, f"{output_prefix}_linkage_matrix.npy")
            indices_output_path = os.path.join(output_dir, f"{output_prefix}_cluster_indices.csv")
            sorted_matrix_output_path = os.path.join(output_dir, f"{output_prefix}_sorted_matrix.npy")
            
            # Save linkage matrix
            np.save(linkage_output_path, linkage_matrix)
            
            # Save cluster indices
            dimension_label = "row_indices" if cluster_rows else "column_indices"
            indices_df = pd.DataFrame({dimension_label: cluster_indices})
            indices_df.to_csv(indices_output_path, index=False)
            
            # Create and save sorted matrix
            if cluster_rows:
                sorted_matrix = matrix_data[cluster_indices, :]
            else:
                sorted_matrix = matrix_data[:, cluster_indices]
            
            np.save(sorted_matrix_output_path, sorted_matrix)
            
            # Add clustering indices to the relevant labels_and_indices file
            self.add_clustering_to_labels_file(dataset_name, folder_name, cluster_indices, cluster_rows)
            
            # Calculate statistics
            labels_file = "Raster_row_labels_and_indices.csv" if cluster_rows else "Raster_column_labels_and_indices.csv"
            statistics = {
                'input_matrix_shape': matrix_data.shape,
                'clustering_method': clustering_method,
                'distance_metric': distance_metric,
                'clustering_dimension': clustering_dimension,
                'cluster_rows': cluster_rows,
                'n_clusters_performed': len(cluster_indices),
                'linkage_matrix_shape': linkage_matrix.shape,
                'output_prefix': output_prefix,
                'output_folder': folder_name,
                'labels_file_updated': labels_file,
                'clustering_column_name': folder_name,
                'output_files': {
                    'linkage_matrix': linkage_output_path,
                    'cluster_indices': indices_output_path,
                    'sorted_matrix': sorted_matrix_output_path
                },
                'matrix_stats': {
                    'mean': float(np.nanmean(matrix_data)),
                    'std': float(np.nanstd(matrix_data)),
                    'min': float(np.nanmin(matrix_data)),
                    'max': float(np.nanmax(matrix_data)),
                    'nan_count': int(np.sum(np.isnan(matrix_data)))
                }
            }
            
            # Step 6: Completed (100%)
            update_progress(100.0)
            
            return {
                'success': True,
                'data': {
                    'linkage_matrix': linkage_matrix,
                    'cluster_indices': cluster_indices,
                    'sorted_matrix': sorted_matrix
                },
                'statistics': statistics,
                'output_path': output_dir,
                'message': f'Hierarchical clustering completed successfully. Files saved to: {output_dir}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'statistics': None,
                'message': f'Hierarchical clustering failed: {str(e)}'
            }


class MatrixAssembleProcessor(BaseProcessor):
    """Processor for assembling matrices by row-wise concatenation."""
    
    def __init__(self):
        super().__init__("MatrixAssemble")
        self.description = "Assemble matrices by row-wise concatenation from different datasets"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'base_set': '',
            'base_matrix': '',
            'add_set': '',
            'add_matrix': '',
            'new_dataset_name': ''
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Matrix Assembly."""
        return [
            "Loading base matrix",
            "Loading add matrix", 
            "Validating matrix compatibility",
            "Concatenating matrices",
            "Creating new dataset folder",
            "Saving assembled matrix",
            "Completed"
        ]
    
    def find_dataset_folders(self) -> List[str]:
        """Find available dataset folders in the datasets directory."""
        folder_manager = DatasetFolderManager()
        datasets_dir = folder_manager.datasets_dir
        
        if not os.path.exists(datasets_dir):
            return []
        
        dataset_folders = []
        for item in os.listdir(datasets_dir):
            item_path = os.path.join(datasets_dir, item)
            if os.path.isdir(item_path):
                dataset_folders.append(item)
        
        return sorted(dataset_folders)
    
    def find_raster_matrices(self, dataset_name: str) -> List[str]:
        """Find available Raster matrices for the given dataset."""
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return []
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return []
        
        matrix_dir = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
        if not os.path.exists(matrix_dir):
            return []
        
        matrix_files = []
        for file in os.listdir(matrix_dir):
            if file.startswith('Raster') and file.endswith('.npy'):
                # Extract the matrix name without extension
                matrix_name = os.path.splitext(file)[0]
                matrix_files.append(matrix_name)
        
        return sorted(matrix_files)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate matrix assembly parameters."""
        base_set = parameters.get('base_set')
        base_matrix = parameters.get('base_matrix')
        add_set = parameters.get('add_set')
        add_matrix = parameters.get('add_matrix')
        new_dataset_name = parameters.get('new_dataset_name')
        
        # Check if all required parameters are provided
        if not all([base_set, base_matrix, add_set, add_matrix, new_dataset_name]):
            return False
        
        # Check if datasets exist
        available_datasets = self.find_dataset_folders()
        if base_set not in available_datasets or add_set not in available_datasets:
            return False
        
        # Check if matrices exist
        base_matrices = self.find_raster_matrices(base_set)
        add_matrices = self.find_raster_matrices(add_set)
        
        if base_matrix not in base_matrices or add_matrix not in add_matrices:
            return False
        
        # Check if new dataset name is valid (no special characters, not empty)
        if not new_dataset_name.strip() or '/' in new_dataset_name or '\\' in new_dataset_name:
            return False
        
        return True
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process matrix assembly with progress updates."""
        try:
            if progress_callback:
                progress_callback(0.0)
            
            # Validate parameters
            if not self.validate_parameters(parameters):
                return {
                    'success': False,
                    'message': 'Invalid parameters for matrix assembly'
                }
            
            base_set = parameters.get('base_set')
            base_matrix = parameters.get('base_matrix')
            add_set = parameters.get('add_set')
            add_matrix = parameters.get('add_matrix')
            new_dataset_name = parameters.get('new_dataset_name')
            
            # Step 1: Load base matrix (0-20%)
            if progress_callback:
                progress_callback(5.0)
            
            # Get workspace-aware paths for base matrix
            folder_manager = DatasetFolderManager()
            base_dataset = DatasetOperations.get_dataset_by_name(base_set)
            if not base_dataset:
                return {
                    'success': False,
                    'message': f'Base dataset "{base_set}" not found'
                }
            
            base_dataset_folder = folder_manager.get_dataset_folder(base_dataset.id, base_set)
            if not base_dataset_folder:
                return {
                    'success': False,
                    'message': f'Base dataset folder not found for "{base_set}"'
                }
            
            base_matrices_path = folder_manager.get_processed_data_path(base_dataset_folder, "matrices")
            base_matrix_path = os.path.join(base_matrices_path, f"{base_matrix}.npy")
            base_data = np.load(base_matrix_path)
            
            if progress_callback:
                progress_callback(20.0)
            
            # Step 2: Load add matrix (20-40%)
            # Get workspace-aware paths for add matrix
            add_dataset = DatasetOperations.get_dataset_by_name(add_set)
            if not add_dataset:
                return {
                    'success': False,
                    'message': f'Add dataset "{add_set}" not found'
                }
            
            add_dataset_folder = folder_manager.get_dataset_folder(add_dataset.id, add_set)
            if not add_dataset_folder:
                return {
                    'success': False,
                    'message': f'Add dataset folder not found for "{add_set}"'
                }
            
            add_matrices_path = folder_manager.get_processed_data_path(add_dataset_folder, "matrices")
            add_matrix_path = os.path.join(add_matrices_path, f"{add_matrix}.npy")
            add_data = np.load(add_matrix_path)
            
            if progress_callback:
                progress_callback(40.0)
            
            # Step 3: Validate matrix compatibility (40-50%)
            if base_data.shape[0] != add_data.shape[0]:
                return {
                    'success': False,
                    'message': f'Matrix compatibility error: Base matrix has {base_data.shape[0]} rows, Add matrix has {add_data.shape[0]} rows. Row counts must match for concatenation.'
                }
            
            if progress_callback:
                progress_callback(50.0)
            
            # Step 4: Concatenate matrices (50-70%)
            assembled_matrix = np.concatenate([base_data, add_data], axis=1)
            
            if progress_callback:
                progress_callback(70.0)
            
            # Step 5: Create new dataset folder structure (70-80%)
            # Create new dataset using workspace-aware folder manager
            new_dataset_folder = folder_manager.create_dataset_folder(999999, new_dataset_name)  # Temporary ID
            new_matrices_dir = folder_manager.get_processed_data_path(new_dataset_folder, "matrices")
            
            os.makedirs(new_matrices_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback(80.0)
            
            # Step 6: Save assembled matrix (80-95%)
            assembled_matrix_name = f"Raster_matrix_assembled_{base_matrix.split('_')[-1]}_{add_matrix.split('_')[-1]}"
            assembled_matrix_path = os.path.join(new_matrices_dir, f"{assembled_matrix_name}.npy")
            
            np.save(assembled_matrix_path, assembled_matrix)
            
            if progress_callback:
                progress_callback(95.0)
            
            # Step 7: Create metadata file (95-100%)
            metadata = {
                'assembly_info': {
                    'base_dataset': base_set,
                    'base_matrix': base_matrix,
                    'add_dataset': add_set,
                    'add_matrix': add_matrix,
                    'assembly_method': 'row_wise_concatenation',
                    'assembled_shape': assembled_matrix.shape,
                    'base_shape': base_data.shape,
                    'add_shape': add_data.shape,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            metadata_path = os.path.join(new_matrices_dir, f"{assembled_matrix_name}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if progress_callback:
                progress_callback(100.0)
            
            return {
                'success': True,
                'message': f'Matrix assembly completed successfully. Assembled matrix shape: {assembled_matrix.shape}',
                'output_path': assembled_matrix_path,
                'assembled_shape': assembled_matrix.shape,
                'base_shape': base_data.shape,
                'add_shape': add_data.shape
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Matrix assembly failed: {str(e)}'
            }


class DimensionalityReductionProcessor(BaseProcessor):
    """Processor for dimensionality reduction analysis of matrices."""
    
    def __init__(self):
        super().__init__("Dimensionality Reduction")
        self.description = "Perform dimensionality reduction analysis on matrices using various methods"
    
    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            'matrix': '',
            'dim_red_type': 'Linear',
            'method': 'PCA'
        }
    
    def get_progress_steps(self) -> List[str]:
        """Return progress step descriptions for Dimensionality Reduction."""
        return [
            "Loading matrix data",
            "Preprocessing data", 
            "Computing PCA",
            "Saving results",
            "Completed"
        ]
    
    def find_matrix_files(self, dataset_name: str) -> List[str]:
        """Find available matrix files for the given dataset."""
        folder_manager = DatasetFolderManager()
        dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        if not dataset:
            return []
        
        dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
        if not dataset_folder:
            return []
        
        matrix_dir = folder_manager.get_processed_data_path(dataset_folder, "matrices")
        
        if not os.path.exists(matrix_dir):
            return []
        
        matrix_files = []
        for file in os.listdir(matrix_dir):
            if file.endswith('.npy') and 'Raster_matrix' in file:
                # Extract the matrix name without extension
                matrix_name = os.path.splitext(file)[0]
                matrix_files.append(matrix_name)
        
        return sorted(matrix_files)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate dimensionality reduction parameters."""
        if not parameters.get('matrix'):
            return False
        
        dim_red_type = parameters.get('dim_red_type')
        method = parameters.get('method')
        
        # Validate method based on dimension reduction type
        valid_methods = {
            'Linear': ['PCA', 'LCA', 'SVD'],
            'Non-Linear': ['t-SNE', 'UMAP'],
            'Other': ['CNMF']
        }
        
        if dim_red_type not in valid_methods:
            return False
        
        if method not in valid_methods[dim_red_type]:
            return False
        
        # PCA-specific validation
        if dim_red_type == 'Linear' and method == 'PCA':
            pca_dimension = parameters.get('pca_dimension')
            if pca_dimension not in ['rows', 'columns']:
                return False
            
            pca_output_filename = parameters.get('pca_output_filename')
            if not pca_output_filename or not pca_output_filename.strip():
                return False
        
        return True
    
    def process_with_progress(self, parameters: Dict[str, Any] = None, 
                            progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process dimensionality reduction with progress updates."""
        try:
            if progress_callback:
                progress_callback(0.0)
            
            # Validate parameters
            if not self.validate_parameters(parameters):
                return {
                    'success': False,
                    'message': 'Invalid parameters for dimensionality reduction'
                }
            
            dataset_name = parameters.get('dataset_name')
            matrix_name = parameters.get('matrix')
            dim_red_type = parameters.get('dim_red_type')
            method = parameters.get('method')
            
            # Route to appropriate method
            if dim_red_type == 'Linear' and method == 'PCA':
                return self.process_pca(parameters, progress_callback)
            else:
                return {
                    'success': False,
                    'message': f'Method {method} ({dim_red_type}) is not yet implemented'
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Dimensionality reduction failed: {str(e)}'
            }
    
    def process_pca(self, parameters: Dict[str, Any], 
                   progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Process PCA analysis with progress updates."""
        try:
            dataset_name = parameters.get('dataset_name')
            matrix_name = parameters.get('matrix')
            pca_dimension = parameters.get('pca_dimension', 'columns')
            output_filename = parameters.get('pca_output_filename', 'PCA_analysis')
            
            # Step 1: Loading matrix data (0-20%)
            if progress_callback:
                progress_callback(0.0)
            
            # Get workspace-aware matrix path
            folder_manager = DatasetFolderManager()
            dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if not dataset:
                return {
                    'success': False,
                    'message': f'Dataset "{dataset_name}" not found'
                }
            
            dataset_folder = folder_manager.get_dataset_folder(dataset.id, dataset_name)
            if not dataset_folder:
                return {
                    'success': False,
                    'message': f'Dataset folder not found for "{dataset_name}"'
                }
            
            matrices_path = folder_manager.get_processed_data_path(dataset_folder, "matrices")
            matrix_path = os.path.join(matrices_path, f"{matrix_name}.npy")
            
            if not os.path.exists(matrix_path):
                return {
                    'success': False,
                    'message': f'Matrix file not found: {matrix_path}'
                }
            
            # Load the matrix
            matrix = np.load(matrix_path)
            
            # Validate matrix dimensions
            if matrix.size == 0:
                return {
                    'success': False,
                    'message': 'Matrix is empty'
                }
            
            if matrix.ndim != 2:
                return {
                    'success': False,
                    'message': f'Matrix must be 2D, got {matrix.ndim}D'
                }
            
            rows, cols = matrix.shape
            if rows < 2 or cols < 2:
                return {
                    'success': False,
                    'message': f'Matrix too small for PCA: {rows}x{cols}'
                }
            
            if progress_callback:
                progress_callback(20.0)
            
            # Step 2: Preprocessing data (20-40%)
            # Prepare data based on dimension selection
            if pca_dimension == 'columns':
                # PCA in column space: transpose so each column becomes a sample
                data = matrix.T  # Shape: (cols, rows)
                analysis_info = f"PCA in column space: analyzing {cols} columns with {rows} features each"
            else:  # rows
                # PCA in row space: each row is a sample
                data = matrix  # Shape: (rows, cols)
                analysis_info = f"PCA in row space: analyzing {rows} rows with {cols} features each"
            
            # Check if we have enough samples for PCA
            n_samples, n_features = data.shape
            if n_samples < 2:
                return {
                    'success': False,
                    'message': f'Need at least 2 samples for PCA, got {n_samples}'
                }
            
            # Center and standardize the data
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data)
            
            if progress_callback:
                progress_callback(40.0)
            
            # Step 3: Computing PCA (40-70%)
            # Initialize PCA with all components
            n_components = min(n_samples, n_features)
            pca = PCA(n_components=n_components)
            
            # Fit PCA and transform data
            transformed_data = pca.fit_transform(data_scaled)
            
            if progress_callback:
                progress_callback(70.0)
            
            # Step 4: Saving results (70-90%)
            # Create output directory using workspace-aware path
            pca_path = folder_manager.get_processed_data_path(dataset_folder, "pca")
            output_dir = os.path.join(pca_path, output_filename)
            os.makedirs(output_dir, exist_ok=True)
            
            # Save principal components
            np.save(os.path.join(output_dir, "principal_components.npy"), pca.components_)
            
            # Save explained variance
            np.save(os.path.join(output_dir, "explained_variance.npy"), pca.explained_variance_)
            
            # Save explained variance ratio
            np.save(os.path.join(output_dir, "explained_variance_ratio.npy"), pca.explained_variance_ratio_)
            
            # Save cumulative variance
            cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
            np.save(os.path.join(output_dir, "cumulative_variance.npy"), cumulative_variance)
            
            # Save transformed data (data projected onto PCs)
            np.save(os.path.join(output_dir, "transformed_data.npy"), transformed_data)
            
            # Save loadings (components transposed for easier interpretation)
            loadings = pca.components_.T
            np.save(os.path.join(output_dir, "loadings.npy"), loadings)
            
            # Save scaler parameters
            scaler_params = {
                'mean': scaler.mean_.tolist(),
                'scale': scaler.scale_.tolist()
            }
            
            # Create summary CSV
            summary_data = {
                'Component': [f'PC{i+1}' for i in range(len(pca.explained_variance_))],
                'Explained_Variance': pca.explained_variance_.tolist(),
                'Explained_Variance_Ratio': pca.explained_variance_ratio_.tolist(),
                'Cumulative_Variance_Ratio': cumulative_variance.tolist()
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(os.path.join(output_dir, "pca_summary.csv"), index=False)
            
            # Save parameters and metadata
            pca_metadata = {
                'analysis_info': analysis_info,
                'original_matrix': matrix_name,
                'original_shape': [int(rows), int(cols)],
                'analysis_dimension': pca_dimension,
                'data_shape_for_pca': [int(n_samples), int(n_features)],
                'n_components': int(n_components),
                'total_explained_variance_ratio': float(cumulative_variance[-1]),
                'scaler_parameters': scaler_params,
                'processing_parameters': {
                    'dim_red_type': parameters.get('dim_red_type'),
                    'method': parameters.get('method'),
                    'pca_dimension': pca_dimension,
                    'output_filename': output_filename
                },
                'timestamp': datetime.now().isoformat()
            }
            
            with open(os.path.join(output_dir, "pca_parameters.json"), 'w') as f:
                json.dump(pca_metadata, f, indent=2)
            
            if progress_callback:
                progress_callback(90.0)
            
            # Step 5: Completed (90-100%)
            if progress_callback:
                progress_callback(100.0)
            
            return {
                'success': True,
                'message': f'PCA analysis completed successfully. {n_components} components extracted, explaining {cumulative_variance[-1]:.1%} of total variance.',
                'output_path': output_dir,
                'analysis_info': analysis_info,
                'n_components': n_components,
                'total_variance_explained': float(cumulative_variance[-1])
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'PCA analysis failed: {str(e)}'
            }


class DataProcessingManager:
    """Manager class for coordinating different data processors."""
    
    def __init__(self):
        self.processors = {
            'Matrix Extraction': MatrixExtractionProcessor(),
            'MatrixAssemble': MatrixAssembleProcessor(),
            'Matrix Modification': MatrixModificationProcessor(),
            'Data Annotation': DataAnnotationProcessor(),
            'Indexing': IndexingProcessor(),
            'Ruzicka Similarity': RuzickaSimilarityProcessor(),
            'Hierarchical Clustering': HierarchicalClusteringProcessor(),
            'Dimensionality Reduction': DimensionalityReductionProcessor()
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
