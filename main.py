#!/usr/bin/env python3
"""
Main launcher script for Glial Neuron Network Modelling Pipeline.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging():
    """Set up logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "pipeline.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'pandas', 'numpy', 'matplotlib', 'tkinter'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Error: Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease install dependencies using:")
        print("  pip install -r requirements.txt")
        print("or")
        print("  conda env create -f environment.yml")
        return False
    
    return True

def main():
    """Main entry point."""
    print("=" * 60)
    print("Glial Neuron Network Modelling - Data Processing Pipeline")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Glial Neuron Network Modelling Pipeline")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Import and start the main GUI
        from src.gui.main_menu import MainMenuGUI
        
        logger.info("Initializing main GUI...")
        app = MainMenuGUI()
        
        logger.info("Starting GUI main loop...")
        app.run()
        
    except ImportError as e:
        logger.error(f"Failed to import GUI modules: {e}")
        print(f"\nError: Failed to import GUI modules: {e}")
        print("Please ensure all dependencies are installed correctly.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    
    finally:
        logger.info("Application shutdown")

if __name__ == "__main__":
    main()
