"""
Database workspace management for flexible database locations.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .connection import DatabaseConnection
from .models import DatabaseSchema


class DatabaseWorkspace:
    """Manages database workspace locations and associated folder structures."""
    
    def __init__(self, workspace_path: str):
        """Initialize workspace manager.
        
        Args:
            workspace_path: Path to the workspace directory containing database and datasets
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.db_path = self.workspace_path / "pipeline.db"
        self.datasets_path = self.workspace_path / "datasets"
        self.figures_path = self.workspace_path / "figures"
        self.processed_path = self.workspace_path / "processed"
        self.raw_path = self.workspace_path / "raw"
        self.backup_path = self.workspace_path / "backups"
        
        # Database connection instance for this workspace
        self._db_connection: Optional[DatabaseConnection] = None
    
    def validate_workspace(self) -> Dict[str, Any]:
        """Validate workspace structure and return status information.
        
        Returns:
            Dict containing validation results:
            - 'is_valid': bool - True if workspace is valid
            - 'has_database': bool - True if database file exists
            - 'has_datasets_folder': bool - True if datasets folder exists
            - 'database_size': int - Size of database file in bytes
            - 'dataset_count': int - Number of dataset folders found
            - 'issues': List[str] - List of validation issues found
        """
        validation_result = {
            'is_valid': True,
            'has_database': False,
            'has_datasets_folder': False,
            'database_size': 0,
            'dataset_count': 0,
            'issues': []
        }
        
        # Check if workspace directory exists
        if not self.workspace_path.exists():
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"Workspace directory does not exist: {self.workspace_path}")
            return validation_result
        
        # Check for database file
        if self.db_path.exists():
            validation_result['has_database'] = True
            validation_result['database_size'] = self.db_path.stat().st_size
        else:
            validation_result['issues'].append("Database file not found")
        
        # Check for datasets folder
        if self.datasets_path.exists():
            validation_result['has_datasets_folder'] = True
            # Count dataset folders
            try:
                dataset_folders = [d for d in self.datasets_path.iterdir() if d.is_dir()]
                validation_result['dataset_count'] = len(dataset_folders)
            except PermissionError:
                validation_result['issues'].append("Cannot access datasets folder due to permissions")
        else:
            validation_result['issues'].append("Datasets folder not found")
        
        # Workspace is considered valid if it has at least the database file
        validation_result['is_valid'] = validation_result['has_database']
        
        return validation_result
    
    def initialize_workspace(self, create_missing: bool = True) -> bool:
        """Initialize workspace structure and database.
        
        Args:
            create_missing: If True, create missing folders and initialize database
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Create workspace directory if it doesn't exist
            if not self.workspace_path.exists():
                if create_missing:
                    self.workspace_path.mkdir(parents=True, exist_ok=True)
                else:
                    return False
            
            # Create required subdirectories
            required_dirs = [
                self.datasets_path,
                self.figures_path,
                self.processed_path,
                self.raw_path,
                self.backup_path
            ]
            
            for directory in required_dirs:
                if create_missing:
                    directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize database if it doesn't exist
            if not self.db_path.exists() and create_missing:
                # Create a new database connection which will initialize the database
                db_connection = DatabaseConnection(str(self.db_path))
                db_connection.close()
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize workspace: {e}")
            return False
    
    def get_database_connection(self) -> DatabaseConnection:
        """Get database connection for this workspace.
        
        Returns:
            DatabaseConnection: Connection to workspace database
        """
        if self._db_connection is None:
            self._db_connection = DatabaseConnection(str(self.db_path))
        return self._db_connection
    
    def close_database_connection(self):
        """Close database connection for this workspace."""
        if self._db_connection is not None:
            self._db_connection.close()
            self._db_connection = None
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get comprehensive workspace information.
        
        Returns:
            Dict containing workspace details
        """
        validation = self.validate_workspace()
        
        info = {
            'workspace_path': str(self.workspace_path),
            'database_path': str(self.db_path),
            'datasets_path': str(self.datasets_path),
            'validation': validation,
            'created_date': None,
            'last_modified': None
        }
        
        # Get workspace creation/modification dates
        if self.workspace_path.exists():
            stat = self.workspace_path.stat()
            info['created_date'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
            info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info
    
    def list_available_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets in this workspace.
        
        Returns:
            List of dataset information dictionaries
        """
        datasets = []
        
        if not self.datasets_path.exists():
            return datasets
        
        try:
            for dataset_folder in self.datasets_path.iterdir():
                if dataset_folder.is_dir():
                    dataset_info = {
                        'folder_name': dataset_folder.name,
                        'folder_path': str(dataset_folder),
                        'has_raw': (dataset_folder / "raw").exists(),
                        'has_processed': (dataset_folder / "processed").exists(),
                        'has_figures': (dataset_folder / "figures").exists(),
                        'last_modified': datetime.fromtimestamp(
                            dataset_folder.stat().st_mtime
                        ).isoformat()
                    }
                    datasets.append(dataset_info)
        except Exception as e:
            print(f"Error listing datasets: {e}")
        
        return sorted(datasets, key=lambda x: x['last_modified'], reverse=True)
    
    def copy_from_workspace(self, source_workspace_path: str, 
                          copy_database: bool = True, 
                          copy_datasets: bool = True) -> bool:
        """Copy data from another workspace to this one.
        
        Args:
            source_workspace_path: Path to source workspace
            copy_database: Whether to copy database file
            copy_datasets: Whether to copy datasets folder
            
        Returns:
            bool: True if copy successful
        """
        try:
            source_path = Path(source_workspace_path)
            
            if not source_path.exists():
                return False
            
            # Initialize this workspace first
            if not self.initialize_workspace():
                return False
            
            # Copy database file
            if copy_database:
                source_db = source_path / "pipeline.db"
                if source_db.exists():
                    shutil.copy2(source_db, self.db_path)
            
            # Copy datasets folder
            if copy_datasets:
                source_datasets = source_path / "datasets"
                if source_datasets.exists():
                    if self.datasets_path.exists():
                        shutil.rmtree(self.datasets_path)
                    shutil.copytree(source_datasets, self.datasets_path)
            
            return True
            
        except Exception as e:
            print(f"Failed to copy from workspace: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of workspace."""
        return f"DatabaseWorkspace({self.workspace_path})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        validation = self.validate_workspace()
        return (f"DatabaseWorkspace(path='{self.workspace_path}', "
                f"valid={validation['is_valid']}, "
                f"datasets={validation['dataset_count']})")


class WorkspaceManager:
    """Global workspace manager for handling active workspace."""
    
    def __init__(self):
        self._current_workspace: Optional[DatabaseWorkspace] = None
        self._default_workspace_path = Path(__file__).parent.parent.parent / "data"
    
    def get_current_workspace(self) -> DatabaseWorkspace:
        """Get the currently active workspace.
        
        Returns:
            DatabaseWorkspace: Current active workspace
        """
        if self._current_workspace is None:
            # Initialize with default workspace (repository data folder)
            self.set_workspace(str(self._default_workspace_path))
        
        return self._current_workspace
    
    def set_workspace(self, workspace_path: str) -> bool:
        """Set the active workspace.
        
        Args:
            workspace_path: Path to workspace directory
            
        Returns:
            bool: True if workspace was set successfully
        """
        try:
            # Close current workspace database connection if exists
            if self._current_workspace is not None:
                self._current_workspace.close_database_connection()
            
            # Create new workspace
            new_workspace = DatabaseWorkspace(workspace_path)
            
            # Validate the workspace
            validation = new_workspace.validate_workspace()
            if not validation['is_valid']:
                return False
            
            self._current_workspace = new_workspace
            return True
            
        except Exception as e:
            print(f"Failed to set workspace: {e}")
            return False
    
    def create_new_workspace(self, workspace_path: str) -> bool:
        """Create and set a new workspace.
        
        Args:
            workspace_path: Path where to create new workspace
            
        Returns:
            bool: True if workspace was created and set successfully
        """
        try:
            new_workspace = DatabaseWorkspace(workspace_path)
            
            if not new_workspace.initialize_workspace(create_missing=True):
                return False
            
            # Close current workspace database connection if exists
            if self._current_workspace is not None:
                self._current_workspace.close_database_connection()
            
            self._current_workspace = new_workspace
            return True
            
        except Exception as e:
            print(f"Failed to create new workspace: {e}")
            return False
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about current workspace."""
        if self._current_workspace is None:
            return {'error': 'No active workspace'}
        
        return self._current_workspace.get_workspace_info()


# Global workspace manager instance
_workspace_manager = WorkspaceManager()


def get_workspace_manager() -> WorkspaceManager:
    """Get the global workspace manager."""
    return _workspace_manager


def get_current_workspace() -> DatabaseWorkspace:
    """Get the current active workspace."""
    return _workspace_manager.get_current_workspace()
