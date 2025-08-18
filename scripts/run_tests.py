#!/usr/bin/env python3
"""
Test runner script for the Glial Neuron Network Modelling Pipeline.
"""

import sys
import os
import unittest
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    
    test_dir = Path("tests")
    if not test_dir.exists():
        print("No tests directory found. Creating basic test structure...")
        create_basic_tests()
    
    try:
        # Try to use pytest if available
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        # Fall back to unittest
        print("pytest not found, using unittest...")
        loader = unittest.TestLoader()
        suite = loader.discover('tests', pattern='test_*.py')
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()

def create_basic_tests():
    """Create basic test structure."""
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Create __init__.py
    (test_dir / "__init__.py").write_text("")
    
    # Create basic database test
    with open(test_dir / "test_database.py", "w") as f:
        f.write("""import unittest
import tempfile
import os
from src.database.connection import DatabaseConnection
from src.database.operations import DatasetOperations

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db = DatabaseConnection(self.temp_db.name)
    
    def tearDown(self):
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def test_database_creation(self):
        \"\"\"Test database creation.\"\"\"
        info = self.db.get_database_info()
        self.assertIn('datasets', info['tables'])
        self.assertIn('processing_jobs', info['tables'])
        self.assertIn('figures', info['tables'])
    
    def test_dataset_operations(self):
        \"\"\"Test basic dataset operations.\"\"\"
        # Create a dataset
        dataset_id = DatasetOperations.create_dataset(
            name="test_dataset",
            file_path="/test/path.csv",
            file_format="csv",
            description="Test dataset"
        )
        self.assertIsNotNone(dataset_id)
        
        # Retrieve the dataset
        dataset = DatasetOperations.get_dataset(dataset_id)
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.name, "test_dataset")

if __name__ == '__main__':
    unittest.main()
""")
    
    # Create basic GUI test
    with open(test_dir / "test_gui.py", "w") as f:
        f.write("""import unittest
from unittest.mock import patch
import tkinter as tk

class TestGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during testing
    
    def tearDown(self):
        self.root.destroy()
    
    def test_main_menu_import(self):
        \"\"\"Test that main menu can be imported.\"\"\"
        try:
            from src.gui.main_menu import MainMenuGUI
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import MainMenuGUI: {e}")
    
    @patch('tkinter.messagebox.showinfo')
    def test_gui_initialization(self, mock_showinfo):
        \"\"\"Test GUI initialization.\"\"\"
        try:
            from src.gui.main_menu import MainMenuGUI
            # Don't actually run the GUI, just test initialization
            app = MainMenuGUI()
            self.assertIsNotNone(app.root)
        except Exception as e:
            self.fail(f"GUI initialization failed: {e}")

if __name__ == '__main__':
    unittest.main()
""")
    
    print("✓ Created basic test structure")

def run_import_tests():
    """Test that all modules can be imported."""
    print("\nTesting module imports...")
    
    modules_to_test = [
        'src.database.models',
        'src.database.connection', 
        'src.database.operations',
        'src.gui.main_menu',
        'src.data_processing.importers',
        'src.data_processing.processors',
        'src.config.settings'
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module} - {e}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0

def run_database_connectivity_test():
    """Test database connectivity."""
    print("\nTesting database connectivity...")
    
    try:
        from src.database.connection import get_database
        db = get_database("test_connection.db")
        info = db.get_database_info()
        print(f"✓ Database created with {len(info['tables'])} tables")
        
        # Clean up
        import os
        if os.path.exists("test_connection.db"):
            os.remove("test_connection.db")
        
        return True
    except Exception as e:
        print(f"✗ Database connectivity test failed: {e}")
        return False

def run_gui_test():
    """Test GUI components."""
    print("\nTesting GUI components...")
    
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        
        from src.gui.main_menu import MainMenuGUI
        print("✓ Main menu GUI can be imported")
        
        root.destroy()
        return True
    except Exception as e:
        print(f"✗ GUI test failed: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("Glial Neuron Network Modelling Pipeline - Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    # Test imports
    if not run_import_tests():
        all_passed = False
    
    # Test database connectivity
    if not run_database_connectivity_test():
        all_passed = False
    
    # Test GUI
    if not run_gui_test():
        all_passed = False
    
    # Run unit tests
    if not run_unit_tests():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("The pipeline is ready to use.")
    else:
        print("✗ SOME TESTS FAILED!")
        print("Please check the errors above and fix them before using the pipeline.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
