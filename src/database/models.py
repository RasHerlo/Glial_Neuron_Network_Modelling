"""
Database models and schema definitions for the data processing pipeline.
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


class DatabaseSchema:
    """Database schema definitions."""
    
    CREATE_TABLES = [
        """
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER,
            file_format TEXT,
            description TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            job_name TEXT NOT NULL,
            job_type TEXT NOT NULL,
            parameters JSON,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
            output_path TEXT,
            error_message TEXT,
            progress REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS figures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processing_job_id INTEGER,
            dataset_id INTEGER,
            figure_name TEXT NOT NULL,
            figure_path TEXT NOT NULL,
            figure_type TEXT,
            creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parameters JSON,
            description TEXT,
            thumbnail_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (processing_job_id) REFERENCES processing_jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processing_job_id INTEGER NOT NULL,
            result_name TEXT NOT NULL,
            result_type TEXT NOT NULL,
            result_data JSON,
            file_path TEXT,
            summary_statistics JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (processing_job_id) REFERENCES processing_jobs (id) ON DELETE CASCADE
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference_key TEXT UNIQUE NOT NULL,
            preference_value JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_datasets_name ON datasets (name)",
        "CREATE INDEX IF NOT EXISTS idx_datasets_import_date ON datasets (import_date)",
        "CREATE INDEX IF NOT EXISTS idx_processing_jobs_dataset_id ON processing_jobs (dataset_id)",
        "CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs (status)",
        "CREATE INDEX IF NOT EXISTS idx_processing_jobs_start_time ON processing_jobs (start_time)",
        "CREATE INDEX IF NOT EXISTS idx_figures_dataset_id ON figures (dataset_id)",
        "CREATE INDEX IF NOT EXISTS idx_figures_processing_job_id ON figures (processing_job_id)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_results_processing_job_id ON analysis_results (processing_job_id)"
    ]


class Dataset:
    """Dataset model for database operations."""
    
    def __init__(self, id: Optional[int] = None, name: str = "", file_path: str = "",
                 import_date: Optional[datetime] = None, file_size: Optional[int] = None,
                 file_format: Optional[str] = None, description: str = "",
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.file_path = file_path
        self.import_date = import_date
        self.file_size = file_size
        self.file_format = file_format
        self.description = description
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'file_path': self.file_path,
            'import_date': self.import_date.isoformat() if self.import_date else None,
            'file_size': self.file_size,
            'file_format': self.file_format,
            'description': self.description,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dataset':
        """Create Dataset from dictionary."""
        dataset = cls(**data)
        if data.get('import_date') and isinstance(data['import_date'], str):
            dataset.import_date = datetime.fromisoformat(data['import_date'])
        return dataset


class ProcessingJob:
    """Processing job model for database operations."""
    
    def __init__(self, id: Optional[int] = None, dataset_id: int = 0, job_name: str = "",
                 job_type: str = "", parameters: Optional[Dict[str, Any]] = None,
                 start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                 status: str = "pending", output_path: str = "", error_message: str = "",
                 progress: float = 0.0):
        self.id = id
        self.dataset_id = dataset_id
        self.job_name = job_name
        self.job_type = job_type
        self.parameters = parameters or {}
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.output_path = output_path
        self.error_message = error_message
        self.progress = progress
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'dataset_id': self.dataset_id,
            'job_name': self.job_name,
            'job_type': self.job_type,
            'parameters': self.parameters,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'output_path': self.output_path,
            'error_message': self.error_message,
            'progress': self.progress
        }


class Figure:
    """Figure model for database operations."""
    
    def __init__(self, id: Optional[int] = None, processing_job_id: Optional[int] = None,
                 dataset_id: Optional[int] = None, figure_name: str = "",
                 figure_path: str = "", figure_type: str = "",
                 creation_date: Optional[datetime] = None,
                 parameters: Optional[Dict[str, Any]] = None,
                 description: str = "", thumbnail_path: str = ""):
        self.id = id
        self.processing_job_id = processing_job_id
        self.dataset_id = dataset_id
        self.figure_name = figure_name
        self.figure_path = figure_path
        self.figure_type = figure_type
        self.creation_date = creation_date
        self.parameters = parameters or {}
        self.description = description
        self.thumbnail_path = thumbnail_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'processing_job_id': self.processing_job_id,
            'dataset_id': self.dataset_id,
            'figure_name': self.figure_name,
            'figure_path': self.figure_path,
            'figure_type': self.figure_type,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'parameters': self.parameters,
            'description': self.description,
            'thumbnail_path': self.thumbnail_path
        }
