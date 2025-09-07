"""
Suite2p Multi-Channel Import GUI - Interface for importing Suite2p datasets with dual channels.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data_processing.importers import Suite2pDatasetDetector, NPYImporter
from src.database.operations import DatasetOperations, DatasetRelationshipOperations
from src.utils.folder_manager import DatasetFolderManager


class Suite2pImportGUI:
    """GUI for Suite2p multi-channel data import."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Suite2p Multi-Channel Import")
        self.window.geometry("800x700")
        self.window.configure(bg='#f0f0f0')
        
        # Make window modal if parent exists
        if parent:
            self.window.transient(parent)
            self.window.grab_set()
        
        # Initialize components
        self.detector = Suite2pDatasetDetector()
        self.npy_importer = NPYImporter()
        self.folder_manager = DatasetFolderManager()
        
        # Variables
        self.data_folder_path = tk.StringVar()
        self.base_dataset_name = tk.StringVar()
        self.description_text = None
        
        # Scan results
        self.scan_results = {}
        self.selected_files = {}  # channel_name -> file_path
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_frame = ttk.Frame(self.window)
        title_frame.pack(pady=10, padx=20, fill="x")
        
        title_label = ttk.Label(
            title_frame,
            text="Suite2p Multi-Channel Import",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Import Suite2p datasets with dual channel support",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Data folder selection frame
        folder_frame = ttk.LabelFrame(self.window, text="Data Folder Selection", padding=10)
        folder_frame.pack(pady=10, padx=20, fill="x")
        
        # Folder path display and browse button
        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill="x", pady=5)
        
        ttk.Label(path_frame, text="DATA Folder:").pack(side="left")
        
        path_entry = ttk.Entry(
            path_frame, 
            textvariable=self.data_folder_path,
            width=50,
            state="readonly"
        )
        path_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        
        browse_btn = ttk.Button(
            path_frame,
            text="Browse",
            command=self.browse_data_folder,
            width=10
        )
        browse_btn.pack(side="right")
        
        # Scan button
        scan_btn = ttk.Button(
            folder_frame,
            text="Scan Folder Structure",
            command=self.scan_folder,
            width=20
        )
        scan_btn.pack(pady=5)
        
        # Channel detection results frame
        self.channels_frame = ttk.LabelFrame(self.window, text="Detected Channels", padding=10)
        self.channels_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Initially show message
        self.channels_info_label = ttk.Label(
            self.channels_frame,
            text="Select a DATA folder and click 'Scan Folder Structure' to detect channels",
            font=("Arial", 10),
            foreground="gray"
        )
        self.channels_info_label.pack(expand=True)
        
        # Import configuration frame
        config_frame = ttk.LabelFrame(self.window, text="Import Configuration", padding=10)
        config_frame.pack(pady=10, padx=20, fill="x")
        
        # Dataset name
        name_frame = ttk.Frame(config_frame)
        name_frame.pack(fill="x", pady=5)
        
        ttk.Label(name_frame, text="Base Dataset Name:").pack(side="left")
        name_entry = ttk.Entry(
            name_frame,
            textvariable=self.base_dataset_name,
            width=40
        )
        name_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
        
        # Description
        desc_frame = ttk.Frame(config_frame)
        desc_frame.pack(fill="x", pady=5)
        
        ttk.Label(desc_frame, text="Description:").pack(anchor="w")
        self.description_text = tk.Text(desc_frame, height=3, width=60)
        self.description_text.pack(fill="x", pady=(5, 0))
        
        # Action buttons frame
        actions_frame = ttk.Frame(self.window)
        actions_frame.pack(pady=10, padx=20, fill="x")
        
        # Import button
        self.import_btn = ttk.Button(
            actions_frame,
            text="Import Datasets",
            command=self.import_datasets,
            width=20,
            state="disabled"
        )
        self.import_btn.pack(side="left")
        
        # Close button
        close_btn = ttk.Button(
            actions_frame,
            text="Close",
            command=self.close_window,
            width=15
        )
        close_btn.pack(side="right")
        
        # Progress frame (initially hidden)
        self.progress_frame = ttk.Frame(self.window)
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(pady=5)
    
    def browse_data_folder(self):
        """Open dialog to browse for DATA folder."""
        folder_path = filedialog.askdirectory(
            title="Select Suite2p DATA Folder",
            initialdir=os.path.expanduser("~")
        )
        
        if folder_path:
            self.data_folder_path.set(folder_path)
            # Clear previous results
            self.scan_results = {}
            self.selected_files = {}
            self.update_channels_display()
    
    def scan_folder(self):
        """Scan the selected folder for Suite2p structure."""
        folder_path = self.data_folder_path.get()
        
        if not folder_path:
            messagebox.showwarning("No Folder", "Please select a DATA folder first.")
            return
        
        if not os.path.exists(folder_path):
            messagebox.showerror("Invalid Path", "Selected folder does not exist.")
            return
        
        # Perform scan
        self.scan_results = self.detector.scan_data_folder(folder_path)
        
        if not self.scan_results['success']:
            messagebox.showerror("Scan Failed", self.scan_results['message'])
            return
        
        # Update display
        self.update_channels_display()
        
        # Auto-generate base dataset name from folder
        folder_name = Path(folder_path).parent.name  # Get parent folder name
        if not self.base_dataset_name.get():
            self.base_dataset_name.set(folder_name)
    
    def update_channels_display(self):
        """Update the channels display based on scan results."""
        # Clear existing widgets
        for widget in self.channels_frame.winfo_children():
            widget.destroy()
        
        if not self.scan_results or not self.scan_results.get('channels'):
            self.channels_info_label = ttk.Label(
                self.channels_frame,
                text="No channels detected. Please scan a valid Suite2p DATA folder.",
                font=("Arial", 10),
                foreground="red"
            )
            self.channels_info_label.pack(expand=True)
            self.import_btn.config(state="disabled")
            return
        
        channels = self.scan_results['channels']
        
        # Create channel selection widgets
        for i, (channel_name, channel_info) in enumerate(channels.items()):
            # Channel frame
            channel_frame = ttk.LabelFrame(
                self.channels_frame, 
                text=f"{channel_name}", 
                padding=10
            )
            channel_frame.pack(fill="x", pady=5)
            
            if 'error' in channel_info:
                # Show error
                error_label = ttk.Label(
                    channel_frame,
                    text=f"Error: {channel_info['error']}",
                    foreground="red"
                )
                error_label.pack()
                continue
            
            if 'warning' in channel_info:
                # Show warning
                warning_label = ttk.Label(
                    channel_frame,
                    text=f"Warning: {channel_info['warning']}",
                    foreground="orange"
                )
                warning_label.pack()
                continue
            
            # Show path
            path_label = ttk.Label(
                channel_frame,
                text=f"Path: {channel_info['path']}",
                font=("Courier", 8)
            )
            path_label.pack(anchor="w")
            
            # File selection
            if channel_info['npy_files']:
                file_frame = ttk.Frame(channel_frame)
                file_frame.pack(fill="x", pady=5)
                
                ttk.Label(file_frame, text="Select .npy file:").pack(side="left")
                
                file_var = tk.StringVar()
                file_combo = ttk.Combobox(
                    file_frame,
                    textvariable=file_var,
                    values=channel_info['npy_files'],
                    state="readonly",
                    width=20
                )
                file_combo.pack(side="left", padx=(10, 5))
                
                # Set default selection (prefer F_spikes.npy, then F.npy, then first file)
                default_file = None
                if "F_spikes.npy" in channel_info['npy_files']:
                    default_file = "F_spikes.npy"
                elif "F.npy" in channel_info['npy_files']:
                    default_file = "F.npy"
                else:
                    default_file = channel_info['npy_files'][0]
                
                file_var.set(default_file)
                
                # Preview button
                preview_btn = ttk.Button(
                    file_frame,
                    text="Preview",
                    command=lambda cn=channel_name, fv=file_var, ci=channel_info: self.preview_file(cn, fv, ci),
                    width=10
                )
                preview_btn.pack(side="left", padx=5)
                
                # Store file selection variable
                setattr(self, f"{channel_name}_file_var", file_var)
        
        # Enable import button if we have at least one valid channel
        valid_channels = [ch for ch in channels.values() if 'npy_files' in ch and ch['npy_files']]
        if valid_channels:
            self.import_btn.config(state="normal")
        else:
            self.import_btn.config(state="disabled")
    
    def preview_file(self, channel_name: str, file_var: tk.StringVar, channel_info: Dict[str, Any]):
        """Preview selected .npy file."""
        selected_file = file_var.get()
        if not selected_file:
            return
        
        file_path = os.path.join(channel_info['path'], selected_file)
        
        try:
            # Import file for preview
            result = self.npy_importer.import_file(file_path)
            
            if result['success']:
                stats = result['statistics']
                preview_text = f"""File: {selected_file}
Channel: {channel_name}
Shape: {stats['shape']} (cells × frames)
Data Type: {stats['dtype']}
Memory: {stats['memory_usage_mb']:.2f} MB
Value Range: {stats['min_value']:.3f} to {stats['max_value']:.3f}
Mean: {stats['mean_value']:.3f}, Std: {stats['std_value']:.3f}
Has NaN: {stats['has_nan']}, Has Inf: {stats['has_inf']}"""
                
                messagebox.showinfo(f"Preview - {channel_name}", preview_text)
            else:
                messagebox.showerror("Preview Error", f"Failed to preview file:\n{result['message']}")
                
        except Exception as e:
            messagebox.showerror("Preview Error", f"Error previewing file:\n{str(e)}")
    
    def import_datasets(self):
        """Import the selected datasets."""
        base_name = self.base_dataset_name.get().strip()
        if not base_name:
            messagebox.showwarning("No Name", "Please enter a base dataset name.")
            return
        
        if not self.scan_results or not self.scan_results.get('channels'):
            messagebox.showerror("No Data", "Please scan a folder first.")
            return
        
        # Collect selected files
        selected_files = {}
        channels = self.scan_results['channels']
        
        for channel_name, channel_info in channels.items():
            if 'npy_files' in channel_info and channel_info['npy_files']:
                file_var = getattr(self, f"{channel_name}_file_var", None)
                if file_var:
                    selected_file = file_var.get()
                    if selected_file:
                        file_path = os.path.join(channel_info['path'], selected_file)
                        selected_files[channel_name] = file_path
        
        if not selected_files:
            messagebox.showerror("No Files", "No files selected for import.")
            return
        
        # Validate file compatibility if multiple files
        if len(selected_files) > 1:
            validation = self.detector.validate_selected_files(selected_files)
            if not validation['valid']:
                messagebox.showerror("Validation Error", validation['message'])
                return
            
            if validation['warnings']:
                warning_text = "Warnings found:\n\n" + "\n".join(validation['warnings'])
                warning_text += "\n\nDo you want to continue with the import?"
                
                if not messagebox.askyesno("Import Warnings", warning_text):
                    return
        
        # Start import process
        self.perform_import(selected_files, base_name)
    
    def perform_import(self, selected_files: Dict[str, str], base_name: str):
        """Perform the actual import process."""
        # Show progress
        self.progress_frame.pack(pady=10, padx=20, fill="x")
        self.progress_label.config(text="Starting import...")
        self.progress_bar['value'] = 0
        self.window.update()
        
        description = self.description_text.get(1.0, tk.END).strip()
        imported_datasets = []
        pair_id = str(uuid.uuid4())  # Unique identifier for this channel pair
        
        try:
            total_files = len(selected_files)
            
            for i, (channel_name, file_path) in enumerate(selected_files.items()):
                self.progress_label.config(text=f"Importing {channel_name}...")
                self.progress_bar['value'] = (i / total_files) * 50  # First 50% for import
                self.window.update()
                
                # Determine channel suffix
                if "ChanA" in channel_name:
                    channel_suffix = "ChanA"
                elif "ChanB" in channel_name:
                    channel_suffix = "ChanB"
                else:
                    channel_suffix = channel_name.replace("SUPPORT_", "")
                
                dataset_name = f"{base_name}_{channel_suffix}"
                
                # Import the file
                import_result = self.npy_importer.import_file(file_path)
                
                if not import_result['success']:
                    messagebox.showerror(
                        "Import Error",
                        f"Failed to import {channel_name}:\n{import_result['message']}"
                    )
                    continue
                
                # Create dataset in database (will be updated with final file path later)
                dataset_id = DatasetOperations.create_dataset(
                    name=dataset_name,
                    file_path=file_path,  # Temporary - will be updated to Raster_with_labels.csv
                    file_format='csv',  # Set to csv for processing pipeline compatibility
                    description=description,
                    metadata=import_result['metadata']
                )
                
                # Create dataset folder structure
                dataset_folder = self.folder_manager.create_dataset_folder(
                    dataset_id,
                    dataset_name,
                    use_clean_names=True
                )
                
                # Save processed files in raw directory (preserve original data)
                base_filename = Path(file_path).stem
                raw_dir = self.folder_manager.get_raw_data_path(dataset_folder)
                
                saved_files = self.npy_importer.save_processed_files(
                    import_result, raw_dir, base_filename
                )
                
                # Generate standardized Raster files in processed/matrices for compatibility
                processed_matrices_dir = self.folder_manager.get_processed_data_path(dataset_folder, "matrices")
                raster_files = self.npy_importer.generate_raster_matrix_files(
                    import_result, processed_matrices_dir
                )
                
                # Update dataset to point to standardized Raster_with_labels.csv for compatibility
                if 'raster_with_labels_csv' in raster_files:
                    DatasetOperations.update_dataset(
                        dataset_id, 
                        file_path=raster_files['raster_with_labels_csv'],
                        file_format='csv'  # Set format to csv for processing compatibility
                    )
                
                imported_datasets.append({
                    'dataset_id': dataset_id,
                    'channel_name': channel_name,
                    'channel_suffix': channel_suffix,
                    'dataset_name': dataset_name
                })
            
            # Link datasets if we have multiple channels
            if len(imported_datasets) > 1:
                self.progress_label.config(text="Linking channel datasets...")
                self.progress_bar['value'] = 75
                self.window.update()
                
                # Link all combinations (for now, assume pairs)
                for i in range(len(imported_datasets)):
                    for j in range(i + 1, len(imported_datasets)):
                        dataset_a = imported_datasets[i]
                        dataset_b = imported_datasets[j]
                        
                        DatasetRelationshipOperations.link_channel_datasets(
                            dataset_a['dataset_id'],
                            dataset_b['dataset_id'],
                            pair_id,
                            metadata={
                                'import_session': pair_id,
                                'source_data_folder': self.scan_results['data_folder'],
                                'base_name': base_name
                            }
                        )
            
            self.progress_label.config(text="Import completed!")
            self.progress_bar['value'] = 100
            self.window.update()
            
            # Show success message
            success_text = f"Successfully imported {len(imported_datasets)} dataset(s):\n\n"
            for dataset in imported_datasets:
                success_text += f"• {dataset['dataset_name']}\n"
            
            if len(imported_datasets) > 1:
                success_text += f"\nDatasets have been linked as channel pairs."
            
            messagebox.showinfo("Import Successful", success_text)
            
            # Clear form
            self.data_folder_path.set("")
            self.base_dataset_name.set("")
            self.description_text.delete(1.0, tk.END)
            self.scan_results = {}
            self.selected_files = {}
            self.update_channels_display()
            
        except Exception as e:
            messagebox.showerror("Import Error", f"An error occurred during import:\n{str(e)}")
        
        finally:
            # Hide progress
            self.progress_frame.pack_forget()
    
    def close_window(self):
        """Close the window."""
        if self.parent:
            self.window.grab_release()
        self.window.destroy()
    
    def run(self):
        """Run the GUI (if standalone)."""
        if not self.parent:
            self.window.mainloop()


if __name__ == "__main__":
    # Test the GUI
    app = Suite2pImportGUI()
    app.run()
