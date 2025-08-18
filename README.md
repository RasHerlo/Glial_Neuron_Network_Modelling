# Glial Neuron Network Modelling - Data Processing Pipeline

A comprehensive, GUI-based data processing pipeline for glial neuron network analysis and visualization.

## Features

- **Intuitive GUI Interface**: User-friendly graphical interface with interconnected windows
- **Data Import**: Support for multiple file formats (CSV, Excel, JSON, text files)
- **Data Processing**: Built-in processors for cleaning, smoothing, filtering, and statistical analysis
- **Figure Generation**: Create publication-ready visualizations and plots
- **Database Integration**: SQLite database for tracking datasets, processing jobs, and results
- **Self-Contained**: Complete virtual environment setup with all dependencies

## Quick Start

### Option 1: Automated Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Glial_Neuron_Network_Modelling
```

2. Run the automated setup:
```bash
python scripts/setup_environment.py
```

3. Launch the application:
```bash
python main.py
```

### Option 2: Manual Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Project Structure

```
Glial_Neuron_Network_Modelling/
├── src/                          # Source code
│   ├── gui/                      # GUI components
│   │   ├── main_menu.py          # Main menu interface
│   │   ├── data_import_gui.py    # Data import interface
│   │   ├── data_processing_gui.py # Data processing interface
│   │   └── figure_generation_gui.py # Figure generation interface
│   ├── database/                 # Database management
│   │   ├── models.py             # Database models
│   │   ├── connection.py         # Database connection
│   │   └── operations.py         # Database operations
│   ├── data_processing/          # Data processing modules
│   │   ├── importers.py          # Data importers
│   │   └── processors.py         # Data processors
│   ├── config/                   # Configuration
│   │   └── settings.py           # Application settings
│   └── utils/                    # Utility functions
├── data/                         # Data directories
│   ├── raw/                      # Raw input data
│   ├── processed/                # Processed data
│   └── figures/                  # Generated figures
├── scripts/                      # Automation scripts
│   ├── setup_environment.py     # Environment setup
│   ├── run_tests.py             # Test runner
│   └── backup_data.py           # Data backup utility
├── tests/                        # Unit tests
├── docs/                         # Documentation
├── main.py                       # Main launcher script
├── requirements.txt              # Python dependencies
├── environment.yml               # Conda environment
└── setup.py                     # Package setup
```

## Usage Guide

### 1. Data Import

- Launch the application and navigate to "Data Import"
- Select files or directories containing your data
- Specify dataset names and descriptions
- Choose whether to copy files to the project directory
- Import data with automatic format detection

### 2. Data Processing

- Select datasets from the "Data Processing" interface
- Choose processing operations:
  - **Data Cleaning**: Handle missing values, duplicates, outliers
  - **Smoothing**: Apply various smoothing filters
  - **Filtering**: Filter data based on criteria
  - **Statistical Analysis**: Generate comprehensive statistics
- Monitor processing progress in real-time
- View processing history and results

### 3. Figure Generation

- Create visualizations from processed or raw data
- Support for multiple plot types:
  - Line plots, scatter plots, histograms
  - Box plots, heatmaps, 3D plots
- Customizable parameters and styling
- Export in multiple formats (PNG, PDF, SVG, etc.)
- Browse and manage generated figures

### 4. Data Management

- Browse all imported datasets
- View processing history and job status
- Search and filter data by various criteria
- Database backup and restore functionality

## Supported File Formats

### Input Formats
- **CSV files** (.csv, .tsv)
- **Excel files** (.xlsx, .xls)
- **JSON files** (.json)
- **Text files** (.txt, .dat)
- **HDF5 files** (.h5) - with h5py
- **MATLAB files** (.mat) - with scipy

### Output Formats
- **Figures**: PNG, PDF, SVG, JPG, EPS
- **Data**: CSV, Excel, JSON
- **Reports**: Text, HTML (planned)

## Database Schema

The application uses SQLite to track:
- **Datasets**: Imported data files with metadata
- **Processing Jobs**: Data processing operations and status
- **Figures**: Generated visualizations and parameters
- **Analysis Results**: Statistical analysis outcomes
- **User Preferences**: Application settings

## Development

### Running Tests

```bash
python scripts/run_tests.py
```

### Code Structure

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Document functions and classes
- Write unit tests for new features

### Adding New Processors

1. Create a new processor class in `src/data_processing/processors.py`
2. Inherit from `BaseProcessor`
3. Implement required methods: `process()`, `get_default_parameters()`
4. Register the processor in `DataProcessingManager`

### Adding New Importers

1. Create a new importer class in `src/data_processing/importers.py`
2. Inherit from `BaseImporter`
3. Implement required methods: `import_file()`, `can_import()`
4. Register the importer in `DataImportManager`

## Backup and Maintenance

### Creating Backups

```bash
python scripts/backup_data.py
```

Options:
- `--database-only`: Backup only the database
- `--no-raw`: Skip raw data backup
- `--no-processed`: Skip processed data backup
- `--no-figures`: Skip figures backup
- `--list`: List available backups

### Database Management

The SQLite database is automatically created and maintained. For advanced operations:

```python
from src.database.connection import get_database

db = get_database()
info = db.get_database_info()
print(info)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **GUI Not Starting**: Check that tkinter is available
   ```bash
   python -c "import tkinter; print('OK')"
   ```

3. **Database Issues**: Delete `data/pipeline.db` to reset database

4. **Memory Issues**: Reduce chunk size in settings for large files

### Getting Help

1. Check the application logs in `logs/pipeline.log`
2. Run the test suite: `python scripts/run_tests.py`
3. Verify installation: `python scripts/setup_environment.py`

## Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 4GB RAM recommended for large datasets
- **Storage**: 1GB free space for installation and data

## License

[Specify your license here - e.g., MIT, GPL, etc.]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Citation

If you use this software in your research, please cite:

```
[Add citation information here]
```

## Changelog

### Version 1.0.0
- Initial release
- Basic GUI framework
- Data import/export functionality
- SQLite database integration
- Core data processing modules
- Figure generation capabilities
A collection of processing scripts, specifically designed to take in neural and glial raster plots, and generate explorative computational models from them.
