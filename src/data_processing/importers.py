"""
Data importers for various file formats with database integration.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Union
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


class DataImportManager:
    """Manager class for coordinating different data importers."""
    
    def __init__(self):
        self.importers = [
            CSVImporter(),
            ExcelImporter(),
            JSONImporter(),
            TextImporter()
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
