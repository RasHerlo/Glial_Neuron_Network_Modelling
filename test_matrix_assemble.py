#!/usr/bin/env python3
"""
Test script for MatrixAssemble functionality
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_processing.processors import DataProcessingManager

def test_matrix_assemble():
    """Test the MatrixAssemble processor functionality."""
    print("Testing MatrixAssemble functionality...")
    
    # Create processing manager
    manager = DataProcessingManager()
    
    # Check if MatrixAssemble processor is available
    matrix_assemble_processor = manager.get_processor("MatrixAssemble")
    if not matrix_assemble_processor:
        print("❌ MatrixAssemble processor not found!")
        return False
    
    print("✅ MatrixAssemble processor found")
    
    # Check available processors
    available_processors = manager.get_available_processors()
    print(f"Available processors: {available_processors}")
    
    # Check if MatrixAssemble is in the list
    if "MatrixAssemble" not in available_processors:
        print("❌ MatrixAssemble not in available processors list!")
        return False
    
    print("✅ MatrixAssemble is in available processors list")
    
    # Test finding dataset folders
    dataset_folders = matrix_assemble_processor.find_dataset_folders()
    print(f"Found dataset folders: {dataset_folders}")
    
    if not dataset_folders:
        print("❌ No dataset folders found!")
        return False
    
    print("✅ Dataset folders found")
    
    # Test finding raster matrices for first dataset
    first_dataset = dataset_folders[0]
    raster_matrices = matrix_assemble_processor.find_raster_matrices(first_dataset)
    print(f"Raster matrices in {first_dataset}: {raster_matrices}")
    
    if not raster_matrices:
        print("❌ No raster matrices found!")
        return False
    
    print("✅ Raster matrices found")
    
    # Test parameter validation
    test_parameters = {
        'base_set': first_dataset,
        'base_matrix': raster_matrices[0],
        'add_set': first_dataset,
        'add_matrix': raster_matrices[0] if len(raster_matrices) > 0 else raster_matrices[0],
        'new_dataset_name': 'test_assembled'
    }
    
    is_valid = matrix_assemble_processor.validate_parameters(test_parameters)
    print(f"Parameter validation result: {is_valid}")
    
    if not is_valid:
        print("❌ Parameter validation failed!")
        return False
    
    print("✅ Parameter validation passed")
    
    print("\n🎉 All MatrixAssemble tests passed!")
    return True

if __name__ == "__main__":
    success = test_matrix_assemble()
    sys.exit(0 if success else 1)
