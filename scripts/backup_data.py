#!/usr/bin/env python3
"""
Data backup script for the Glial Neuron Network Modelling Pipeline.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
import argparse

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def create_backup_directory():
    """Create backup directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def backup_database(backup_dir):
    """Backup the SQLite database."""
    print("Backing up database...")
    
    db_path = Path("data/pipeline.db")
    if not db_path.exists():
        print("✗ Database file not found")
        return False
    
    try:
        # Copy database file
        backup_db_path = backup_dir / "pipeline.db"
        shutil.copy2(db_path, backup_db_path)
        
        # Create a SQL dump as well
        dump_path = backup_dir / "pipeline_dump.sql"
        with sqlite3.connect(str(db_path)) as conn:
            with open(dump_path, 'w') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
        
        print(f"✓ Database backed up to {backup_db_path}")
        print(f"✓ SQL dump created at {dump_path}")
        return True
    except Exception as e:
        print(f"✗ Database backup failed: {e}")
        return False

def backup_data_files(backup_dir, include_raw=True, include_processed=True, include_figures=True):
    """Backup data files."""
    print("Backing up data files...")
    
    data_dir = Path("data")
    if not data_dir.exists():
        print("✗ Data directory not found")
        return False
    
    backup_data_dir = backup_dir / "data"
    backup_data_dir.mkdir(exist_ok=True)
    
    success = True
    
    # Backup raw data
    if include_raw:
        raw_dir = data_dir / "raw"
        if raw_dir.exists() and any(raw_dir.iterdir()):
            try:
                backup_raw_dir = backup_data_dir / "raw"
                shutil.copytree(raw_dir, backup_raw_dir)
                file_count = len(list(backup_raw_dir.rglob("*")))
                print(f"✓ Raw data backed up ({file_count} files)")
            except Exception as e:
                print(f"✗ Raw data backup failed: {e}")
                success = False
        else:
            print("- No raw data to backup")
    
    # Backup processed data
    if include_processed:
        processed_dir = data_dir / "processed"
        if processed_dir.exists() and any(processed_dir.iterdir()):
            try:
                backup_processed_dir = backup_data_dir / "processed"
                shutil.copytree(processed_dir, backup_processed_dir)
                file_count = len(list(backup_processed_dir.rglob("*")))
                print(f"✓ Processed data backed up ({file_count} files)")
            except Exception as e:
                print(f"✗ Processed data backup failed: {e}")
                success = False
        else:
            print("- No processed data to backup")
    
    # Backup figures
    if include_figures:
        figures_dir = data_dir / "figures"
        if figures_dir.exists() and any(figures_dir.iterdir()):
            try:
                backup_figures_dir = backup_data_dir / "figures"
                shutil.copytree(figures_dir, backup_figures_dir)
                file_count = len(list(backup_figures_dir.rglob("*")))
                print(f"✓ Figures backed up ({file_count} files)")
            except Exception as e:
                print(f"✗ Figures backup failed: {e}")
                success = False
        else:
            print("- No figures to backup")
    
    return success

def backup_configuration(backup_dir):
    """Backup configuration files."""
    print("Backing up configuration...")
    
    config_files = [
        "requirements.txt",
        "environment.yml",
        "setup.py",
        ".gitignore",
        "main.py"
    ]
    
    config_backup_dir = backup_dir / "config"
    config_backup_dir.mkdir(exist_ok=True)
    
    for config_file in config_files:
        file_path = Path(config_file)
        if file_path.exists():
            try:
                shutil.copy2(file_path, config_backup_dir / config_file)
                print(f"✓ {config_file}")
            except Exception as e:
                print(f"✗ Failed to backup {config_file}: {e}")
        else:
            print(f"- {config_file} not found")
    
    return True

def backup_logs(backup_dir):
    """Backup log files."""
    print("Backing up logs...")
    
    logs_dir = Path("logs")
    if logs_dir.exists() and any(logs_dir.iterdir()):
        try:
            backup_logs_dir = backup_dir / "logs"
            shutil.copytree(logs_dir, backup_logs_dir)
            file_count = len(list(backup_logs_dir.rglob("*")))
            print(f"✓ Logs backed up ({file_count} files)")
            return True
        except Exception as e:
            print(f"✗ Logs backup failed: {e}")
            return False
    else:
        print("- No logs to backup")
        return True

def create_backup_info(backup_dir):
    """Create backup information file."""
    info_file = backup_dir / "backup_info.txt"
    
    with open(info_file, 'w') as f:
        f.write(f"Glial Neuron Network Modelling Pipeline Backup\n")
        f.write(f"=" * 50 + "\n")
        f.write(f"Backup Date: {datetime.now().isoformat()}\n")
        f.write(f"Backup Directory: {backup_dir}\n")
        f.write(f"Python Version: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n")
        f.write(f"\nBackup Contents:\n")
        
        for item in backup_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(backup_dir)
                file_size = item.stat().st_size
                f.write(f"  {relative_path} ({file_size} bytes)\n")
    
    print(f"✓ Backup info created at {info_file}")

def list_backups():
    """List all available backups."""
    backups_dir = Path("backups")
    if not backups_dir.exists():
        print("No backups directory found")
        return
    
    backups = sorted([d for d in backups_dir.iterdir() if d.is_dir()])
    
    if not backups:
        print("No backups found")
        return
    
    print(f"\nAvailable backups ({len(backups)}):")
    print("-" * 40)
    
    for backup in backups:
        info_file = backup / "backup_info.txt"
        if info_file.exists():
            with open(info_file) as f:
                lines = f.readlines()
                backup_date = next((line.split(": ", 1)[1].strip() for line in lines if line.startswith("Backup Date:")), "Unknown")
        else:
            backup_date = "Unknown"
        
        backup_size = sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())
        backup_size_mb = backup_size / (1024 * 1024)
        
        print(f"  {backup.name}")
        print(f"    Date: {backup_date}")
        print(f"    Size: {backup_size_mb:.1f} MB")
        print()

def main():
    """Main backup function."""
    parser = argparse.ArgumentParser(description="Backup Glial Neuron Network Modelling Pipeline data")
    parser.add_argument("--no-raw", action="store_true", help="Skip raw data backup")
    parser.add_argument("--no-processed", action="store_true", help="Skip processed data backup")
    parser.add_argument("--no-figures", action="store_true", help="Skip figures backup")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--database-only", action="store_true", help="Backup only the database")
    
    args = parser.parse_args()
    
    if args.list:
        list_backups()
        return 0
    
    print("=" * 60)
    print("Glial Neuron Network Modelling Pipeline - Data Backup")
    print("=" * 60)
    
    # Create backup directory
    backup_dir = create_backup_directory()
    print(f"Creating backup in: {backup_dir}")
    
    success = True
    
    # Always backup database
    if not backup_database(backup_dir):
        success = False
    
    if not args.database_only:
        # Backup data files
        if not backup_data_files(backup_dir, 
                                include_raw=not args.no_raw,
                                include_processed=not args.no_processed,
                                include_figures=not args.no_figures):
            success = False
        
        # Backup configuration
        if not backup_configuration(backup_dir):
            success = False
        
        # Backup logs
        if not backup_logs(backup_dir):
            success = False
    
    # Create backup info
    create_backup_info(backup_dir)
    
    # Calculate total backup size
    total_size = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ BACKUP COMPLETED SUCCESSFULLY!")
        print(f"Backup location: {backup_dir}")
        print(f"Total size: {total_size_mb:.1f} MB")
    else:
        print("✗ BACKUP COMPLETED WITH ERRORS!")
        print("Please check the errors above.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
