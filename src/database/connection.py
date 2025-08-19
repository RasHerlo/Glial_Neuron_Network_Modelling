"""
Database connection management for SQLite database.
"""

import sqlite3
import os
import threading
from typing import Optional
from contextlib import contextmanager
import json
from datetime import datetime
from .models import DatabaseSchema


class DatabaseConnection:
    """Thread-safe SQLite database connection manager."""
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_db_directory()
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Use WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            # Custom JSON adapter for storing complex data
            self._setup_json_adapter(self._local.connection)
            
        return self._local.connection
    
    def _setup_json_adapter(self, conn: sqlite3.Connection):
        """Set up JSON adapters for storing complex data types."""
        def adapt_json(obj):
            return json.dumps(obj, default=str).encode('utf-8')
        
        def convert_json(s):
            try:
                return json.loads(s.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return s.decode('utf-8')
        
        # Register adapters for dict and list types
        sqlite3.register_adapter(dict, adapt_json)
        sqlite3.register_adapter(list, adapt_json)
        sqlite3.register_converter("JSON", convert_json)
    
    def _initialize_database(self):
        """Initialize database with tables and indexes."""
        with self.get_cursor() as cursor:
            # Create tables
            for table_sql in DatabaseSchema.CREATE_TABLES:
                cursor.execute(table_sql)
            
            # Create indexes
            for index_sql in DatabaseSchema.CREATE_INDEXES:
                cursor.execute(index_sql)
            
            # Insert default preferences if they don't exist
            self._setup_default_preferences(cursor)
    
    def _setup_default_preferences(self, cursor: sqlite3.Cursor):
        """Set up default user preferences."""
        default_preferences = {
            'default_data_format': 'csv',
            'default_figure_format': 'png',
            'auto_backup': True,
            'max_recent_datasets': 10,
            'theme': 'light',
            'default_processing_params': {
                'smoothing_factor': 0.5,
                'noise_threshold': 0.1
            }
        }
        
        for key, value in default_preferences.items():
            cursor.execute("""
                INSERT OR IGNORE INTO user_preferences (preference_key, preference_value)
                VALUES (?, ?)
            """, (key, value))
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic transaction management."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Execute a SELECT query and return one result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the last row ID."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an UPDATE/DELETE query and return affected row count."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def backup_database(self, backup_path: str):
        """Create a backup of the database."""
        with sqlite3.connect(backup_path) as backup_conn:
            self._get_connection().backup(backup_conn)
    
    def get_database_info(self) -> dict:
        """Get information about the database."""
        with self.get_cursor() as cursor:
            # Get table information
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get row counts for each table
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            
            # Get database file size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                'database_path': self.db_path,
                'database_size_bytes': db_size,
                'tables': tables,
                'table_row_counts': table_counts,
                'last_modified': datetime.fromtimestamp(
                    os.path.getmtime(self.db_path)
                ).isoformat() if os.path.exists(self.db_path) else None
            }
    
    def close(self):
        """Close the database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


# Global database instance
_db_instance: Optional[DatabaseConnection] = None


def get_database(db_path: str = "data/pipeline.db") -> DatabaseConnection:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection(db_path)
    return _db_instance


def close_database():
    """Close the global database connection."""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None
