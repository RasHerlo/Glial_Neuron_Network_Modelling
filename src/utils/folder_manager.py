"""
Folder management utilities for dataset organization.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional, List


class DatasetFolderManager:
    """Manages dataset folder structure and organization."""
    
    def __init__(self, base_data_dir: str = "data"):
        self.base_data_dir = Path(base_data_dir)
        self.datasets_dir = self.base_data_dir / "datasets"
        self.shared_dir = self.base_data_dir / "shared"
    
    def create_dataset_folder(self, dataset_id: int, dataset_name: str) -> str:
        """Create a dataset folder structure and return the base path.
        
        Args:
            dataset_id: Unique dataset ID
            dataset_name: Name of the dataset
            
        Returns:
            str: Absolute path to the dataset folder
        """
        # Sanitize dataset name for folder use
        safe_name = self._sanitize_folder_name(dataset_name)
        folder_name = f"dataset_{dataset_id:03d}_{safe_name}"
        
        dataset_path = self.datasets_dir / folder_name
        
        # Create directory structure
        os.makedirs(dataset_path / "raw", exist_ok=True)
        os.makedirs(dataset_path / "processed" / "matrices", exist_ok=True)
        os.makedirs(dataset_path / "processed" / "pca", exist_ok=True)
        os.makedirs(dataset_path / "processed" / "vectors", exist_ok=True)
        os.makedirs(dataset_path / "processed" / "statistics", exist_ok=True)
        os.makedirs(dataset_path / "figures", exist_ok=True)
        
        return str(dataset_path.absolute())
    
    def get_dataset_folder(self, dataset_id: int, dataset_name: str) -> Optional[str]:
        """Get existing dataset folder path.
        
        Args:
            dataset_id: Unique dataset ID
            dataset_name: Name of the dataset
            
        Returns:
            str: Absolute path to dataset folder if exists, None otherwise
        """
        safe_name = self._sanitize_folder_name(dataset_name)
        folder_name = f"dataset_{dataset_id:03d}_{safe_name}"
        dataset_path = self.datasets_dir / folder_name
        
        if dataset_path.exists():
            return str(dataset_path.absolute())
        return None
    
    def get_raw_data_path(self, dataset_folder: str) -> str:
        """Get the raw data directory path."""
        return os.path.join(dataset_folder, "raw")
    
    def get_processed_data_path(self, dataset_folder: str, data_type: str = "") -> str:
        """Get the processed data directory path."""
        processed_path = os.path.join(dataset_folder, "processed")
        if data_type:
            processed_path = os.path.join(processed_path, data_type)
        return processed_path
    
    def get_figures_path(self, dataset_folder: str) -> str:
        """Get the figures directory path."""
        return os.path.join(dataset_folder, "figures")
    
    def generate_processed_filename(self, base_name: str, process_type: str, 
                                  extension: str = ".npy") -> str:
        """Generate a filename for processed data.
        
        Args:
            base_name: Base name (usually from original dataset)
            process_type: Type of processing (e.g., 'pca', 'correlation_matrix')
            extension: File extension
            
        Returns:
            str: Generated filename
        """
        safe_base = self._sanitize_filename(base_name)
        safe_process = self._sanitize_filename(process_type)
        return f"{safe_base}_{safe_process}{extension}"
    
    def ensure_processed_type_folder(self, dataset_folder: str, data_type: str) -> str:
        """Ensure a processed data type folder exists."""
        processed_type_path = self.get_processed_data_path(dataset_folder, data_type)
        os.makedirs(processed_type_path, exist_ok=True)
        return processed_type_path
    
    def get_dataset_info_from_path(self, dataset_path: str) -> Tuple[Optional[int], Optional[str]]:
        """Extract dataset ID and name from folder path.
        
        Args:
            dataset_path: Path to dataset folder
            
        Returns:
            Tuple of (dataset_id, dataset_name) or (None, None) if invalid
        """
        folder_name = Path(dataset_path).name
        
        # Pattern: dataset_001_MyDatasetName
        match = re.match(r'dataset_(\d+)_(.+)', folder_name)
        if match:
            dataset_id = int(match.group(1))
            dataset_name = match.group(2)
            return dataset_id, dataset_name
        
        return None, None
    
    def list_dataset_folders(self) -> List[Tuple[int, str, str]]:
        """List all existing dataset folders.
        
        Returns:
            List of tuples: (dataset_id, dataset_name, folder_path)
        """
        if not self.datasets_dir.exists():
            return []
        
        dataset_folders = []
        for folder_path in self.datasets_dir.iterdir():
            if folder_path.is_dir():
                dataset_id, dataset_name = self.get_dataset_info_from_path(str(folder_path))
                if dataset_id is not None:
                    dataset_folders.append((dataset_id, dataset_name, str(folder_path)))
        
        return sorted(dataset_folders, key=lambda x: x[0])  # Sort by ID
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize a name for use as a folder name."""
        # Remove/replace invalid characters for folder names
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove extra spaces and replace with underscores
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_.')
        # Limit length
        return sanitized[:50] if len(sanitized) > 50 else sanitized
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a name for use as a filename."""
        # Similar to folder name but more restrictive
        sanitized = re.sub(r'[<>:"/\\|?*\s]', '_', name)
        sanitized = sanitized.strip('_.')
        return sanitized[:30] if len(sanitized) > 30 else sanitized
