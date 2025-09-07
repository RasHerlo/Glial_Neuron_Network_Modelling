"""
Data importers for various file formats with database integration.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
import json
from datetime import datetime

from ..database.operations import DatasetOperations
from ..utils.folder_manager import DatasetFolderManager


class BaseImporter:
    """Base class for data importers."""
    
    def __init__(self):
        self.supported_formats = []
    
    def can_import(self, file_path: str) -> bool:
        """Check if this importer can handle the file format."""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_formats
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import data from file. Should be implemented by subclasses."""
        raise NotImplementedError
    
    def get_metadata(self, file_path: str, data: Any = None) -> Dict[str, Any]:
        """Extract metadata from file and data."""
        metadata = {
            'file_size': os.path.getsize(file_path),
            'file_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'import_timestamp': datetime.now().isoformat()
        }
        
        if data is not None:
            if hasattr(data, 'shape'):
                metadata['data_shape'] = data.shape
            if hasattr(data, 'dtypes'):
                metadata['data_types'] = data.dtypes.to_dict() if hasattr(data.dtypes, 'to_dict') else str(data.dtypes)
            if hasattr(data, 'columns'):
                metadata['columns'] = list(data.columns)
        
        return metadata


class CSVImporter(BaseImporter):
    """Importer for CSV files."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.csv', '.tsv']
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import CSV file."""
        try:
            # Extract raw_import setting before processing other parameters
            raw_import = kwargs.pop('raw_import', False)
            
            # Default parameters
            params = {
                'sep': ',' if file_path.endswith('.csv') else '\t',
                'header': None if raw_import else 0,  # Key change: no header assumption for raw import
                'index_col': None,
                'encoding': 'utf-8'
            }
            
            # Extract advanced import settings before updating params
            convert_numeric = kwargs.pop('convert_numeric', False)
            handle_errors = kwargs.pop('handle_errors', 'coerce')
            
            # Handle advanced import settings
            if 'skip_rows' in kwargs:
                params['skiprows'] = kwargs.pop('skip_rows')
            if 'header_row' in kwargs and not raw_import:
                # Only use header_row if not in raw import mode
                params['header'] = kwargs.pop('header_row')
            elif 'header_row' in kwargs:
                # Remove header_row from kwargs if in raw import mode
                kwargs.pop('header_row')
            
            # Update with any additional parameters
            params.update(kwargs)
            
            # Try to read the file
            data = pd.read_csv(file_path, **params)
            
            # If raw import, generate meaningful column names
            if raw_import:
                data.columns = [f'Column_{i}' for i in range(len(data.columns))]
            
            # Enhanced automatic data type preservation
            if raw_import or convert_numeric:
                for col in data.columns:
                    if data[col].dtype == 'object':  # Text columns
                        if raw_import:
                            # For raw import, try automatic conversion but keep original if conversion fails
                            numeric_version = pd.to_numeric(data[col], errors='ignore')
                            # Only replace if conversion actually happened (not just returned original)
                            if not numeric_version.equals(data[col]):
                                data[col] = numeric_version
                        elif convert_numeric and handle_errors == 'coerce':
                            # Original logic for explicit convert_numeric requests
                            numeric_version = pd.to_numeric(data[col], errors='coerce')
                            # Only replace if we successfully converted most values
                            if numeric_version.notna().sum() > len(data) * 0.5:
                                data[col] = numeric_version
            
            # Get basic statistics
            stats = {
                'row_count': len(data),
                'column_count': len(data.columns),
                'memory_usage': data.memory_usage(deep=True).sum(),
                'null_counts': data.isnull().sum().to_dict(),
                'data_types': data.dtypes.to_dict()
            }
            
            # Get numeric column statistics
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats['numeric_summary'] = data[numeric_cols].describe().to_dict()
            
            # Create success message
            import_mode = "raw import" if raw_import else "standard import"
            success_message = f'Successfully imported {len(data)} rows and {len(data.columns)} columns using {import_mode}'
            
            return {
                'data': data,
                'statistics': stats,
                'metadata': self.get_metadata(file_path, data),
                'success': True,
                'message': success_message,
                'import_mode': import_mode,
                'raw_import': raw_import
            }
            
        except Exception as e:
            return {
                'data': None,
                'statistics': None,
                'metadata': self.get_metadata(file_path),
                'success': False,
                'message': f'Failed to import CSV: {str(e)}'
            }


class ExcelImporter(BaseImporter):
    """Importer for Excel files."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.xlsx', '.xls']
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import Excel file."""
        try:
            # Default parameters
            params = {
                'sheet_name': 0,  # First sheet by default
                'header': 0,
                'index_col': None
            }
            params.update(kwargs)
            
            # Read Excel file
            data = pd.read_excel(file_path, **params)
            
            # Get sheet names for metadata
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Get basic statistics
            stats = {
                'row_count': len(data),
                'column_count': len(data.columns),
                'sheet_names': sheet_names,
                'active_sheet': params['sheet_name'] if isinstance(params['sheet_name'], str) else sheet_names[params['sheet_name']],
                'memory_usage': data.memory_usage(deep=True).sum(),
                'null_counts': data.isnull().sum().to_dict(),
                'data_types': data.dtypes.to_dict()
            }
            
            # Get numeric column statistics
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats['numeric_summary'] = data[numeric_cols].describe().to_dict()
            
            return {
                'data': data,
                'statistics': stats,
                'metadata': self.get_metadata(file_path, data),
                'success': True,
                'message': f'Successfully imported {len(data)} rows and {len(data.columns)} columns from sheet "{stats["active_sheet"]}"'
            }
            
        except Exception as e:
            return {
                'data': None,
                'statistics': None,
                'metadata': self.get_metadata(file_path),
                'success': False,
                'message': f'Failed to import Excel: {str(e)}'
            }


class JSONImporter(BaseImporter):
    """Importer for JSON files."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.json']
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Try to convert to DataFrame if possible
            data = None
            if isinstance(json_data, list):
                # List of records
                data = pd.DataFrame(json_data)
            elif isinstance(json_data, dict):
                # Dictionary - try to convert to DataFrame
                try:
                    data = pd.DataFrame(json_data)
                except:
                    # If conversion fails, keep as dict
                    pass
            
            # Get statistics
            stats = {
                'json_type': type(json_data).__name__,
                'json_keys': list(json_data.keys()) if isinstance(json_data, dict) else None,
                'json_length': len(json_data) if hasattr(json_data, '__len__') else None
            }
            
            if data is not None:
                stats.update({
                    'row_count': len(data),
                    'column_count': len(data.columns),
                    'memory_usage': data.memory_usage(deep=True).sum(),
                    'null_counts': data.isnull().sum().to_dict(),
                    'data_types': data.dtypes.to_dict()
                })
            
            return {
                'data': data if data is not None else json_data,
                'statistics': stats,
                'metadata': self.get_metadata(file_path, data),
                'success': True,
                'message': f'Successfully imported JSON data'
            }
            
        except Exception as e:
            return {
                'data': None,
                'statistics': None,
                'metadata': self.get_metadata(file_path),
                'success': False,
                'message': f'Failed to import JSON: {str(e)}'
            }


class TextImporter(BaseImporter):
    """Importer for generic text files."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.txt', '.dat']
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import text file."""
        try:
            # Default parameters
            params = {
                'encoding': 'utf-8',
                'delimiter': None,  # Auto-detect
                'skip_rows': 0
            }
            params.update(kwargs)
            
            # Read file content
            with open(file_path, 'r', encoding=params['encoding']) as f:
                lines = f.readlines()[params['skip_rows']:]
            
            # Try to detect structure and convert to DataFrame
            data = None
            if params['delimiter']:
                # Use specified delimiter
                try:
                    import io
                    text_data = ''.join(lines)
                    data = pd.read_csv(io.StringIO(text_data), sep=params['delimiter'])
                except:
                    pass
            else:
                # Try common delimiters
                delimiters = ['\t', ',', ';', ' ', '|']
                for delim in delimiters:
                    try:
                        import io
                        text_data = ''.join(lines)
                        test_data = pd.read_csv(io.StringIO(text_data), sep=delim, nrows=5)
                        if len(test_data.columns) > 1:  # Found structure
                            data = pd.read_csv(io.StringIO(text_data), sep=delim)
                            break
                    except:
                        continue
            
            # Get statistics
            stats = {
                'line_count': len(lines),
                'file_encoding': params['encoding'],
                'detected_delimiter': None
            }
            
            if data is not None:
                stats.update({
                    'row_count': len(data),
                    'column_count': len(data.columns),
                    'memory_usage': data.memory_usage(deep=True).sum(),
                    'null_counts': data.isnull().sum().to_dict(),
                    'data_types': data.dtypes.to_dict()
                })
            
            return {
                'data': data if data is not None else lines,
                'statistics': stats,
                'metadata': self.get_metadata(file_path, data),
                'success': True,
                'message': f'Successfully imported text file with {len(lines)} lines'
            }
            
        except Exception as e:
            return {
                'data': None,
                'statistics': None,
                'metadata': self.get_metadata(file_path),
                'success': False,
                'message': f'Failed to import text file: {str(e)}'
            }


class NPYImporter(BaseImporter):
    """Importer for NumPy array files (.npy)."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.npy']
    
    def apply_nan_columns(self, data_array: np.ndarray, start_col: int, end_col: int) -> np.ndarray:
        """Insert NaN values in specified column range.
        
        Args:
            data_array: Original 2D numpy array
            start_col: Start column index (0-based, inclusive)
            end_col: End column index (0-based, inclusive)
            
        Returns:
            np.ndarray: Array with NaN values inserted in specified columns
        """
        if data_array.ndim != 2:
            raise ValueError(f"Expected 2D array, got {data_array.ndim}D array")
        
        # Validate column indices
        n_rows, n_cols = data_array.shape
        if start_col < 0 or end_col < 0:
            raise ValueError("Column indices must be non-negative")
        if start_col >= n_cols or end_col >= n_cols:
            raise ValueError(f"Column indices must be < {n_cols}")
        if start_col > end_col:
            raise ValueError("Start column must be <= end column")
        
        # Create a copy to avoid modifying original array
        result_array = data_array.copy()
        
        # Insert NaN values in specified column range
        result_array[:, start_col:end_col+1] = np.nan
        
        return result_array
    
    def import_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import NumPy array file and generate labels.
        
        Args:
            file_path: Path to .npy file
            **kwargs: Import settings (row_prefix, col_prefix, etc.)
        """
        try:
            # Load numpy array
            data_array = np.load(file_path)
            
            # Validate array
            if data_array.ndim != 2:
                return {
                    'success': False,
                    'message': f'Expected 2D array, got {data_array.ndim}D array',
                    'data': None,
                    'metadata': {}
                }
            
            # Apply NaN insertion if requested
            nan_insertion = kwargs.get('nan_insertion')
            if nan_insertion and nan_insertion.get('enabled', False):
                try:
                    start_col = nan_insertion.get('start_col', 0)
                    end_col = nan_insertion.get('end_col', 0)
                    
                    if start_col >= 0 and end_col >= 0 and start_col <= end_col:
                        data_array = self.apply_nan_columns(data_array, start_col, end_col)
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Failed to apply NaN insertion: {str(e)}',
                        'data': None,
                        'metadata': {}
                    }
            
            # Get array dimensions (after potential NaN insertion)
            n_rows, n_cols = data_array.shape
            
            # Generate row labels (cells) - Cell_0001, Cell_0002, etc.
            row_prefix = kwargs.get('row_prefix', 'Cell')
            row_labels = [f"{row_prefix}_{i+1:04d}" for i in range(n_rows)]
            
            # Generate column labels (frames) - Frame_00001, Frame_00002, etc.
            col_prefix = kwargs.get('col_prefix', 'Frame')
            col_labels = [f"{col_prefix}_{i+1:05d}" for i in range(n_cols)]
            
            # Create DataFrame with labels for compatibility
            df = pd.DataFrame(data_array, index=row_labels, columns=col_labels)
            
            # Calculate statistics
            statistics = {
                'shape': data_array.shape,
                'dtype': str(data_array.dtype),
                'total_elements': data_array.size,
                'memory_usage_mb': data_array.nbytes / (1024 * 1024),
                'min_value': float(np.min(data_array)),
                'max_value': float(np.max(data_array)),
                'mean_value': float(np.mean(data_array)),
                'std_value': float(np.std(data_array)),
                'has_nan': bool(np.isnan(data_array).any()),
                'has_inf': bool(np.isinf(data_array).any())
            }
            
            # Create metadata
            metadata = self.get_metadata(file_path, df)
            metadata.update({
                'array_statistics': statistics,
                'import_type': 'numpy_array',
                'row_prefix': row_prefix,
                'col_prefix': col_prefix,
                'original_shape': data_array.shape,
                'generated_labels': True
            })
            
            return {
                'success': True,
                'data': df,
                'raw_array': data_array,  # Keep original array for saving
                'row_labels': row_labels,
                'col_labels': col_labels,
                'statistics': statistics,
                'metadata': metadata,
                'message': f'Successfully imported numpy array with shape {data_array.shape}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to import numpy array: {str(e)}',
                'data': None,
                'metadata': {}
            }
    
    def save_processed_files(self, import_result: Dict[str, Any], output_dir: str, 
                           base_filename: str, nan_suffix: bool = False) -> Dict[str, str]:
        """Save processed files for numpy import.
        
        Args:
            import_result: Result from import_file method
            output_dir: Directory to save files
            base_filename: Base name for output files
            nan_suffix: If True, append '_nans' suffix to filenames
            
        Returns:
            Dict mapping file types to saved file paths
        """
        saved_files = {}
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Apply suffix if NaN insertion was used
            filename_base = f"{base_filename}_nans" if nan_suffix else base_filename
            
            # Save original numpy array
            npy_path = os.path.join(output_dir, f"{filename_base}.npy")
            np.save(npy_path, import_result['raw_array'])
            saved_files['original_npy'] = npy_path
            
            # Save labeled CSV for compatibility with existing tools
            csv_path = os.path.join(output_dir, f"{filename_base}_labeled.csv")
            import_result['data'].to_csv(csv_path)
            saved_files['labeled_csv'] = csv_path
            
            # Save row labels
            row_labels_path = os.path.join(output_dir, "row_labels.csv")
            pd.DataFrame({'row_label': import_result['row_labels']}).to_csv(
                row_labels_path, index=False
            )
            saved_files['row_labels'] = row_labels_path
            
            # Save column labels
            col_labels_path = os.path.join(output_dir, "col_labels.csv")
            pd.DataFrame({'col_label': import_result['col_labels']}).to_csv(
                col_labels_path, index=False
            )
            saved_files['col_labels'] = col_labels_path
            
            # Save matrix info
            matrix_info = {
                'original_file': import_result['metadata'].get('file_path', ''),
                'shape': import_result['statistics']['shape'],
                'dtype': import_result['statistics']['dtype'],
                'import_timestamp': datetime.now().isoformat(),
                'statistics': import_result['statistics'],
                'row_prefix': import_result['metadata']['row_prefix'],
                'col_prefix': import_result['metadata']['col_prefix']
            }
            
            info_path = os.path.join(output_dir, "matrix_info.json")
            with open(info_path, 'w') as f:
                json.dump(matrix_info, f, indent=2)
            saved_files['matrix_info'] = info_path
            
        except Exception as e:
            print(f"Error saving processed files: {e}")
        
        return saved_files
    
    def generate_raster_matrix_files(self, import_result: Dict[str, Any], 
                                   processed_matrices_dir: str) -> Dict[str, str]:
        """Generate standardized Raster_* files for processing pipeline compatibility.
        
        Args:
            import_result: Result from import_file method containing raw_array, labels, etc.
            processed_matrices_dir: Directory to save standardized files
            
        Returns:
            Dict mapping file types to saved file paths
        """
        raster_files = {}
        
        try:
            os.makedirs(processed_matrices_dir, exist_ok=True)
            
            # 1. Save matrix as Raster_matrix.npy (standard name for processing tools)
            raster_matrix_path = os.path.join(processed_matrices_dir, "Raster_matrix.npy")
            np.save(raster_matrix_path, import_result['raw_array'])
            raster_files['raster_matrix_npy'] = raster_matrix_path
            
            # 2. Create Raster_with_labels.csv (matrix with row/column labels applied)
            matrix_with_labels = import_result['data'].copy()  # This already has labels applied
            raster_with_labels_path = os.path.join(processed_matrices_dir, "Raster_with_labels.csv")
            matrix_with_labels.to_csv(raster_with_labels_path, index=True)
            raster_files['raster_with_labels_csv'] = raster_with_labels_path
            
            # 3. Create Raster_row_labels_and_indices.csv (single column: row_labels)
            row_labels_df = pd.DataFrame({'row_labels': import_result['row_labels']})
            raster_row_labels_path = os.path.join(processed_matrices_dir, "Raster_row_labels_and_indices.csv")
            row_labels_df.to_csv(raster_row_labels_path, index=False)
            raster_files['raster_row_labels_csv'] = raster_row_labels_path
            
            # 4. Create Raster_column_labels_and_indices.csv (single column: column_labels)
            col_labels_df = pd.DataFrame({'column_labels': import_result['col_labels']})
            raster_col_labels_path = os.path.join(processed_matrices_dir, "Raster_column_labels_and_indices.csv")
            col_labels_df.to_csv(raster_col_labels_path, index=False)
            raster_files['raster_col_labels_csv'] = raster_col_labels_path
            
            print(f"Generated standardized Raster files in: {processed_matrices_dir}")
            
        except Exception as e:
            print(f"Error generating Raster matrix files: {e}")
        
        return raster_files


class Suite2pDatasetDetector:
    """Detector for Suite2p dataset structure and multi-channel data."""
    
    def __init__(self):
        self.expected_structure = [
            "SUPPORT_ChanA", "SUPPORT_ChanB"
        ]
        self.suite2p_path = ["derippled", "suite2p", "plane0"]
    
    def scan_data_folder(self, data_folder_path: str) -> Dict[str, Any]:
        """Scan DATA folder for Suite2p structure.
        
        Args:
            data_folder_path: Path to the DATA folder
            
        Returns:
            Dict containing scan results
        """
        data_path = Path(data_folder_path)
        
        if not data_path.exists():
            return {
                'success': False,
                'message': f'Data folder not found: {data_folder_path}',
                'channels': {}
            }
        
        channels = {}
        
        # Look for channel folders
        for channel_name in self.expected_structure:
            channel_path = data_path / channel_name
            
            if channel_path.exists():
                # Navigate to plane0 folder
                plane0_path = channel_path
                for subdir in self.suite2p_path:
                    plane0_path = plane0_path / subdir
                
                if plane0_path.exists():
                    # Find .npy files in plane0
                    npy_files = list(plane0_path.glob("*.npy"))
                    
                    if npy_files:
                        channels[channel_name] = {
                            'path': str(plane0_path),
                            'npy_files': [f.name for f in npy_files],
                            'full_paths': [str(f) for f in npy_files]
                        }
                    else:
                        channels[channel_name] = {
                            'path': str(plane0_path),
                            'npy_files': [],
                            'full_paths': [],
                            'warning': 'No .npy files found in plane0 folder'
                        }
                else:
                    channels[channel_name] = {
                        'path': None,
                        'npy_files': [],
                        'full_paths': [],
                        'error': f'Suite2p structure not found (missing path: {plane0_path})'
                    }
        
        return {
            'success': len(channels) > 0,
            'message': f'Found {len(channels)} channels' if channels else 'No channels found',
            'channels': channels,
            'data_folder': str(data_path)
        }
    
    def validate_selected_files(self, selected_files: Dict[str, str]) -> Dict[str, Any]:
        """Validate that selected files from different channels are compatible.
        
        Args:
            selected_files: Dict mapping channel names to selected file paths
            
        Returns:
            Dict containing validation results
        """
        if len(selected_files) < 2:
            return {
                'valid': True,
                'message': 'Single channel selected, no compatibility check needed',
                'warnings': []
            }
        
        shapes = {}
        warnings = []
        
        try:
            # Load each selected file and check dimensions
            for channel, file_path in selected_files.items():
                if not os.path.exists(file_path):
                    return {
                        'valid': False,
                        'message': f'File not found: {file_path}',
                        'warnings': []
                    }
                
                array = np.load(file_path)
                shapes[channel] = array.shape
            
            # Check time dimension compatibility (columns should match)
            time_dims = [shape[1] for shape in shapes.values()]
            
            if len(set(time_dims)) > 1:
                warnings.append(
                    f"Time dimensions don't match: {dict(zip(selected_files.keys(), time_dims))}. "
                    "This may cause issues in cross-channel analyses."
                )
            
            # Check if cell counts are very different (might be worth noting)
            cell_counts = [shape[0] for shape in shapes.values()]
            max_cells = max(cell_counts)
            min_cells = min(cell_counts)
            
            if max_cells > min_cells * 2:  # If one channel has >2x more cells
                warnings.append(
                    f"Cell counts vary significantly: {dict(zip(selected_files.keys(), cell_counts))}. "
                    "This is normal but worth noting."
                )
            
            return {
                'valid': True,
                'message': 'Files are compatible' if not warnings else 'Files loaded with warnings',
                'warnings': warnings,
                'shapes': shapes
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Error validating files: {str(e)}',
                'warnings': []
            }


class DataImportManager:
    """Manager class for coordinating different data importers."""
    
    def __init__(self):
        self.importers = [
            CSVImporter(),
            ExcelImporter(),
            JSONImporter(),
            TextImporter(),
            NPYImporter()
        ]
        self.folder_manager = DatasetFolderManager()
    
    def get_importer(self, file_path: str) -> Optional[BaseImporter]:
        """Get appropriate importer for file."""
        for importer in self.importers:
            if importer.can_import(file_path):
                return importer
        return None
    
    def import_file(self, file_path: str, dataset_name: str = None, 
                   description: str = "", **kwargs) -> Dict[str, Any]:
        """Import file and optionally save to database."""
        if not os.path.exists(file_path):
            return {
                'success': False,
                'message': f'File not found: {file_path}'
            }
        
        # Check for duplicates if dataset name is provided
        if dataset_name:
            duplicate_check = self._check_for_duplicates(dataset_name)
            if not duplicate_check['can_proceed']:
                return duplicate_check
        
        # Get appropriate importer
        importer = self.get_importer(file_path)
        if not importer:
            return {
                'success': False,
                'message': f'No importer available for file: {file_path}'
            }
        
        # Extract advanced import settings from kwargs
        advanced_settings = {}
        for key in ['skip_rows', 'header_row', 'convert_numeric', 'handle_errors', 'raw_import']:
            if key in kwargs:
                advanced_settings[key] = kwargs[key]
        
        # Import the file with advanced settings
        result = importer.import_file(file_path, **kwargs)
        
        if result['success'] and dataset_name:
            # Save to database if dataset name provided
            try:
                file_format = Path(file_path).suffix.lower().replace('.', '')
                
                dataset_id = DatasetOperations.create_dataset(
                    name=dataset_name,
                    file_path=file_path,
                    file_format=file_format,
                    description=description,
                    metadata=result['metadata']
                )
                
                result['dataset_id'] = dataset_id
                result['message'] += f' Dataset saved with ID: {dataset_id}'
                
            except Exception as e:
                result['database_error'] = str(e)
                result['message'] += f' Warning: Failed to save to database: {str(e)}'
        
        return result
    
    def get_supported_formats(self) -> list:
        """Get list of all supported file formats."""
        formats = []
        for importer in self.importers:
            formats.extend(importer.supported_formats)
        return sorted(list(set(formats)))
    
    def preview_file(self, file_path: str, max_rows: int = 10, **import_settings) -> Dict[str, Any]:
        """Preview file content without full import.
        
        Args:
            file_path: Path to the file to preview
            max_rows: Maximum number of rows to preview
            **import_settings: Import settings to apply (skip_rows, header_row, etc.)
        """
        importer = self.get_importer(file_path)
        if not importer:
            return {
                'success': False,
                'message': f'No importer available for file: {file_path}'
            }
        
        # Prepare kwargs with import settings and row limit
        kwargs = dict(import_settings)  # Copy import settings
        kwargs['nrows'] = max_rows  # Add row limit for preview
        
        # For CSV and Excel, we can limit rows and apply import settings
        if isinstance(importer, (CSVImporter, ExcelImporter)):
            result = importer.import_file(file_path, **kwargs)
        else:
            # For other formats, import full file but limit display
            # Remove nrows for formats that don't support it
            other_kwargs = {k: v for k, v in import_settings.items() if k != 'nrows'}
            result = importer.import_file(file_path, **other_kwargs)
            if result['success'] and hasattr(result['data'], 'head'):
                result['data'] = result['data'].head(max_rows)
        
        return result
    
    def _check_for_duplicates(self, dataset_name: str) -> Dict[str, Any]:
        """Check for duplicate datasets and return appropriate response.
        
        Args:
            dataset_name: Name of the dataset to check
            
        Returns:
            Dict with 'can_proceed' boolean and 'message' if conflicts found
        """
        # Check database for existing dataset
        existing_dataset = DatasetOperations.get_dataset_by_name(dataset_name)
        
        # Check filesystem for existing folders
        folder_conflicts = self.folder_manager.check_dataset_conflicts(dataset_name)
        
        # Determine conflict type and create appropriate message
        if existing_dataset and folder_conflicts['folder_exists']:
            # Both database and folder exist
            return {
                'success': False,
                'can_proceed': False,
                'message': f'Dataset "{dataset_name}" already exists in both database and filesystem.\n'
                          f'Database ID: {existing_dataset.id}\n'
                          f'Import cancelled to prevent conflicts. Please handle manually.'
            }
        elif existing_dataset:
            # Database exists but no folder
            return {
                'success': False,
                'can_proceed': False,
                'message': f'Dataset "{dataset_name}" already exists in database (ID: {existing_dataset.id}) '
                          f'but folder is missing.\n'
                          f'Import cancelled. Please resolve this conflict manually.'
            }
        elif folder_conflicts['folder_exists']:
            # Folder exists but no database entry
            folder_type = "clean name" if folder_conflicts['clean_folder_exists'] else "legacy format"
            return {
                'success': False,
                'can_proceed': False,
                'message': f'Dataset folder "{dataset_name}" already exists ({folder_type}) '
                          f'but no database entry found.\n'
                          f'Import cancelled. Please resolve this conflict manually.'
            }
        
        # No conflicts found
        return {
            'success': True,
            'can_proceed': True,
            'message': 'No conflicts detected'
        }
