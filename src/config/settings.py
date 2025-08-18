"""
Configuration settings for the data processing pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FIGURES_DIR = DATA_DIR / "figures"
LOGS_DIR = BASE_DIR / "logs"

# Database settings
DATABASE_CONFIG = {
    'default_path': str(DATA_DIR / "pipeline.db"),
    'backup_dir': str(DATA_DIR / "backups"),
    'auto_backup': True,
    'backup_interval_hours': 24
}

# GUI settings
GUI_CONFIG = {
    'theme': 'light',
    'window_size': {
        'main_menu': '800x600',
        'data_import': '700x500',
        'data_processing': '800x600',
        'figure_generation': '900x700'
    },
    'font_family': 'Arial',
    'font_sizes': {
        'title': 16,
        'subtitle': 12,
        'normal': 10,
        'small': 9
    }
}

# Data processing settings
PROCESSING_CONFIG = {
    'default_chunk_size': 10000,
    'max_memory_usage_gb': 4,
    'temp_dir': str(BASE_DIR / "temp"),
    'supported_formats': ['.csv', '.xlsx', '.txt', '.json', '.h5'],
    'default_encoding': 'utf-8',
    'auto_detect_delimiter': True
}

# Figure generation settings
FIGURE_CONFIG = {
    'default_format': 'png',
    'default_dpi': 300,
    'default_size': (10, 6),
    'color_palette': 'Set1',
    'style': 'seaborn-v0_8',
    'save_thumbnails': True,
    'thumbnail_size': (200, 150)
}

# Logging settings
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_handler': {
        'enabled': True,
        'filename': str(LOGS_DIR / "pipeline.log"),
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    },
    'console_handler': {
        'enabled': True
    }
}

# Analysis settings
ANALYSIS_CONFIG = {
    'correlation_threshold': 0.7,
    'outlier_methods': ['iqr', 'zscore'],
    'default_confidence_level': 0.95,
    'max_categories_display': 20
}

# Performance settings
PERFORMANCE_CONFIG = {
    'parallel_processing': True,
    'max_workers': os.cpu_count(),
    'progress_update_interval': 0.1,  # seconds
    'cache_results': True,
    'cache_size_mb': 100
}

# File validation settings
VALIDATION_CONFIG = {
    'max_file_size_mb': 500,
    'allowed_extensions': ['.csv', '.xlsx', '.xls', '.txt', '.json', '.h5', '.mat'],
    'scan_for_viruses': False,  # Would require additional antivirus integration
    'validate_data_integrity': True
}

# Export settings
EXPORT_CONFIG = {
    'default_formats': ['csv', 'xlsx', 'json'],
    'compression': {
        'enabled': False,
        'format': 'gzip'
    },
    'include_metadata': True,
    'timestamp_format': '%Y%m%d_%H%M%S'
}


class Settings:
    """Settings management class."""
    
    def __init__(self):
        self._settings = {
            'database': DATABASE_CONFIG,
            'gui': GUI_CONFIG,
            'processing': PROCESSING_CONFIG,
            'figures': FIGURE_CONFIG,
            'logging': LOGGING_CONFIG,
            'analysis': ANALYSIS_CONFIG,
            'performance': PERFORMANCE_CONFIG,
            'validation': VALIDATION_CONFIG,
            'export': EXPORT_CONFIG
        }
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            DATA_DIR,
            RAW_DATA_DIR,
            PROCESSED_DATA_DIR,
            FIGURES_DIR,
            LOGS_DIR,
            Path(DATABASE_CONFIG['backup_dir']),
            Path(PROCESSING_CONFIG['temp_dir'])
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Get configuration value."""
        if section not in self._settings:
            return default
        
        if key is None:
            return self._settings[section]
        
        return self._settings[section].get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value."""
        if section not in self._settings:
            self._settings[section] = {}
        
        self._settings[section][key] = value
    
    def get_database_path(self) -> str:
        """Get database file path."""
        return self.get('database', 'default_path')
    
    def get_data_directories(self) -> Dict[str, str]:
        """Get data directory paths."""
        return {
            'base': str(DATA_DIR),
            'raw': str(RAW_DATA_DIR),
            'processed': str(PROCESSED_DATA_DIR),
            'figures': str(FIGURES_DIR),
            'logs': str(LOGS_DIR)
        }
    
    def is_file_format_supported(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in self.get('processing', 'supported_formats', [])
    
    def get_max_file_size(self) -> int:
        """Get maximum allowed file size in bytes."""
        return self.get('validation', 'max_file_size_mb', 500) * 1024 * 1024
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update settings from dictionary."""
        for section, values in config_dict.items():
            if section in self._settings:
                self._settings[section].update(values)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self._settings.copy()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get global settings instance."""
    return settings
