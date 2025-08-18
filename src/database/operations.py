"""
Database operations for CRUD functionality.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import os

from .connection import get_database
from .models import Dataset, ProcessingJob, Figure


class DatasetOperations:
    """Database operations for datasets."""
    
    @staticmethod
    def create_dataset(name: str, file_path: str, file_format: str = None,
                      description: str = "", metadata: Dict[str, Any] = None) -> int:
        """Create a new dataset record."""
        db = get_database()
        
        # Get file size if file exists
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        
        query = """
            INSERT INTO datasets (name, file_path, file_size, file_format, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        return db.execute_insert(query, (
            name, file_path, file_size, file_format, description, metadata or {}
        ))
    
    @staticmethod
    def get_dataset(dataset_id: int) -> Optional[Dataset]:
        """Get a dataset by ID."""
        db = get_database()
        query = "SELECT * FROM datasets WHERE id = ?"
        result = db.execute_one(query, (dataset_id,))
        
        if result:
            return Dataset(
                id=result[0], name=result[1], file_path=result[2],
                import_date=datetime.fromisoformat(result[3]) if result[3] else None,
                file_size=result[4], file_format=result[5], description=result[6],
                metadata=result[7] or {}
            )
        return None
    
    @staticmethod
    def get_dataset_by_name(name: str) -> Optional[Dataset]:
        """Get a dataset by name."""
        db = get_database()
        query = "SELECT * FROM datasets WHERE name = ?"
        result = db.execute_one(query, (name,))
        
        if result:
            return Dataset(
                id=result[0], name=result[1], file_path=result[2],
                import_date=datetime.fromisoformat(result[3]) if result[3] else None,
                file_size=result[4], file_format=result[5], description=result[6],
                metadata=result[7] or {}
            )
        return None
    
    @staticmethod
    def list_datasets(limit: int = None, offset: int = 0) -> List[Dataset]:
        """List all datasets with optional pagination."""
        db = get_database()
        query = "SELECT * FROM datasets ORDER BY import_date DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        results = db.execute_query(query)
        datasets = []
        
        for result in results:
            datasets.append(Dataset(
                id=result[0], name=result[1], file_path=result[2],
                import_date=datetime.fromisoformat(result[3]) if result[3] else None,
                file_size=result[4], file_format=result[5], description=result[6],
                metadata=result[7] or {}
            ))
        
        return datasets
    
    @staticmethod
    def update_dataset(dataset_id: int, **kwargs) -> bool:
        """Update dataset fields."""
        db = get_database()
        
        # Build dynamic update query
        valid_fields = ['name', 'file_path', 'file_format', 'description', 'metadata']
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                params.append(value)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(dataset_id)
        
        query = f"UPDATE datasets SET {', '.join(updates)} WHERE id = ?"
        return db.execute_update(query, tuple(params)) > 0
    
    @staticmethod
    def delete_dataset(dataset_id: int) -> bool:
        """Delete a dataset (cascades to related records)."""
        db = get_database()
        query = "DELETE FROM datasets WHERE id = ?"
        return db.execute_update(query, (dataset_id,)) > 0
    
    @staticmethod
    def search_datasets(search_term: str) -> List[Dataset]:
        """Search datasets by name or description."""
        db = get_database()
        query = """
            SELECT * FROM datasets 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY import_date DESC
        """
        search_pattern = f"%{search_term}%"
        results = db.execute_query(query, (search_pattern, search_pattern))
        
        datasets = []
        for result in results:
            datasets.append(Dataset(
                id=result[0], name=result[1], file_path=result[2],
                import_date=datetime.fromisoformat(result[3]) if result[3] else None,
                file_size=result[4], file_format=result[5], description=result[6],
                metadata=result[7] or {}
            ))
        
        return datasets


class ProcessingJobOperations:
    """Database operations for processing jobs."""
    
    @staticmethod
    def create_job(dataset_id: int, job_name: str, job_type: str,
                  parameters: Dict[str, Any] = None) -> int:
        """Create a new processing job."""
        db = get_database()
        query = """
            INSERT INTO processing_jobs (dataset_id, job_name, job_type, parameters)
            VALUES (?, ?, ?, ?)
        """
        return db.execute_insert(query, (dataset_id, job_name, job_type, parameters or {}))
    
    @staticmethod
    def get_job(job_id: int) -> Optional[ProcessingJob]:
        """Get a processing job by ID."""
        db = get_database()
        query = "SELECT * FROM processing_jobs WHERE id = ?"
        result = db.execute_one(query, (job_id,))
        
        if result:
            return ProcessingJob(
                id=result[0], dataset_id=result[1], job_name=result[2], job_type=result[3],
                parameters=result[4] or {}, 
                start_time=datetime.fromisoformat(result[5]) if result[5] else None,
                end_time=datetime.fromisoformat(result[6]) if result[6] else None,
                status=result[7], output_path=result[8], error_message=result[9],
                progress=result[10]
            )
        return None
    
    @staticmethod
    def update_job_status(job_id: int, status: str, progress: float = None,
                         error_message: str = None, output_path: str = None) -> bool:
        """Update job status and related fields."""
        db = get_database()
        
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        if output_path is not None:
            updates.append("output_path = ?")
            params.append(output_path)
        
        if status == 'running' and progress == 0:
            updates.append("start_time = CURRENT_TIMESTAMP")
        elif status in ['completed', 'failed', 'cancelled']:
            updates.append("end_time = CURRENT_TIMESTAMP")
        
        params.append(job_id)
        query = f"UPDATE processing_jobs SET {', '.join(updates)} WHERE id = ?"
        
        return db.execute_update(query, tuple(params)) > 0
    
    @staticmethod
    def list_jobs_for_dataset(dataset_id: int) -> List[ProcessingJob]:
        """List all jobs for a specific dataset."""
        db = get_database()
        query = """
            SELECT * FROM processing_jobs 
            WHERE dataset_id = ? 
            ORDER BY start_time DESC
        """
        results = db.execute_query(query, (dataset_id,))
        
        jobs = []
        for result in results:
            jobs.append(ProcessingJob(
                id=result[0], dataset_id=result[1], job_name=result[2], job_type=result[3],
                parameters=result[4] or {},
                start_time=datetime.fromisoformat(result[5]) if result[5] else None,
                end_time=datetime.fromisoformat(result[6]) if result[6] else None,
                status=result[7], output_path=result[8], error_message=result[9],
                progress=result[10]
            ))
        
        return jobs
    
    @staticmethod
    def get_active_jobs() -> List[ProcessingJob]:
        """Get all currently active (running) jobs."""
        db = get_database()
        query = """
            SELECT * FROM processing_jobs 
            WHERE status IN ('pending', 'running') 
            ORDER BY start_time ASC
        """
        results = db.execute_query(query)
        
        jobs = []
        for result in results:
            jobs.append(ProcessingJob(
                id=result[0], dataset_id=result[1], job_name=result[2], job_type=result[3],
                parameters=result[4] or {},
                start_time=datetime.fromisoformat(result[5]) if result[5] else None,
                end_time=datetime.fromisoformat(result[6]) if result[6] else None,
                status=result[7], output_path=result[8], error_message=result[9],
                progress=result[10]
            ))
        
        return jobs


class FigureOperations:
    """Database operations for figures."""
    
    @staticmethod
    def create_figure(figure_name: str, figure_path: str, figure_type: str = "png",
                     processing_job_id: int = None, dataset_id: int = None,
                     parameters: Dict[str, Any] = None, description: str = "",
                     thumbnail_path: str = "") -> int:
        """Create a new figure record."""
        db = get_database()
        query = """
            INSERT INTO figures (processing_job_id, dataset_id, figure_name, figure_path, 
                               figure_type, parameters, description, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        return db.execute_insert(query, (
            processing_job_id, dataset_id, figure_name, figure_path,
            figure_type, parameters or {}, description, thumbnail_path
        ))
    
    @staticmethod
    def list_figures_for_dataset(dataset_id: int) -> List[Figure]:
        """List all figures for a specific dataset."""
        db = get_database()
        query = """
            SELECT * FROM figures 
            WHERE dataset_id = ? 
            ORDER BY creation_date DESC
        """
        results = db.execute_query(query, (dataset_id,))
        
        figures = []
        for result in results:
            figures.append(Figure(
                id=result[0], processing_job_id=result[1], dataset_id=result[2],
                figure_name=result[3], figure_path=result[4], figure_type=result[5],
                creation_date=datetime.fromisoformat(result[6]) if result[6] else None,
                parameters=result[7] or {}, description=result[8],
                thumbnail_path=result[9]
            ))
        
        return figures
    
    @staticmethod
    def list_figures_for_job(job_id: int) -> List[Figure]:
        """List all figures for a specific processing job."""
        db = get_database()
        query = """
            SELECT * FROM figures 
            WHERE processing_job_id = ? 
            ORDER BY creation_date DESC
        """
        results = db.execute_query(query, (job_id,))
        
        figures = []
        for result in results:
            figures.append(Figure(
                id=result[0], processing_job_id=result[1], dataset_id=result[2],
                figure_name=result[3], figure_path=result[4], figure_type=result[5],
                creation_date=datetime.fromisoformat(result[6]) if result[6] else None,
                parameters=result[7] or {}, description=result[8],
                thumbnail_path=result[9]
            ))
        
        return figures


class UserPreferencesOperations:
    """Database operations for user preferences."""
    
    @staticmethod
    def get_preference(key: str, default_value: Any = None) -> Any:
        """Get a user preference value."""
        db = get_database()
        query = "SELECT preference_value FROM user_preferences WHERE preference_key = ?"
        result = db.execute_one(query, (key,))
        
        return result[0] if result else default_value
    
    @staticmethod
    def set_preference(key: str, value: Any) -> bool:
        """Set a user preference value."""
        db = get_database()
        query = """
            INSERT OR REPLACE INTO user_preferences (preference_key, preference_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """
        return db.execute_update(query, (key, value)) > 0
    
    @staticmethod
    def get_all_preferences() -> Dict[str, Any]:
        """Get all user preferences."""
        db = get_database()
        query = "SELECT preference_key, preference_value FROM user_preferences"
        results = db.execute_query(query)
        
        return {row[0]: row[1] for row in results}
