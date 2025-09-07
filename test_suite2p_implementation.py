"""
Simple test script to verify Suite2p multi-channel implementation.
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def create_test_data():
    """Create test Suite2p folder structure with sample .npy files."""
    test_data_path = Path("test_suite2p_data")
    
    # Create folder structure
    for channel in ["SUPPORT_ChanA", "SUPPORT_ChanB"]:
        plane_path = test_data_path / channel / "derippled" / "suite2p" / "plane0"
        plane_path.mkdir(parents=True, exist_ok=True)
        
        # Create sample .npy files
        # F.npy - smaller matrix (50 cells, 1000 frames)
        F_data = np.random.rand(50, 1000).astype(np.float32)
        np.save(plane_path / "F.npy", F_data)
        
        # F_spikes.npy - same dimensions but different data
        spikes_data = np.random.rand(50, 1000).astype(np.float32)
        np.save(plane_path / "F_spikes.npy", spikes_data)
        
        # spks.npy - binary spike data
        binary_spikes = (np.random.rand(50, 1000) > 0.95).astype(np.float32)
        np.save(plane_path / "spks.npy", binary_spikes)
    
    print(f"Created test data structure at: {test_data_path.absolute()}")
    return str(test_data_path.absolute())

def test_npy_importer():
    """Test the NPY importer functionality."""
    print("\n=== Testing NPY Importer ===")
    
    from src.data_processing.importers import NPYImporter
    
    # Create test data
    test_data_path = create_test_data()
    test_file = Path(test_data_path) / "SUPPORT_ChanA" / "derippled" / "suite2p" / "plane0" / "F_spikes.npy"
    
    importer = NPYImporter()
    result = importer.import_file(str(test_file))
    
    if result['success']:
        print(f"✓ Successfully imported {test_file}")
        print(f"  Shape: {result['statistics']['shape']}")
        print(f"  Data type: {result['statistics']['dtype']}")
        print(f"  Row labels: {result['row_labels'][:5]}...")  # First 5
        print(f"  Col labels: {result['col_labels'][:5]}...")  # First 5
    else:
        print(f"✗ Failed to import: {result['message']}")

def test_suite2p_detector():
    """Test the Suite2p dataset detector."""
    print("\n=== Testing Suite2p Detector ===")
    
    from src.data_processing.importers import Suite2pDatasetDetector
    
    # Use existing test data
    test_data_path = Path("test_suite2p_data")
    if not test_data_path.exists():
        test_data_path = create_test_data()
    
    detector = Suite2pDatasetDetector()
    results = detector.scan_data_folder(str(test_data_path))
    
    if results['success']:
        print(f"✓ Successfully scanned folder")
        print(f"  Found {len(results['channels'])} channels")
        for channel_name, channel_info in results['channels'].items():
            print(f"  {channel_name}: {len(channel_info.get('npy_files', []))} .npy files")
            if channel_info.get('npy_files'):
                print(f"    Files: {', '.join(channel_info['npy_files'])}")
    else:
        print(f"✗ Failed to scan: {results['message']}")

def test_database_schema():
    """Test that the database schema includes relationships table."""
    print("\n=== Testing Database Schema ===")
    
    from src.database.models import DatabaseSchema
    
    # Check if relationships table is in schema
    relationships_table_found = False
    for table_sql in DatabaseSchema.CREATE_TABLES:
        if "dataset_relationships" in table_sql:
            relationships_table_found = True
            break
    
    if relationships_table_found:
        print("✓ Dataset relationships table found in schema")
    else:
        print("✗ Dataset relationships table not found in schema")
    
    # Check if relationships indexes are in schema
    relationships_index_found = False
    for index_sql in DatabaseSchema.CREATE_INDEXES:
        if "dataset_relationships" in index_sql:
            relationships_index_found = True
            break
    
    if relationships_index_found:
        print("✓ Dataset relationships indexes found in schema")
    else:
        print("✗ Dataset relationships indexes not found in schema")

def test_workspace_integration():
    """Test that the workspace system works with new functionality."""
    print("\n=== Testing Workspace Integration ===")
    
    try:
        from src.database.workspace import get_current_workspace
        from src.utils.folder_manager import DatasetFolderManager
        
        # Get current workspace
        workspace = get_current_workspace()
        print(f"✓ Current workspace: {workspace.workspace_path}")
        
        # Test folder manager with workspace
        folder_manager = DatasetFolderManager()
        print(f"✓ Folder manager datasets path: {folder_manager.datasets_dir}")
        
        # Verify they match
        if str(folder_manager.datasets_dir) == str(workspace.datasets_path):
            print("✓ Folder manager correctly uses workspace paths")
        else:
            print("✗ Folder manager not using workspace paths correctly")
            
    except Exception as e:
        print(f"✗ Workspace integration error: {e}")

def cleanup_test_data():
    """Clean up test data."""
    import shutil
    test_path = Path("test_suite2p_data")
    if test_path.exists():
        shutil.rmtree(test_path)
        print(f"Cleaned up test data at: {test_path}")

if __name__ == "__main__":
    print("Testing Suite2p Multi-Channel Implementation")
    print("=" * 50)
    
    try:
        test_npy_importer()
        test_suite2p_detector() 
        test_database_schema()
        test_workspace_integration()
        
        print("\n" + "=" * 50)
        print("All tests completed! 🎉")
        print("\nTo test the GUI:")
        print("1. Run: python main.py")
        print("2. Click 'Data Import'")
        print("3. Click 'Suite2p Multi-Channel' button")
        print("4. Select the 'test_suite2p_data' folder")
        
        # Ask if user wants to clean up
        response = input("\nClean up test data? (y/n): ").lower().strip()
        if response == 'y':
            cleanup_test_data()
        else:
            print("Test data preserved for GUI testing")
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
