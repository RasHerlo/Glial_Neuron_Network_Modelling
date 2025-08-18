#!/usr/bin/env python3
"""
Environment setup script for the Glial Neuron Network Modelling Pipeline.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print("✓ Success")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python 3.8+ required, but found Python {version.major}.{version.minor}")
        return False
    
    print(f"✓ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✓ Virtual environment already exists")
        return True
    
    # Create virtual environment
    if platform.system() == "Windows":
        command = "python -m venv venv"
    else:
        command = "python3 -m venv venv"
    
    return run_command(command, "Creating virtual environment")

def activate_and_install_dependencies():
    """Activate virtual environment and install dependencies."""
    if platform.system() == "Windows":
        pip_path = "venv\\Scripts\\pip"
        activate_command = "venv\\Scripts\\activate"
    else:
        pip_path = "venv/bin/pip"
        activate_command = "source venv/bin/activate"
    
    # Upgrade pip
    if not run_command(f"{pip_path} install --upgrade pip", 
                      "Upgrading pip"):
        return False
    
    # Install dependencies
    if not run_command(f"{pip_path} install -r requirements.txt", 
                      "Installing dependencies from requirements.txt"):
        return False
    
    return True

def setup_directories():
    """Create necessary directories."""
    directories = [
        "data/raw",
        "data/processed", 
        "data/figures",
        "logs",
        "temp"
    ]
    
    print("\nCreating project directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")
    
    return True

def test_installation():
    """Test if installation was successful."""
    print("\nTesting installation...")
    
    # Test Python imports
    test_imports = [
        "pandas", "numpy", "matplotlib", "tkinter", "sqlite3"
    ]
    
    for module in test_imports:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - Failed to import")
            return False
    
    return True

def create_activation_scripts():
    """Create convenient activation scripts."""
    if platform.system() == "Windows":
        # Windows batch file
        with open("activate.bat", "w") as f:
            f.write("""@echo off
echo Activating Glial Neuron Network Modelling Pipeline environment...
call venv\\Scripts\\activate.bat
echo Environment activated! You can now run:
echo   python main.py
cmd /k
""")
        print("✓ Created activate.bat")
        
        # Windows PowerShell script
        with open("activate.ps1", "w") as f:
            f.write("""Write-Host "Activating Glial Neuron Network Modelling Pipeline environment..." -ForegroundColor Green
& .\\venv\\Scripts\\Activate.ps1
Write-Host "Environment activated! You can now run:" -ForegroundColor Green
Write-Host "  python main.py" -ForegroundColor Yellow
""")
        print("✓ Created activate.ps1")
    
    else:
        # Unix shell script
        with open("activate.sh", "w") as f:
            f.write("""#!/bin/bash
echo "Activating Glial Neuron Network Modelling Pipeline environment..."
source venv/bin/activate
echo "Environment activated! You can now run:"
echo "  python main.py"
exec "$SHELL"
""")
        os.chmod("activate.sh", 0o755)
        print("✓ Created activate.sh")

def main():
    """Main setup function."""
    print("=" * 60)
    print("Glial Neuron Network Modelling Pipeline - Environment Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        print("Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not activate_and_install_dependencies():
        print("Failed to install dependencies")
        sys.exit(1)
    
    # Setup directories
    if not setup_directories():
        print("Failed to create directories")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("Installation test failed")
        sys.exit(1)
    
    # Create activation scripts
    create_activation_scripts()
    
    print("\n" + "=" * 60)
    print("✓ SETUP COMPLETE!")
    print("=" * 60)
    print("\nTo start using the pipeline:")
    
    if platform.system() == "Windows":
        print("1. Run 'activate.bat' to activate the environment")
    else:
        print("1. Run './activate.sh' to activate the environment")
    
    print("2. Run 'python main.py' to start the application")
    print("\nOr simply run 'python main.py' directly (it will use the virtual environment)")

if __name__ == "__main__":
    main()
