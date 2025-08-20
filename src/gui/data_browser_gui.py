"""
Data Browser GUI - Interface for browsing and managing datasets.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
from datetime import datetime
from typing import Optional, List
import subprocess
import platform

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, ProcessingJobOperations, FigureOperations, ProcessedDataOperations
from src.database.models import Dataset
from src.utils.folder_manager import DatasetFolderManager


class DataBrowserGUI:
    """GUI for browsing and managing datasets."""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Data Browser")
        self.window.geometry("1200x800")
        self.window.configure(bg='#f0f0f0')
        
        self.selected_dataset = None
        self.selected_folder_path = None
        self.datasets = []
        self.filtered_datasets = []
        self.folder_manager = DatasetFolderManager()
        
        self.setup_ui()
        self.load_datasets()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = ttk.Label(self.window, text="Data Browser", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Main container with paned window
        main_paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left panel - Dataset list
        self.create_dataset_list_panel(main_paned)
        
        # Right panel - Dataset details
        self.create_dataset_details_panel(main_paned)
    
    def create_dataset_list_panel(self, parent):
        """Create the left panel with dataset list and controls."""
        left_frame = ttk.Frame(parent)
        parent.add(left_frame, weight=1)
        
        # Search and filter frame
        search_frame = ttk.LabelFrame(left_frame, text="Search & Filter", padding=10)
        search_frame.pack(fill="x", padx=5, pady=5)
        
        # Search entry
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky="w", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Format filter
        ttk.Label(search_frame, text="Format:").grid(row=1, column=0, sticky="w", padx=5)
        self.format_filter_var = tk.StringVar()
        self.format_filter_var.trace('w', self.on_filter_change)
        format_combo = ttk.Combobox(search_frame, textvariable=self.format_filter_var,
                                   values=["All", "csv", "xlsx", "json", "txt", "h5"], 
                                   state="readonly", width=22)
        format_combo.grid(row=1, column=1, padx=5, pady=2)
        format_combo.set("All")
        
        # Sort options
        ttk.Label(search_frame, text="Sort by:").grid(row=2, column=0, sticky="w", padx=5)
        self.sort_var = tk.StringVar(value="import_date")
        self.sort_var.trace('w', self.on_sort_change)
        sort_combo = ttk.Combobox(search_frame, textvariable=self.sort_var,
                                 values=["name", "import_date", "file_size", "file_format"],
                                 state="readonly", width=22)
        sort_combo.grid(row=2, column=1, padx=5, pady=2)
        
        # Dataset list frame
        list_frame = ttk.LabelFrame(left_frame, text="Dataset Folders", padding=5)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Dataset folder treeview
        columns = ("type", "size", "date")
        self.dataset_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=20)
        
        # Configure columns
        self.dataset_tree.heading("#0", text="Dataset / Folder")
        self.dataset_tree.heading("type", text="Type")
        self.dataset_tree.heading("size", text="Size")
        self.dataset_tree.heading("date", text="Date")
        
        self.dataset_tree.column("#0", width=250)
        self.dataset_tree.column("type", width=100)
        self.dataset_tree.column("size", width=100)
        self.dataset_tree.column("date", width=120)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.dataset_tree.yview)
        self.dataset_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.dataset_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")
        
        # Bind selection event
        self.dataset_tree.bind("<<TreeviewSelect>>", self.on_dataset_select)
        
        # Action buttons frame
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(action_frame, text="Refresh", command=self.load_datasets).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Reload Datasets", command=self.reload_datasets).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Open File", command=self.open_dataset_file).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Edit", command=self.edit_dataset).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Delete", command=self.delete_dataset).pack(side="left", padx=2)
    
    def create_dataset_details_panel(self, parent):
        """Create the right panel with dataset details."""
        right_frame = ttk.Frame(parent)
        parent.add(right_frame, weight=2)
        
        # Create notebook for different detail views
        self.details_notebook = ttk.Notebook(right_frame)
        self.details_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Basic info tab
        self.create_basic_info_tab()
        
        # Processing history tab
        self.create_processing_history_tab()
        
        # Processed data tab
        self.create_processed_data_tab()
        
        # Figures tab
        self.create_figures_tab()
        
        # Metadata tab
        self.create_metadata_tab()
    
    def create_basic_info_tab(self):
        """Create the basic information tab."""
        info_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(info_frame, text="Basic Info")
        
        # Dataset info display
        info_container = ttk.LabelFrame(info_frame, text="Dataset Information", padding=10)
        info_container.pack(fill="x", padx=10, pady=5)
        
        # Create info labels
        self.info_labels = {}
        info_fields = [
            ("ID:", "id"),
            ("Name:", "name"),
            ("File Path:", "file_path"),
            ("File Format:", "file_format"),
            ("File Size:", "file_size"),
            ("Import Date:", "import_date"),
            ("Description:", "description")
        ]
        
        for i, (label_text, field_name) in enumerate(info_fields):
            ttk.Label(info_container, text=label_text, font=("Arial", 9, "bold")).grid(
                row=i, column=0, sticky="nw", padx=5, pady=2)
            self.info_labels[field_name] = ttk.Label(info_container, text="", wraplength=400)
            self.info_labels[field_name].grid(row=i, column=1, sticky="nw", padx=10, pady=2)
        
        # File operations frame
        file_ops_frame = ttk.LabelFrame(info_frame, text="File Operations", padding=10)
        file_ops_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(file_ops_frame, text="Open File Location", 
                  command=self.open_file_location).pack(side="left", padx=5)
        ttk.Button(file_ops_frame, text="Copy File Path", 
                  command=self.copy_file_path).pack(side="left", padx=5)
        ttk.Button(file_ops_frame, text="Preview Data", 
                  command=self.preview_data).pack(side="left", padx=5)
        
        # Statistics frame (placeholder for future data preview)
        stats_frame = ttk.LabelFrame(info_frame, text="Quick Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True)
        stats_scrollbar.pack(side="right", fill="y")
    
    def create_processing_history_tab(self):
        """Create the processing history tab."""
        history_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(history_frame, text="Processing History")
        
        # Jobs list
        jobs_frame = ttk.LabelFrame(history_frame, text="Processing Jobs", padding=5)
        jobs_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Jobs treeview
        job_columns = ("job_name", "job_type", "status", "start_time", "progress")
        self.jobs_tree = ttk.Treeview(jobs_frame, columns=job_columns, show="headings", height=15)
        
        # Configure job columns
        self.jobs_tree.heading("job_name", text="Job Name")
        self.jobs_tree.heading("job_type", text="Type")
        self.jobs_tree.heading("status", text="Status")
        self.jobs_tree.heading("start_time", text="Start Time")
        self.jobs_tree.heading("progress", text="Progress")
        
        self.jobs_tree.column("job_name", width=150)
        self.jobs_tree.column("job_type", width=120)
        self.jobs_tree.column("status", width=80)
        self.jobs_tree.column("start_time", width=130)
        self.jobs_tree.column("progress", width=80)
        
        # Jobs scrollbar
        jobs_scrollbar = ttk.Scrollbar(jobs_frame, orient="vertical", command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=jobs_scrollbar.set)
        
        self.jobs_tree.pack(side="left", fill="both", expand=True)
        jobs_scrollbar.pack(side="right", fill="y")
        
        # Job actions frame
        job_actions_frame = ttk.Frame(history_frame)
        job_actions_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(job_actions_frame, text="View Job Details", 
                  command=self.view_job_details).pack(side="left", padx=5)
        ttk.Button(job_actions_frame, text="Open Output File", 
                  command=self.open_job_output).pack(side="left", padx=5)
        ttk.Button(job_actions_frame, text="Rerun Job", 
                  command=self.rerun_job).pack(side="left", padx=5)
    
    def create_processed_data_tab(self):
        """Create the processed data tab."""
        processed_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(processed_frame, text="Processed Data")
        
        # Processed data list
        data_frame = ttk.LabelFrame(processed_frame, text="Processed Data", padding=5)
        data_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Processed data treeview
        data_columns = ("data_name", "data_type", "file_size", "created_at")
        self.processed_data_tree = ttk.Treeview(data_frame, columns=data_columns, show="headings", height=15)
        
        # Configure processed data columns
        self.processed_data_tree.heading("data_name", text="Data Name")
        self.processed_data_tree.heading("data_type", text="Type")
        self.processed_data_tree.heading("file_size", text="Size")
        self.processed_data_tree.heading("created_at", text="Created")
        
        self.processed_data_tree.column("data_name", width=200)
        self.processed_data_tree.column("data_type", width=100)
        self.processed_data_tree.column("file_size", width=80)
        self.processed_data_tree.column("created_at", width=130)
        
        # Processed data scrollbar
        data_scrollbar = ttk.Scrollbar(data_frame, orient="vertical", command=self.processed_data_tree.yview)
        self.processed_data_tree.configure(yscrollcommand=data_scrollbar.set)
        
        self.processed_data_tree.pack(side="left", fill="both", expand=True)
        data_scrollbar.pack(side="right", fill="y")
        
        # Processed data actions frame
        data_actions_frame = ttk.Frame(processed_frame)
        data_actions_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(data_actions_frame, text="Open File Location", 
                  command=self.open_processed_data_location).pack(side="left", padx=5)
        ttk.Button(data_actions_frame, text="View Data Info", 
                  command=self.view_processed_data_info).pack(side="left", padx=5)
        ttk.Button(data_actions_frame, text="Delete Processed Data", 
                  command=self.delete_processed_data).pack(side="left", padx=5)
    
    def create_figures_tab(self):
        """Create the figures tab."""
        figures_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(figures_frame, text="Generated Figures")
        
        # Figures list
        figs_frame = ttk.LabelFrame(figures_frame, text="Figures", padding=5)
        figs_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Figures treeview
        fig_columns = ("figure_name", "figure_type", "creation_date", "description")
        self.figures_tree = ttk.Treeview(figs_frame, columns=fig_columns, show="headings", height=15)
        
        # Configure figure columns
        self.figures_tree.heading("figure_name", text="Figure Name")
        self.figures_tree.heading("figure_type", text="Type")
        self.figures_tree.heading("creation_date", text="Created")
        self.figures_tree.heading("description", text="Description")
        
        self.figures_tree.column("figure_name", width=150)
        self.figures_tree.column("figure_type", width=80)
        self.figures_tree.column("creation_date", width=130)
        self.figures_tree.column("description", width=200)
        
        # Figures scrollbar
        figs_scrollbar = ttk.Scrollbar(figs_frame, orient="vertical", command=self.figures_tree.yview)
        self.figures_tree.configure(yscrollcommand=figs_scrollbar.set)
        
        self.figures_tree.pack(side="left", fill="both", expand=True)
        figs_scrollbar.pack(side="right", fill="y")
        
        # Figure actions frame
        fig_actions_frame = ttk.Frame(figures_frame)
        fig_actions_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(fig_actions_frame, text="Open Figure", 
                  command=self.open_figure).pack(side="left", padx=5)
        ttk.Button(fig_actions_frame, text="Copy Figure Path", 
                  command=self.copy_figure_path).pack(side="left", padx=5)
        ttk.Button(fig_actions_frame, text="Export Figure", 
                  command=self.export_figure).pack(side="left", padx=5)
    
    def create_metadata_tab(self):
        """Create the metadata tab."""
        metadata_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(metadata_frame, text="Metadata")
        
        # Metadata display
        meta_frame = ttk.LabelFrame(metadata_frame, text="Dataset Metadata", padding=10)
        meta_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.metadata_text = tk.Text(meta_frame, wrap=tk.WORD)
        meta_scrollbar = ttk.Scrollbar(meta_frame, orient="vertical", command=self.metadata_text.yview)
        self.metadata_text.configure(yscrollcommand=meta_scrollbar.set)
        
        self.metadata_text.pack(side="left", fill="both", expand=True)
        meta_scrollbar.pack(side="right", fill="y")
        
        # Metadata actions
        meta_actions_frame = ttk.Frame(metadata_frame)
        meta_actions_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(meta_actions_frame, text="Edit Metadata", 
                  command=self.edit_metadata).pack(side="left", padx=5)
        ttk.Button(meta_actions_frame, text="Export Metadata", 
                  command=self.export_metadata).pack(side="left", padx=5)
    
    def load_datasets(self):
        """Load all datasets from database."""
        try:
            self.datasets = DatasetOperations.list_datasets()
            self.apply_filters_and_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load datasets: {str(e)}")
    
    def apply_filters_and_display(self):
        """Apply current filters and display datasets."""
        # Apply search filter
        search_term = self.search_var.get().lower()
        format_filter = self.format_filter_var.get()
        
        self.filtered_datasets = []
        for dataset in self.datasets:
            # Search filter
            if search_term and search_term not in dataset.name.lower() and search_term not in (dataset.description or "").lower():
                continue
            
            # Format filter
            if format_filter != "All" and dataset.file_format != format_filter:
                continue
            
            self.filtered_datasets.append(dataset)
        
        # Apply sorting
        sort_by = self.sort_var.get()
        reverse = sort_by in ["import_date", "file_size"]  # Newest/largest first
        
        if sort_by == "name":
            self.filtered_datasets.sort(key=lambda x: x.name.lower())
        elif sort_by == "import_date":
            self.filtered_datasets.sort(key=lambda x: x.import_date or datetime.min, reverse=reverse)
        elif sort_by == "file_size":
            self.filtered_datasets.sort(key=lambda x: x.file_size or 0, reverse=reverse)
        elif sort_by == "file_format":
            self.filtered_datasets.sort(key=lambda x: x.file_format or "")
        
        # Update display
        self.update_dataset_display()
    
    def update_dataset_display(self):
        """Update the dataset treeview display with folder structure."""
        # Clear existing items
        for item in self.dataset_tree.get_children():
            self.dataset_tree.delete(item)
        
        # Add filtered datasets as folder structure
        for dataset in self.filtered_datasets:
            # Get dataset folder path
            dataset_folder = self.folder_manager.get_dataset_folder(dataset.id, dataset.name)
            
            if not dataset_folder or not os.path.exists(dataset_folder):
                # Fallback: show dataset as file if no folder structure exists
                date_str = dataset.import_date.strftime("%Y-%m-%d %H:%M") if dataset.import_date else "Unknown"
                size_str = self._format_file_size(dataset.file_size)
                
                self.dataset_tree.insert("", "end", text=dataset.name,
                                       values=("Dataset (file)", size_str, date_str),
                                       tags=("dataset",))
                continue
            
            # Format date
            date_str = dataset.import_date.strftime("%Y-%m-%d %H:%M") if dataset.import_date else "Unknown"
            
            # Insert main dataset folder with clean display name
            dataset_item = self.dataset_tree.insert("", "end", text=dataset.name,
                                                   values=("Dataset Folder", "", date_str),
                                                   tags=("dataset_folder",))
            
            # Add subfolders
            self._add_subfolders(dataset_item, dataset_folder, dataset)
    
    def _add_subfolders(self, parent_item, folder_path, dataset):
        """Add subfolders to the dataset tree."""
        try:
            subfolders = ["raw", "processed", "figures"]
            
            for subfolder in subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if os.path.exists(subfolder_path):
                    # Count files in subfolder
                    file_count = self._count_files_in_folder(subfolder_path)
                    count_str = f"{file_count} files" if file_count > 0 else "empty"
                    
                    subfolder_item = self.dataset_tree.insert(parent_item, "end", text=subfolder,
                                                            values=("Folder", count_str, ""),
                                                            tags=("subfolder",))
                    
                    # For processed folder, add type subfolders
                    if subfolder == "processed":
                        self._add_processed_subfolders(subfolder_item, subfolder_path)
        except Exception as e:
            print(f"Error adding subfolders: {e}")
    
    def _add_processed_subfolders(self, parent_item, processed_path):
        """Add processed data type subfolders."""
        try:
            type_folders = ["matrices", "pca", "vectors", "statistics"]
            
            for type_folder in type_folders:
                type_path = os.path.join(processed_path, type_folder)
                if os.path.exists(type_path):
                    file_count = self._count_files_in_folder(type_path)
                    count_str = f"{file_count} files" if file_count > 0 else "empty"
                    
                    self.dataset_tree.insert(parent_item, "end", text=type_folder,
                                           values=("Data Type", count_str, ""),
                                           tags=("data_type",))
        except Exception as e:
            print(f"Error adding processed subfolders: {e}")
    
    def _count_files_in_folder(self, folder_path):
        """Count files in a folder."""
        try:
            if not os.path.exists(folder_path):
                return 0
            return len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        except Exception:
            return 0
    
    def _format_file_size(self, file_size):
        """Format file size for display."""
        if not file_size:
            return "Unknown"
        
        if file_size > 1024*1024:
            return f"{file_size / (1024*1024):.1f} MB"
        elif file_size > 1024:
            return f"{file_size / 1024:.1f} KB"
        else:
            return f"{file_size} B"
    
    def on_search_change(self, *args):
        """Handle search text change."""
        self.apply_filters_and_display()
    
    def on_filter_change(self, *args):
        """Handle filter change."""
        self.apply_filters_and_display()
    
    def on_sort_change(self, *args):
        """Handle sort change."""
        self.apply_filters_and_display()
    
    def on_dataset_select(self, event):
        """Handle dataset/folder selection."""
        selection = self.dataset_tree.selection()
        if selection:
            item_id = selection[0]
            item = self.dataset_tree.item(item_id)
            item_text = item['text']
            item_tags = item['tags']
            
            # Reset selection state
            self.selected_dataset = None
            self.selected_folder_path = None
            
            if 'dataset_folder' in item_tags:
                # Selected a dataset folder - find the dataset
                dataset_name = item_text  # This is the display name we set
                self.selected_dataset = next((d for d in self.filtered_datasets if d.name == dataset_name), None)
                if self.selected_dataset:
                    dataset_folder = self.folder_manager.get_dataset_folder(self.selected_dataset.id, self.selected_dataset.name)
                    self.selected_folder_path = dataset_folder
                    self.update_dataset_details()
            
            elif 'dataset' in item_tags:
                # Selected a dataset (file-based, no folder structure)
                self.selected_dataset = next((d for d in self.filtered_datasets if d.name == item_text), None)
                if self.selected_dataset:
                    self.update_dataset_details()
            
            elif 'subfolder' in item_tags or 'data_type' in item_tags:
                # Selected a subfolder - show folder contents
                folder_path = self._get_full_folder_path(item_id)
                self.selected_folder_path = folder_path
                
                # Also find the parent dataset
                parent_dataset = self._find_parent_dataset(item_id)
                self.selected_dataset = parent_dataset
                
                self.update_folder_contents_display()
    
    def _get_full_folder_path(self, item_id):
        """Get the full path for a selected folder item."""
        try:
            # Build path by walking up the tree
            path_parts = []
            current_item = item_id
            
            while current_item:
                item = self.dataset_tree.item(current_item)
                item_text = item['text']
                item_tags = item['tags']
                
                if 'dataset_folder' in item_tags:
                    # Found the dataset folder - get its actual path
                    dataset_name = item_text
                    dataset = next((d for d in self.filtered_datasets if d.name == dataset_name), None)
                    if dataset:
                        dataset_folder = self.folder_manager.get_dataset_folder(dataset.id, dataset.name)
                        if dataset_folder:
                            path_parts.reverse()
                            return os.path.join(dataset_folder, *path_parts)
                    break
                else:
                    path_parts.append(item_text)
                
                current_item = self.dataset_tree.parent(current_item)
            
            return None
        except Exception as e:
            print(f"Error getting folder path: {e}")
            return None
    
    def _find_parent_dataset(self, item_id):
        """Find the parent dataset for a folder item."""
        try:
            current_item = item_id
            
            while current_item:
                item = self.dataset_tree.item(current_item)
                item_tags = item['tags']
                
                if 'dataset_folder' in item_tags:
                    dataset_name = item['text']
                    return next((d for d in self.filtered_datasets if d.name == dataset_name), None)
                
                current_item = self.dataset_tree.parent(current_item)
            
            return None
        except Exception as e:
            print(f"Error finding parent dataset: {e}")
            return None
    
    def update_dataset_details(self):
        """Update the dataset details panel."""
        if not self.selected_dataset:
            return
        
        # Update basic info
        self.info_labels["id"].config(text=str(self.selected_dataset.id))
        self.info_labels["name"].config(text=self.selected_dataset.name)
        self.info_labels["file_path"].config(text=self.selected_dataset.file_path)
        self.info_labels["file_format"].config(text=self.selected_dataset.file_format or "Unknown")
        
        # Format file size
        if self.selected_dataset.file_size:
            if self.selected_dataset.file_size > 1024*1024:
                size_text = f"{self.selected_dataset.file_size / (1024*1024):.2f} MB ({self.selected_dataset.file_size:,} bytes)"
            elif self.selected_dataset.file_size > 1024:
                size_text = f"{self.selected_dataset.file_size / 1024:.2f} KB ({self.selected_dataset.file_size:,} bytes)"
            else:
                size_text = f"{self.selected_dataset.file_size} bytes"
        else:
            size_text = "Unknown"
        self.info_labels["file_size"].config(text=size_text)
        
        # Format date
        date_text = self.selected_dataset.import_date.strftime("%Y-%m-%d %H:%M:%S") if self.selected_dataset.import_date else "Unknown"
        self.info_labels["import_date"].config(text=date_text)
        
        self.info_labels["description"].config(text=self.selected_dataset.description or "No description")
        
        # Update processing history
        self.update_processing_history()
        
        # Update processed data
        self.update_processed_data_list()
        
        # Update figures
        self.update_figures_list()
        
        # Update metadata
        self.update_metadata_display()
        
        # Update statistics (placeholder)
        self.update_statistics()
    
    def update_folder_contents_display(self):
        """Update the display to show folder contents when a folder is selected."""
        if not self.selected_folder_path or not os.path.exists(self.selected_folder_path):
            return
        
        # Clear all tabs and create a folder contents tab
        for tab_id in self.details_notebook.tabs():
            self.details_notebook.forget(tab_id)
        
        # Create folder contents tab
        folder_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(folder_frame, text="Folder Contents")
        
        # Folder info
        info_frame = ttk.LabelFrame(folder_frame, text="Folder Information", padding=10)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        folder_name = os.path.basename(self.selected_folder_path)
        ttk.Label(info_frame, text=f"Folder: {folder_name}", font=("Arial", 12, "bold")).pack(anchor="w")
        ttk.Label(info_frame, text=f"Path: {self.selected_folder_path}").pack(anchor="w")
        
        # File list
        files_frame = ttk.LabelFrame(folder_frame, text="Files", padding=10)
        files_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for files
        file_columns = ("name", "size", "modified")
        file_tree = ttk.Treeview(files_frame, columns=file_columns, show="tree headings", height=15)
        
        # Configure columns
        file_tree.heading("#0", text="Type")
        file_tree.heading("name", text="File Name")
        file_tree.heading("size", text="Size")
        file_tree.heading("modified", text="Modified")
        
        file_tree.column("#0", width=80)
        file_tree.column("name", width=300)
        file_tree.column("size", width=100)
        file_tree.column("modified", width=150)
        
        # Add files to tree
        try:
            files = os.listdir(self.selected_folder_path)
            files.sort()
            
            for file_name in files:
                file_path = os.path.join(self.selected_folder_path, file_name)
                
                if os.path.isfile(file_path):
                    # Get file info
                    file_size = os.path.getsize(file_path)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Format size and date
                    size_str = self._format_file_size(file_size)
                    date_str = file_modified.strftime("%Y-%m-%d %H:%M")
                    
                    # Determine file type icon
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in ['.csv', '.tsv']:
                        file_type = "📊"
                    elif ext in ['.png', '.jpg', '.jpeg', '.svg']:
                        file_type = "🖼️"
                    elif ext in ['.npy', '.npz']:
                        file_type = "🔢"
                    elif ext in ['.json']:
                        file_type = "📝"
                    else:
                        file_type = "📄"
                    
                    file_tree.insert("", "end", text=file_type,
                                   values=(file_name, size_str, date_str))
        
        except Exception as e:
            error_label = ttk.Label(files_frame, text=f"Error reading folder: {str(e)}")
            error_label.pack()
            return
        
        # Add scrollbar
        file_scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=file_tree.yview)
        file_tree.configure(yscrollcommand=file_scrollbar.set)
        
        file_tree.pack(side="left", fill="both", expand=True)
        file_scrollbar.pack(side="right", fill="y")
        
        # Bind double-click to open file
        def on_file_double_click(event):
            selection = file_tree.selection()
            if selection:
                item = file_tree.item(selection[0])
                file_name = item['values'][0]
                file_path = os.path.join(self.selected_folder_path, file_name)
                self.open_file_external(file_path)
        
        file_tree.bind("<Double-1>", on_file_double_click)
        
        # Action buttons
        button_frame = ttk.Frame(folder_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(button_frame, text="Open Folder", 
                  command=lambda: self.open_file_external(self.selected_folder_path)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Refresh", 
                  command=self.update_folder_contents_display).pack(side="left", padx=5)
    
    def open_file_external(self, file_path):
        """Open a file or folder with the system default application."""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(file_path)
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def reload_datasets(self):
        """Show dialog to reload orphaned dataset folders."""
        try:
            # Scan for orphaned folders
            orphaned_folders = self._scan_orphaned_folders()
            
            if not orphaned_folders:
                messagebox.showinfo("No Orphaned Datasets", 
                                   "No dataset folders found that are not already in the database.")
                return
            
            # Show selection dialog
            self._show_reload_selection_dialog(orphaned_folders)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan for datasets: {str(e)}")
    
    def _scan_orphaned_folders(self):
        """Scan for dataset folders that don't have database entries."""
        orphaned = []
        datasets_dir = self.folder_manager.datasets_dir
        
        if not datasets_dir.exists():
            return orphaned
        
        # Get all existing dataset names from database
        existing_datasets = {d.name for d in self.datasets}
        
        # Scan all folders in datasets directory
        for folder_path in datasets_dir.iterdir():
            if not folder_path.is_dir():
                continue
                
            folder_name = folder_path.name
            
            # Try to extract dataset name from folder
            dataset_name = self._extract_dataset_name_from_folder(folder_name)
            
            if dataset_name and dataset_name not in existing_datasets:
                # This folder is orphaned - get its info
                folder_info = self._get_folder_info(folder_path, dataset_name)
                if folder_info:
                    orphaned.append(folder_info)
        
        return sorted(orphaned, key=lambda x: x['last_modified'], reverse=True)
    
    def _extract_dataset_name_from_folder(self, folder_name):
        """Extract dataset name from folder name (handles both old and new formats)."""
        # Check if it's legacy format (dataset_XXX_Name)
        if folder_name.startswith("dataset_") and "_" in folder_name[8:]:
            # Extract name after dataset_XXX_
            parts = folder_name.split("_", 2)
            if len(parts) >= 3 and parts[1].isdigit():
                return parts[2]  # Return the name part
        
        # Check if it's clean format (just the name)
        # Verify it's a valid dataset folder by checking for expected subfolders
        folder_path = self.folder_manager.datasets_dir / folder_name
        expected_subfolders = ['raw', 'processed', 'figures']
        has_expected_structure = any(
            (folder_path / subfolder).exists() 
            for subfolder in expected_subfolders
        )
        
        if has_expected_structure:
            return folder_name
        
        return None
    
    def _get_folder_info(self, folder_path, dataset_name):
        """Get information about a dataset folder."""
        try:
            # Get folder statistics
            total_size = self._get_folder_size(folder_path)
            last_modified = datetime.fromtimestamp(folder_path.stat().st_mtime)
            
            # Count contents
            raw_count = self._count_files_in_subfolder(folder_path, 'raw')
            processed_count = self._count_files_in_subfolder(folder_path, 'processed')
            figures_count = self._count_files_in_subfolder(folder_path, 'figures')
            
            # Determine folder type
            is_legacy = folder_path.name.startswith("dataset_")
            
            return {
                'folder_path': str(folder_path),
                'folder_name': folder_path.name,
                'dataset_name': dataset_name,
                'total_size': total_size,
                'last_modified': last_modified,
                'raw_files': raw_count,
                'processed_files': processed_count,
                'figures': figures_count,
                'is_legacy_format': is_legacy
            }
        except Exception as e:
            print(f"Error getting folder info for {folder_path}: {e}")
            return None
    
    def _get_folder_size(self, folder_path):
        """Calculate total size of folder and all subfolders."""
        total_size = 0
        try:
            for path in folder_path.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
        except Exception:
            pass
        return total_size
    
    def _count_files_in_subfolder(self, folder_path, subfolder_name):
        """Count files in a specific subfolder."""
        subfolder_path = folder_path / subfolder_name
        if not subfolder_path.exists():
            return 0
        
        try:
            return len([f for f in subfolder_path.rglob('*') if f.is_file()])
        except Exception:
            return 0
    
    def _show_reload_selection_dialog(self, orphaned_folders):
        """Show dialog to select which datasets to reload."""
        dialog = tk.Toplevel(self.window)
        dialog.title("Reload Datasets")
        dialog.geometry("800x500")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.window.winfo_rootx() + 50, self.window.winfo_rooty() + 50))
        
        # Title
        title_label = ttk.Label(dialog, text=f"Found {len(orphaned_folders)} dataset folder(s) to reload", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=10)
        
        # Instructions
        instructions = ttk.Label(dialog, 
                                text="Select the datasets you want to reload. All processed data and figures will be preserved.",
                                wraplength=750)
        instructions.pack(pady=5)
        
        # Create frame for treeview
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create treeview with checkboxes
        columns = ("select", "dataset_name", "size", "last_modified", "contents", "type")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        tree.heading("select", text="Select")
        tree.heading("dataset_name", text="Dataset Name")
        tree.heading("size", text="Size")
        tree.heading("last_modified", text="Last Modified")
        tree.heading("contents", text="Contents")
        tree.heading("type", text="Format")
        
        tree.column("select", width=80)
        tree.column("dataset_name", width=200)
        tree.column("size", width=100)
        tree.column("last_modified", width=120)
        tree.column("contents", width=150)
        tree.column("type", width=100)
        
        # Add data to tree
        item_data = {}  # Store folder info by item ID
        for folder_info in orphaned_folders:
            # Format size
            size_str = self._format_file_size(folder_info['total_size'])
            
            # Format date
            date_str = folder_info['last_modified'].strftime("%Y-%m-%d %H:%M")
            
            # Format contents
            contents = f"{folder_info['raw_files']} raw, {folder_info['processed_files']} proc, {folder_info['figures']} figs"
            
            # Format type
            type_str = "Legacy" if folder_info['is_legacy_format'] else "Clean"
            
            item_id = tree.insert("", "end",
                                values=("☐", folder_info['dataset_name'], size_str, date_str, contents, type_str))
            item_data[item_id] = folder_info
        
        # Track selected items
        selected_items = set()
        
        def toggle_selection(event):
            """Toggle item selection on click."""
            item = tree.selection()[0] if tree.selection() else None
            if item:
                if item in selected_items:
                    selected_items.remove(item)
                    tree.set(item, "select", "☐")
                else:
                    selected_items.add(item)
                    tree.set(item, "select", "☑")
        
        tree.bind("<Button-1>", toggle_selection)
        tree.bind("<space>", toggle_selection)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Selection buttons
        button_frame1 = ttk.Frame(dialog)
        button_frame1.pack(fill="x", padx=10, pady=5)
        
        def select_all():
            for item in tree.get_children():
                selected_items.add(item)
                tree.set(item, "select", "☑")
        
        def select_none():
            selected_items.clear()
            for item in tree.get_children():
                tree.set(item, "select", "☐")
        
        ttk.Button(button_frame1, text="Select All", command=select_all).pack(side="left", padx=5)
        ttk.Button(button_frame1, text="Select None", command=select_none).pack(side="left", padx=5)
        
        # Action buttons
        button_frame2 = ttk.Frame(dialog)
        button_frame2.pack(fill="x", padx=10, pady=10)
        
        def reload_selected():
            if not selected_items:
                messagebox.showwarning("No Selection", "Please select at least one dataset to reload.")
                return
            
            # Get selected folder info
            selected_folders = [item_data[item] for item in selected_items]
            
            dialog.destroy()
            self._process_reload_datasets(selected_folders)
        
        def cancel_reload():
            dialog.destroy()
        
        ttk.Button(button_frame2, text="Cancel", command=cancel_reload).pack(side="right", padx=5)
        ttk.Button(button_frame2, text=f"Reload Selected", command=reload_selected).pack(side="right", padx=5)
    
    def _process_reload_datasets(self, selected_folders):
        """Process the actual reloading of selected datasets."""
        try:
            successful_reloads = []
            failed_reloads = []
            conflicts = []
            
            for folder_info in selected_folders:
                result = self._reload_single_dataset(folder_info)
                
                if result['success']:
                    successful_reloads.append(result['dataset_name'])
                elif result['conflict']:
                    conflicts.append(result)
                else:
                    failed_reloads.append((result['dataset_name'], result['error']))
            
            # Handle conflicts if any
            if conflicts:
                self._handle_reload_conflicts(conflicts, successful_reloads, failed_reloads)
                return
            
            # Show results
            self._show_reload_results(successful_reloads, failed_reloads)
            
        except Exception as e:
            messagebox.showerror("Reload Error", f"An error occurred during reload: {str(e)}")
    
    def _reload_single_dataset(self, folder_info):
        """Reload a single dataset from folder information."""
        try:
            dataset_name = folder_info['dataset_name']
            folder_path = folder_info['folder_path']
            
            # Check for naming conflicts in database
            existing_dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if existing_dataset:
                return {
                    'success': False,
                    'conflict': True,
                    'dataset_name': dataset_name,
                    'folder_info': folder_info,
                    'existing_dataset': existing_dataset
                }
            
            # Recover metadata from folder
            metadata = self._recover_metadata_from_folder(folder_path)
            
            # Find original raw file for file_path and format detection
            raw_file_info = self._find_primary_raw_file(folder_path)
            
            # Create database entry
            dataset_id = DatasetOperations.create_dataset(
                name=dataset_name,
                file_path=raw_file_info['file_path'],
                file_format=raw_file_info['file_format'],
                description=f"Reloaded from folder on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                metadata=metadata
            )
            
            return {
                'success': True,
                'conflict': False,
                'dataset_name': dataset_name,
                'dataset_id': dataset_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'conflict': False,
                'dataset_name': folder_info['dataset_name'],
                'error': str(e)
            }
    
    def _recover_metadata_from_folder(self, folder_path):
        """Recover metadata from folder contents."""
        metadata = {
            'reloaded': True,
            'reload_date': datetime.now().isoformat(),
            'folder_structure': 'detected',
            'original_folder_path': folder_path
        }
        
        try:
            # Get folder creation time as proxy for original import
            folder_stat = os.stat(folder_path)
            metadata['estimated_original_import'] = datetime.fromtimestamp(folder_stat.st_ctime).isoformat()
            
            # Count contents
            raw_path = os.path.join(folder_path, 'raw')
            processed_path = os.path.join(folder_path, 'processed')
            figures_path = os.path.join(folder_path, 'figures')
            
            if os.path.exists(raw_path):
                raw_files = [f for f in os.listdir(raw_path) if os.path.isfile(os.path.join(raw_path, f))]
                metadata['raw_files'] = raw_files
                metadata['raw_file_count'] = len(raw_files)
            
            if os.path.exists(processed_path):
                processed_types = []
                for item in os.listdir(processed_path):
                    item_path = os.path.join(processed_path, item)
                    if os.path.isdir(item_path):
                        file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                        processed_types.append({'type': item, 'file_count': file_count})
                metadata['processed_data_types'] = processed_types
            
            if os.path.exists(figures_path):
                figure_files = [f for f in os.listdir(figures_path) if os.path.isfile(os.path.join(figures_path, f))]
                metadata['figure_files'] = figure_files
                metadata['figure_count'] = len(figure_files)
                
        except Exception as e:
            metadata['metadata_recovery_error'] = str(e)
        
        return metadata
    
    def _find_primary_raw_file(self, folder_path):
        """Find the primary raw file to use as the dataset's main file."""
        raw_path = os.path.join(folder_path, 'raw')
        
        if not os.path.exists(raw_path):
            return {
                'file_path': folder_path,  # Use folder as fallback
                'file_format': 'folder'
            }
        
        try:
            raw_files = [f for f in os.listdir(raw_path) if os.path.isfile(os.path.join(raw_path, f))]
            
            if not raw_files:
                return {
                    'file_path': raw_path,
                    'file_format': 'empty'
                }
            
            # Prefer CSV files, then other data files
            preferred_extensions = ['.csv', '.xlsx', '.json', '.tsv', '.txt']
            
            for ext in preferred_extensions:
                for file in raw_files:
                    if file.lower().endswith(ext):
                        return {
                            'file_path': os.path.join(raw_path, file),
                            'file_format': ext[1:]  # Remove the dot
                        }
            
            # If no preferred file found, use the first file
            first_file = raw_files[0]
            ext = os.path.splitext(first_file)[1]
            return {
                'file_path': os.path.join(raw_path, first_file),
                'file_format': ext[1:] if ext else 'unknown'
            }
            
        except Exception:
            return {
                'file_path': raw_path,
                'file_format': 'error'
            }
    
    def _handle_reload_conflicts(self, conflicts, successful_reloads, failed_reloads):
        """Handle naming conflicts during reload."""
        if not conflicts:
            self._show_reload_results(successful_reloads, failed_reloads)
            return
        
        # Show conflict resolution dialog
        conflict_dialog = tk.Toplevel(self.window)
        conflict_dialog.title("Resolve Naming Conflicts")
        conflict_dialog.geometry("600x400")
        conflict_dialog.transient(self.window)
        conflict_dialog.grab_set()
        
        # Center dialog
        conflict_dialog.geometry("+%d+%d" % (self.window.winfo_rootx() + 100, self.window.winfo_rooty() + 100))
        
        # Title
        title_label = ttk.Label(conflict_dialog, text="Naming Conflicts Found", font=("Arial", 12, "bold"))
        title_label.pack(pady=10)
        
        # Instructions
        instructions = ttk.Label(conflict_dialog, 
                                text="The following datasets already exist. Choose new names or skip:",
                                wraplength=550)
        instructions.pack(pady=5)
        
        # Scrollable frame for conflicts
        canvas = tk.Canvas(conflict_dialog)
        scrollbar = ttk.Scrollbar(conflict_dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Conflict resolution entries
        resolution_vars = {}
        
        for i, conflict in enumerate(conflicts):
            conflict_frame = ttk.LabelFrame(scrollable_frame, text=f"Conflict {i+1}", padding=10)
            conflict_frame.pack(fill="x", padx=10, pady=5)
            
            # Original name
            ttk.Label(conflict_frame, text=f"Original: {conflict['dataset_name']}", 
                     font=("Arial", 10, "bold")).pack(anchor="w")
            ttk.Label(conflict_frame, text=f"Conflicts with database ID: {conflict['existing_dataset'].id}").pack(anchor="w")
            
            # Resolution options
            resolution_var = tk.StringVar(value="skip")
            resolution_vars[i] = {
                'var': resolution_var,
                'conflict': conflict,
                'new_name_var': tk.StringVar(value=f"{conflict['dataset_name']}_reloaded")
            }
            
            ttk.Radiobutton(conflict_frame, text="Skip this dataset", 
                           variable=resolution_var, value="skip").pack(anchor="w")
            
            rename_frame = ttk.Frame(conflict_frame)
            rename_frame.pack(fill="x", pady=2)
            ttk.Radiobutton(rename_frame, text="Rename to:", 
                           variable=resolution_var, value="rename").pack(side="left")
            ttk.Entry(rename_frame, textvariable=resolution_vars[i]['new_name_var'], width=30).pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        # Action buttons
        button_frame = ttk.Frame(conflict_dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        def apply_resolutions():
            # Process each conflict based on user choice
            additional_successful = []
            additional_failed = []
            
            for i, resolution_info in resolution_vars.items():
                choice = resolution_info['var'].get()
                conflict = resolution_info['conflict']
                
                if choice == "rename":
                    new_name = resolution_info['new_name_var'].get().strip()
                    if new_name and new_name != conflict['dataset_name']:
                        # Update conflict info with new name
                        conflict['folder_info']['dataset_name'] = new_name
                        result = self._reload_single_dataset(conflict['folder_info'])
                        
                        if result['success']:
                            additional_successful.append(new_name)
                        else:
                            additional_failed.append((new_name, result.get('error', 'Unknown error')))
                    else:
                        additional_failed.append((conflict['dataset_name'], "Invalid new name"))
                # If "skip", do nothing
            
            conflict_dialog.destroy()
            
            # Combine results and show final summary
            all_successful = successful_reloads + additional_successful
            all_failed = failed_reloads + additional_failed
            self._show_reload_results(all_successful, all_failed)
        
        def cancel_conflicts():
            conflict_dialog.destroy()
            self._show_reload_results(successful_reloads, failed_reloads)
        
        ttk.Button(button_frame, text="Cancel", command=cancel_conflicts).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Apply", command=apply_resolutions).pack(side="right", padx=5)
    
    def _show_reload_results(self, successful_reloads, failed_reloads):
        """Show the results of the reload operation."""
        if successful_reloads:
            success_msg = f"Successfully reloaded {len(successful_reloads)} dataset(s):\n" + "\n".join(f"• {name}" for name in successful_reloads)
            
            if failed_reloads:
                failed_msg = f"\n\nFailed to reload {len(failed_reloads)} dataset(s):\n" + "\n".join(f"• {name}: {error}" for name, error in failed_reloads)
                messagebox.showwarning("Reload Complete with Errors", success_msg + failed_msg)
            else:
                messagebox.showinfo("Reload Complete", success_msg)
            
            # Refresh the dataset list to show reloaded datasets
            self.load_datasets()
        
        elif failed_reloads:
            failed_msg = f"Failed to reload {len(failed_reloads)} dataset(s):\n" + "\n".join(f"• {name}: {error}" for name, error in failed_reloads)
            messagebox.showerror("Reload Failed", failed_msg)
        
        else:
            messagebox.showinfo("No Action", "No datasets were reloaded.")
    
    def update_processing_history(self):
        """Update the processing history tab."""
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        if not self.selected_dataset:
            return
        
        try:
            jobs = ProcessingJobOperations.list_jobs_for_dataset(self.selected_dataset.id)
            
            for job in jobs:
                start_time = job.start_time.strftime("%Y-%m-%d %H:%M") if job.start_time else "Unknown"
                progress = f"{job.progress:.1f}%" if job.progress is not None else "N/A"
                
                self.jobs_tree.insert("", "end", values=(
                    job.job_name, job.job_type, job.status, start_time, progress
                ))
                
        except Exception as e:
            print(f"Error loading processing history: {e}")
    
    def update_processed_data_list(self):
        """Update the processed data list."""
        # Clear existing items
        for item in self.processed_data_tree.get_children():
            self.processed_data_tree.delete(item)
        
        if not self.selected_dataset:
            return
        
        try:
            processed_data = ProcessedDataOperations.list_processed_data_for_dataset(self.selected_dataset.id)
            
            for data in processed_data:
                # Format file size
                if data.file_size:
                    if data.file_size > 1024*1024:
                        size_str = f"{data.file_size / (1024*1024):.1f} MB"
                    elif data.file_size > 1024:
                        size_str = f"{data.file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{data.file_size} B"
                else:
                    size_str = "Unknown"
                
                # Format creation date
                created_str = data.created_at.strftime("%Y-%m-%d %H:%M") if data.created_at else "Unknown"
                
                self.processed_data_tree.insert("", "end", text=str(data.id),
                                               values=(data.data_name, data.data_type, size_str, created_str))
                
        except Exception as e:
            print(f"Error loading processed data: {e}")
    
    def update_figures_list(self):
        """Update the figures list."""
        # Clear existing items
        for item in self.figures_tree.get_children():
            self.figures_tree.delete(item)
        
        if not self.selected_dataset:
            return
        
        try:
            figures = FigureOperations.list_figures_for_dataset(self.selected_dataset.id)
            
            for figure in figures:
                creation_date = figure.creation_date.strftime("%Y-%m-%d %H:%M") if figure.creation_date else "Unknown"
                
                self.figures_tree.insert("", "end", values=(
                    figure.figure_name, figure.figure_type, creation_date, figure.description or ""
                ))
                
        except Exception as e:
            print(f"Error loading figures: {e}")
    
    def update_metadata_display(self):
        """Update the metadata display."""
        self.metadata_text.config(state=tk.NORMAL)
        self.metadata_text.delete(1.0, tk.END)
        
        if self.selected_dataset and self.selected_dataset.metadata:
            import json
            try:
                formatted_metadata = json.dumps(self.selected_dataset.metadata, indent=2)
                self.metadata_text.insert(1.0, formatted_metadata)
            except:
                self.metadata_text.insert(1.0, str(self.selected_dataset.metadata))
        else:
            self.metadata_text.insert(1.0, "No metadata available")
        
        self.metadata_text.config(state=tk.DISABLED)
    
    def update_statistics(self):
        """Update the statistics display (placeholder)."""
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        
        if self.selected_dataset:
            stats_text = f"Dataset Statistics for: {self.selected_dataset.name}\n"
            stats_text += "=" * 50 + "\n\n"
            stats_text += f"File Path: {self.selected_dataset.file_path}\n"
            stats_text += f"File Format: {self.selected_dataset.file_format}\n"
            
            if self.selected_dataset.file_size:
                stats_text += f"File Size: {self.selected_dataset.file_size:,} bytes\n"
            
            stats_text += f"Import Date: {self.selected_dataset.import_date}\n\n"
            
            # Get processing job count
            try:
                jobs = ProcessingJobOperations.list_jobs_for_dataset(self.selected_dataset.id)
                stats_text += f"Processing Jobs: {len(jobs)}\n"
                
                completed_jobs = [j for j in jobs if j.status == 'completed']
                stats_text += f"Completed Jobs: {len(completed_jobs)}\n"
                
                figures = FigureOperations.list_figures_for_dataset(self.selected_dataset.id)
                stats_text += f"Generated Figures: {len(figures)}\n"
                
            except Exception as e:
                stats_text += f"Error loading statistics: {e}\n"
            
            stats_text += "\n[Data preview functionality will be implemented in future updates]"
            
            self.stats_text.insert(1.0, stats_text)
        
        self.stats_text.config(state=tk.DISABLED)
    
    # Action methods
    def open_dataset_file(self):
        """Open the selected dataset file."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        file_path = self.selected_dataset.file_path
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"File not found: {file_path}")
            return
        
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def open_file_location(self):
        """Open the file location in file explorer."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        file_path = self.selected_dataset.file_path
        
        # Convert to absolute path if it's not already
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        directory = os.path.dirname(file_path)
        
        # Check if file exists first
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", 
                               f"File not found:\n{file_path}\n\n"
                               f"The file may have been moved or deleted.")
            return
        
        # Check if directory exists
        if not os.path.exists(directory):
            messagebox.showerror("Directory Not Found", 
                               f"Directory not found:\n{directory}\n\n"
                               f"The directory may have been moved or deleted.")
            return
        
        try:
            if platform.system() == 'Windows':
                # Use the absolute file path for Windows Explorer
                subprocess.call(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', '-R', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', directory])
        except Exception as e:
            messagebox.showerror("Error", 
                               f"Failed to open file location:\n{str(e)}\n\n"
                               f"File path: {file_path}\n"
                               f"Directory: {directory}")
    
    def copy_file_path(self):
        """Copy file path to clipboard."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        self.window.clipboard_clear()
        self.window.clipboard_append(self.selected_dataset.file_path)
        messagebox.showinfo("Copied", f"File path copied to clipboard:\n{self.selected_dataset.file_path}")
    
    def edit_dataset(self):
        """Edit dataset information."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        # Create edit dialog
        edit_window = tk.Toplevel(self.window)
        edit_window.title("Edit Dataset")
        edit_window.geometry("500x400")
        edit_window.transient(self.window)
        edit_window.grab_set()
        
        # Name field
        ttk.Label(edit_window, text="Name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        name_var = tk.StringVar(value=self.selected_dataset.name)
        name_entry = ttk.Entry(edit_window, textvariable=name_var, width=50)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Description field
        ttk.Label(edit_window, text="Description:").grid(row=1, column=0, sticky="nw", padx=10, pady=5)
        desc_text = tk.Text(edit_window, width=50, height=8)
        desc_text.grid(row=1, column=1, padx=10, pady=5)
        desc_text.insert(1.0, self.selected_dataset.description or "")
        
        # Buttons
        button_frame = ttk.Frame(edit_window)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def save_changes():
            new_name = name_var.get().strip()
            new_description = desc_text.get(1.0, tk.END).strip()
            
            if not new_name:
                messagebox.showerror("Error", "Name cannot be empty")
                return
            
            try:
                success = DatasetOperations.update_dataset(
                    self.selected_dataset.id,
                    name=new_name,
                    description=new_description
                )
                
                if success:
                    messagebox.showinfo("Success", "Dataset updated successfully")
                    edit_window.destroy()
                    self.load_datasets()  # Reload to show changes
                else:
                    messagebox.showerror("Error", "Failed to update dataset")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update dataset: {str(e)}")
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side="left", padx=5)
    
    def delete_dataset(self):
        """Delete the selected dataset."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        file_path = self.selected_dataset.file_path
        dataset_name = self.selected_dataset.name
        
        # Determine if this is a copied file (in data/raw directory)
        data_raw_path = os.path.abspath("data/raw")
        is_copied_file = file_path and file_path.startswith(data_raw_path)
        
        # Enhanced confirmation dialog
        if is_copied_file:
            # For copied files, offer choice to delete physical file
            dialog_text = (
                f"Delete dataset '{dataset_name}'?\n\n"
                f"This will delete:\n"
                f"• Dataset record from database\n"
                f"• All associated processing jobs and figures\n\n"
                f"The dataset file is a copy in your project:\n"
                f"{os.path.basename(file_path)}\n\n"
                f"Do you also want to delete the physical file?\n\n"
                f"YES = Delete database record AND file\n"
                f"NO = Delete database record only (keep file)\n"
                f"CANCEL = Don't delete anything"
            )
            
            # Create custom dialog with Yes/No/Cancel
            result = messagebox.askyesnocancel("Confirm Delete", dialog_text)
            
            if result is None:  # Cancel
                return
            elif result is True:  # Yes - delete both
                delete_file = True
                action_description = "Dataset and file deleted successfully"
            else:  # No - delete database only
                delete_file = False
                action_description = "Dataset deleted successfully (file kept)"
                
        else:
            # For original files, only ask about database deletion
            dialog_text = (
                f"Delete dataset '{dataset_name}'?\n\n"
                f"This will delete:\n"
                f"• Dataset record from database\n"
                f"• All associated processing jobs and figures\n\n"
                f"The original file will NOT be deleted:\n"
                f"{file_path}\n\n"
                f"This action cannot be undone."
            )
            
            result = messagebox.askyesno("Confirm Delete", dialog_text)
            
            if not result:
                return
            
            delete_file = False
            action_description = "Dataset deleted successfully (original file kept)"
        
        # Perform the deletion
        try:
            success = DatasetOperations.delete_dataset(self.selected_dataset.id, delete_file=delete_file)
            if success:
                messagebox.showinfo("Success", action_description)
                self.selected_dataset = None
                self.load_datasets()  # Reload list
                # Clear details panel
                for label in self.info_labels.values():
                    label.config(text="")
            else:
                messagebox.showerror("Error", "Failed to delete dataset")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete dataset: {str(e)}")
    
    def preview_data(self):
        """Preview dataset data."""
        if not self.selected_dataset:
            messagebox.showwarning("No Selection", "Please select a dataset first.")
            return
        
        file_path = self.selected_dataset.file_path
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"File not found: {file_path}")
            return
        
        # Create preview window
        preview_window = tk.Toplevel(self.window)
        preview_window.title(f"Data Preview - {self.selected_dataset.name}")
        preview_window.geometry("1000x700")
        preview_window.transient(self.window)
        
        # Create notebook for different preview modes
        preview_notebook = ttk.Notebook(preview_window)
        preview_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        try:
            # Load and preview the data
            self.create_data_preview_tabs(preview_notebook, file_path)
        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to preview data: {str(e)}")
            preview_window.destroy()
    
    def get_full_file_statistics(self):
        """Calculate statistics for the complete file."""
        if not self.selected_dataset:
            return None
        
        file_path = self.selected_dataset.file_path
        if not os.path.exists(file_path):
            return "File not found"
        
        try:
            # Import the full data using our importers
            from src.data_processing.importers import DataImportManager
            import pandas as pd
            
            import_manager = DataImportManager()
            
            # Get stored import settings from dataset metadata (same logic as preview)
            import_settings = {}
            if self.selected_dataset and self.selected_dataset.metadata:
                metadata = self.selected_dataset.metadata
                stored_settings = {}
                
                # Handle different metadata types (dict, bytes, or string) for backward compatibility
                try:
                    if isinstance(metadata, dict):
                        # Metadata is already a dict (new format with working JSON adapter)
                        stored_settings = metadata.get('import_settings', {})
                    elif isinstance(metadata, (bytes, str)):
                        # Metadata is bytes or string (legacy format or broken JSON adapter)
                        import json
                        if isinstance(metadata, bytes):
                            metadata = metadata.decode('utf-8')
                        parsed_metadata = json.loads(metadata)
                        stored_settings = parsed_metadata.get('import_settings', {})
                    else:
                        # Unknown metadata type, skip
                        stored_settings = {}
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
                    # If parsing fails, log and continue without import settings
                    print(f"Warning: Could not parse dataset metadata: {e}")
                    stored_settings = {}
                
                # Extract the settings we need for full file import
                if isinstance(stored_settings, dict):
                    for key in ['skip_rows', 'header_row', 'convert_numeric', 'handle_errors', 'raw_import']:
                        if key in stored_settings:
                            import_settings[key] = stored_settings[key]
            
            # Import the complete file (no row limit) but force raw mode for accurate file dimensions
            stats_settings = dict(import_settings)
            stats_settings['raw_import'] = True  # Force raw mode for accurate file statistics
            result = import_manager.import_file(file_path, **stats_settings)
            
            if not result['success']:
                return f"Error loading full file: {result['message']}"
            
            full_data = result['data']
            
            if not hasattr(full_data, 'shape'):
                return f"Full file loaded but not in tabular format\nData type: {type(full_data).__name__}"
            
            # Generate comprehensive statistics
            stats_text = ""
            
            # Basic shape information
            stats_text += f"Complete File Shape: {full_data.shape}\n"
            stats_text += f"Total Columns: {len(full_data.columns)}\n"
            stats_text += f"Total Rows: {len(full_data)}\n"
            stats_text += f"Memory Usage: {full_data.memory_usage(deep=True).sum() / (1024*1024):.2f} MB\n\n"
            
            # Data types summary
            dtype_counts = full_data.dtypes.value_counts()
            stats_text += "Data Types Summary:\n" + "-"*25 + "\n"
            for dtype, count in dtype_counts.items():
                stats_text += f"{dtype}: {count} columns\n"
            stats_text += "\n"
            
            # Missing values analysis
            missing_total = full_data.isnull().sum().sum()
            if missing_total > 0:
                stats_text += f"Missing Values: {missing_total:,} total ({missing_total/(len(full_data)*len(full_data.columns))*100:.2f}% of all cells)\n"
                missing_by_col = full_data.isnull().sum()
                cols_with_missing = missing_by_col[missing_by_col > 0]
                if len(cols_with_missing) <= 20:  # Show details if not too many columns
                    stats_text += "Columns with missing values:\n"
                    for col, count in cols_with_missing.items():
                        stats_text += f"  {col}: {count:,} ({count/len(full_data)*100:.1f}%)\n"
                else:
                    stats_text += f"Missing values found in {len(cols_with_missing)} columns\n"
                stats_text += "\n"
            else:
                stats_text += "Missing Values: None\n\n"
            
            # Numeric columns analysis
            numeric_cols = full_data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                stats_text += f"Numeric Columns: {len(numeric_cols)}\n"
                if len(numeric_cols) <= 5:  # Show summary stats for few columns
                    stats_text += "Numeric Summary (first 5 columns):\n"
                    desc_stats = full_data[numeric_cols[:5]].describe()
                    stats_text += desc_stats.to_string() + "\n\n"
                else:
                    # Just show basic stats for all numeric columns
                    stats_text += f"Numeric columns range from {full_data[numeric_cols].min().min():.4f} to {full_data[numeric_cols].max().max():.4f}\n\n"
            
            # Categorical columns analysis  
            cat_cols = full_data.select_dtypes(include=['object', 'category']).columns
            if len(cat_cols) > 0:
                stats_text += f"Categorical/Text Columns: {len(cat_cols)}\n"
                if len(cat_cols) <= 10:
                    for col in cat_cols[:10]:
                        unique_count = full_data[col].nunique()
                        stats_text += f"  {col}: {unique_count:,} unique values\n"
                    if len(cat_cols) > 10:
                        stats_text += f"  ... and {len(cat_cols) - 10} more categorical columns\n"
                else:
                    total_unique = sum(full_data[col].nunique() for col in cat_cols)
                    stats_text += f"Average unique values per categorical column: {total_unique/len(cat_cols):.1f}\n"
                stats_text += "\n"
            
            # File size vs memory usage
            file_size_mb = os.path.getsize(file_path) / (1024*1024)
            memory_mb = full_data.memory_usage(deep=True).sum() / (1024*1024)
            stats_text += f"File Size: {file_size_mb:.2f} MB\n"
            stats_text += f"Memory Usage: {memory_mb:.2f} MB\n"
            stats_text += f"Compression Ratio: {file_size_mb/memory_mb:.2f}x\n\n"
            
            return stats_text
            
        except Exception as e:
            return f"Error calculating full file statistics: {str(e)}"
    
    def create_data_preview_tabs(self, notebook, file_path):
        """Create different tabs for data preview."""
        # Import the data using our importers
        from src.data_processing.importers import DataImportManager
        import pandas as pd
        
        import_manager = DataImportManager()
        
        # Get stored import settings from dataset metadata (if available)
        import_settings = {}
        if self.selected_dataset and self.selected_dataset.metadata:
            metadata = self.selected_dataset.metadata
            stored_settings = {}
            
            # Handle different metadata types (dict, bytes, or string) for backward compatibility
            try:
                if isinstance(metadata, dict):
                    # Metadata is already a dict (new format with working JSON adapter)
                    stored_settings = metadata.get('import_settings', {})
                elif isinstance(metadata, (bytes, str)):
                    # Metadata is bytes or string (legacy format or broken JSON adapter)
                    import json
                    if isinstance(metadata, bytes):
                        metadata = metadata.decode('utf-8')
                    parsed_metadata = json.loads(metadata)
                    stored_settings = parsed_metadata.get('import_settings', {})
                else:
                    # Unknown metadata type, skip
                    stored_settings = {}
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
                # If parsing fails, log and continue without import settings
                print(f"Warning: Could not parse dataset metadata: {e}")
                stored_settings = {}
            
            # Extract the settings we need for preview
            if isinstance(stored_settings, dict):
                for key in ['skip_rows', 'header_row', 'convert_numeric', 'handle_errors', 'raw_import']:
                    if key in stored_settings:
                        import_settings[key] = stored_settings[key]
        
        # Preview with limited rows but force raw mode to show actual file content
        preview_settings = dict(import_settings)
        preview_settings['raw_import'] = True  # Force raw mode for preview to avoid header consumption
        result = import_manager.preview_file(file_path, max_rows=100, **preview_settings)
        
        if not result['success']:
            raise Exception(result['message'])
        
        data = result['data']
        
        # Tab 1: Data Table View
        self.create_table_preview_tab(notebook, data)
        
        # Tab 2: Summary Statistics
        self.create_statistics_preview_tab(notebook, data, result.get('statistics'))
        
        # Tab 3: Data Info
        self.create_info_preview_tab(notebook, data, result)
        
        # Tab 4: Raw Data (for text files or first few lines)
        self.create_raw_preview_tab(notebook, file_path)
    
    def create_table_preview_tab(self, notebook, data):
        """Create table view tab for data preview."""
        import pandas as pd
        
        table_frame = ttk.Frame(notebook)
        notebook.add(table_frame, text="Data Table")
        
        # Info label with more detail
        if hasattr(data, 'shape'):
            info_text = f"Preview: Showing first {data.shape[0]} rows of dataset (limited for performance)"
            if data.shape[0] == 100:
                info_text += f"\nNote: Full dataset may contain more rows - see Statistics tab for complete file info"
        else:
            info_text = "Data preview (format may not support tabular display)"
        
        info_label = ttk.Label(table_frame, text=info_text, font=("Arial", 9, "italic"))
        info_label.pack(pady=5)
        
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        if hasattr(data, 'columns') and hasattr(data, 'iloc'):
            # DataFrame - create table view
            columns = list(data.columns)
            
            # Create treeview with columns
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=25)
            
            # Configure column headings and widths
            for col in columns:
                tree.heading(col, text=str(col))
                tree.column(col, width=120, minwidth=80)
            
            # Add data rows
            for i, row in data.iterrows():
                values = []
                for col in columns:
                    val = row[col]
                    # Format the value for display
                    if pd.isna(val):
                        val_str = "NaN"
                    elif isinstance(val, float):
                        val_str = f"{val:.4f}" if abs(val) < 1000 else f"{val:.2e}"
                    else:
                        val_str = str(val)
                    
                    # Truncate long strings
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    
                    values.append(val_str)
                
                tree.insert("", "end", values=values)
            
            # Add scrollbars
            v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
            
            tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Pack widgets
            tree.pack(side="left", fill="both", expand=True)
            v_scrollbar.pack(side="right", fill="y")
            h_scrollbar.pack(side="bottom", fill="x")
            
        else:
            # Not a DataFrame - show as text
            text_widget = tk.Text(tree_frame, wrap=tk.WORD)
            text_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=text_scrollbar.set)
            
            if isinstance(data, list):
                # List data
                for i, item in enumerate(data[:100]):
                    text_widget.insert(tk.END, f"Row {i+1}: {str(item)}\n")
            else:
                # Other data types
                text_widget.insert(tk.END, str(data))
            
            text_widget.pack(side="left", fill="both", expand=True)
            text_scrollbar.pack(side="right", fill="y")
            text_widget.config(state=tk.DISABLED)

    def create_statistics_preview_tab(self, notebook, data, statistics):
        """Create statistics preview tab with both preview and full file statistics."""
        import pandas as pd
        
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="Statistics")
        
        # Create text widget for statistics
        stats_text = tk.Text(stats_frame, wrap=tk.WORD, font=("Consolas", 10))
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=stats_text.yview)
        stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        stats_content = f"Dataset Statistics\n{'='*70}\n\n"
        
        # Section 1: Full File Statistics
        stats_content += f"📊 FULL FILE STATISTICS\n{'='*50}\n"
        try:
            full_file_stats = self.get_full_file_statistics()
            if full_file_stats:
                stats_content += full_file_stats + "\n"
            else:
                stats_content += "Unable to calculate full file statistics.\n\n"
        except Exception as e:
            stats_content += f"Error calculating full file statistics: {str(e)}\n\n"
        
        # Section 2: Preview Data Statistics  
        stats_content += f"🔍 PREVIEW DATA STATISTICS (First 100 rows shown in table)\n{'='*60}\n"
        
        if hasattr(data, 'describe'):
            # DataFrame statistics
            try:
                # Basic info
                stats_content += f"Preview Shape: {data.shape}\n"
                stats_content += f"Preview Columns: {len(data.columns)}\n"
                stats_content += f"Preview Rows: {len(data)}\n\n"
                
                # Data types
                stats_content += "Data Types:\n" + "-"*20 + "\n"
                for col, dtype in data.dtypes.items():
                    stats_content += f"{col}: {dtype}\n"
                stats_content += "\n"
                
                # Missing values in preview
                missing = data.isnull().sum()
                if missing.sum() > 0:
                    stats_content += "Missing Values (in preview):\n" + "-"*30 + "\n"
                    for col, count in missing.items():
                        if count > 0:
                            stats_content += f"{col}: {count} ({count/len(data)*100:.1f}%)\n"
                    stats_content += "\n"
                
                # Descriptive statistics for numeric columns (preview only)
                numeric_cols = data.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0 and len(numeric_cols) <= 10:  # Only show if reasonable number of columns
                    stats_content += "Descriptive Statistics - Preview Data (Numeric Columns):\n" + "-"*55 + "\n"
                    desc_stats = data[numeric_cols].describe()
                    stats_content += desc_stats.to_string() + "\n\n"
                elif len(numeric_cols) > 10:
                    stats_content += f"Descriptive Statistics: {len(numeric_cols)} numeric columns (too many to display)\n\n"
                
                # Categorical columns summary (preview only)
                cat_cols = data.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0:
                    stats_content += "Categorical Columns Summary - Preview Data:\n" + "-"*45 + "\n"
                    for col in cat_cols[:5]:  # Limit to first 5 categorical columns
                        unique_count = data[col].nunique()
                        stats_content += f"{col}: {unique_count} unique values (in preview)\n"
                        if unique_count <= 10:
                            value_counts = data[col].value_counts().head(5)
                            for val, count in value_counts.items():
                                stats_content += f"  {val}: {count}\n"
                        stats_content += "\n"
                    
                    if len(cat_cols) > 5:
                        stats_content += f"... and {len(cat_cols) - 5} more categorical columns\n\n"
                        
            except Exception as e:
                stats_content += f"Error generating preview statistics: {str(e)}\n"
        
        elif statistics:
            # Use provided statistics
            stats_content += "File Import Statistics:\n" + "-"*25 + "\n"
            for key, value in statistics.items():
                if isinstance(value, dict):
                    stats_content += f"{key}:\n"
                    for subkey, subvalue in value.items():
                        stats_content += f"  {subkey}: {subvalue}\n"
                else:
                    stats_content += f"{key}: {value}\n"
            stats_content += "\n"
        
        else:
            stats_content += "No preview statistics available for this data type.\n"
        
        stats_text.insert(1.0, stats_content)
        stats_text.config(state=tk.DISABLED)
        
        stats_text.pack(side="left", fill="both", expand=True)
        stats_scrollbar.pack(side="right", fill="y")
    
    def create_info_preview_tab(self, notebook, data, result):
        """Create info preview tab."""
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Data Info")
        
        info_text = tk.Text(info_frame, wrap=tk.WORD, font=("Consolas", 10))
        info_scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=info_text.yview)
        info_text.configure(yscrollcommand=info_scrollbar.set)
        
        info_content = f"Data Import Information\n{'='*50}\n\n"
        
        # Import result information
        info_content += f"Preview Import Status: {'Success' if result['success'] else 'Failed'}\n"
        info_content += f"Message: {result.get('message', 'N/A')}\n\n"
        
        # File information
        file_path = self.selected_dataset.file_path
        info_content += f"File Information:\n{'-'*20}\n"
        info_content += f"Path: {file_path}\n"
        info_content += f"Size: {os.path.getsize(file_path):,} bytes ({os.path.getsize(file_path)/(1024*1024):.2f} MB)\n"
        info_content += f"Modified: {datetime.fromtimestamp(os.path.getmtime(file_path))}\n\n"
        
        # Data structure info
        if hasattr(data, 'shape'):
            info_content += f"Preview Data Structure (First 100 rows):\n{'-'*40}\n"
            info_content += f"Type: {type(data).__name__}\n"
            info_content += f"Preview Shape: {data.shape}\n"
            info_content += f"Preview Memory Usage: {data.memory_usage(deep=True).sum() / 1024:.2f} KB\n\n"
        
        # Metadata from database
        if self.selected_dataset.metadata:
            info_content += f"Stored Metadata:\n{'-'*20}\n"
            import json
            try:
                formatted_metadata = json.dumps(self.selected_dataset.metadata, indent=2)
                info_content += formatted_metadata + "\n\n"
            except:
                info_content += str(self.selected_dataset.metadata) + "\n\n"
        
        # Sample of data structure
        if hasattr(data, 'dtypes'):
            info_content += f"Column Information:\n{'-'*20}\n"
            for i, (col, dtype) in enumerate(data.dtypes.items()):
                sample_values = data[col].dropna().head(3).tolist()
                sample_str = ", ".join([str(v)[:20] for v in sample_values])
                info_content += f"{i+1:2d}. {col} ({dtype}): {sample_str}...\n"
        
        info_text.insert(1.0, info_content)
        info_text.config(state=tk.DISABLED)
        
        info_text.pack(side="left", fill="both", expand=True)
        info_scrollbar.pack(side="right", fill="y")
    
    def create_raw_preview_tab(self, notebook, file_path):
        """Create raw file preview tab."""
        raw_frame = ttk.Frame(notebook)
        notebook.add(raw_frame, text="Raw Data")
        
        # Info label
        info_label = ttk.Label(raw_frame, 
                              text="Showing first 50 lines of raw file", 
                              font=("Arial", 9, "italic"))
        info_label.pack(pady=5)
        
        raw_text = tk.Text(raw_frame, wrap=tk.NONE, font=("Consolas", 9))
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(raw_frame, orient="vertical", command=raw_text.yview)
        h_scrollbar = ttk.Scrollbar(raw_frame, orient="horizontal", command=raw_text.xview)
        raw_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        try:
            # Read first 50 lines of the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 50:  # Limit to first 50 lines
                        break
                    lines.append(f"{i+1:3d}: {line.rstrip()}")
                
                raw_content = "\n".join(lines)
                if i >= 49:  # If we hit the limit
                    raw_content += f"\n\n... (showing first 50 lines only)"
                
                raw_text.insert(1.0, raw_content)
                
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= 50:
                            break
                        lines.append(f"{i+1:3d}: {line.rstrip()}")
                    
                    raw_content = "\n".join(lines)
                    if i >= 49:
                        raw_content += f"\n\n... (showing first 50 lines only)"
                    
                    raw_text.insert(1.0, raw_content)
            except:
                raw_text.insert(1.0, "Unable to preview file - may be binary or use unsupported encoding")
        except Exception as e:
            raw_text.insert(1.0, f"Error reading file: {str(e)}")
        
        raw_text.config(state=tk.DISABLED)
        
        # Pack widgets
        raw_text.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

    def view_job_details(self):
        """View processing job details."""
        messagebox.showinfo("Coming Soon", "Job details view will be implemented soon!")
    
    def open_job_output(self):
        """Open job output file."""
        messagebox.showinfo("Coming Soon", "Job output opening will be implemented soon!")
    
    def rerun_job(self):
        """Rerun a processing job."""
        messagebox.showinfo("Coming Soon", "Job rerun functionality will be implemented soon!")
    
    def open_figure(self):
        """Open selected figure."""
        selection = self.figures_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a figure first.")
            return
        
        messagebox.showinfo("Coming Soon", "Figure opening will be implemented soon!")
    
    def copy_figure_path(self):
        """Copy figure path to clipboard."""
        messagebox.showinfo("Coming Soon", "Figure path copying will be implemented soon!")
    
    def export_figure(self):
        """Export selected figure."""
        messagebox.showinfo("Coming Soon", "Figure export will be implemented soon!")
    
    def edit_metadata(self):
        """Edit dataset metadata."""
        messagebox.showinfo("Coming Soon", "Metadata editing will be implemented soon!")
    
    def export_metadata(self):
        """Export dataset metadata."""
        messagebox.showinfo("Coming Soon", "Metadata export will be implemented soon!")
    
    # Processed data action methods
    def open_processed_data_location(self):
        """Open the location of selected processed data."""
        selection = self.processed_data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select processed data first.")
            return
        
        try:
            item = self.processed_data_tree.item(selection[0])
            processed_data_id = int(item['text'])
            
            processed_data = ProcessedDataOperations.get_processed_data(processed_data_id)
            if not processed_data:
                messagebox.showerror("Error", "Processed data not found.")
                return
            
            file_path = processed_data.file_path
            directory = os.path.dirname(file_path)
            
            if not os.path.exists(directory):
                messagebox.showerror("Directory Not Found", 
                                   f"Directory not found:\n{directory}")
                return
            
            if platform.system() == 'Windows':
                subprocess.call(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', '-R', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', directory])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open location: {str(e)}")
    
    def view_processed_data_info(self):
        """View information about selected processed data."""
        selection = self.processed_data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select processed data first.")
            return
        
        try:
            item = self.processed_data_tree.item(selection[0])
            processed_data_id = int(item['text'])
            
            processed_data = ProcessedDataOperations.get_processed_data(processed_data_id)
            if not processed_data:
                messagebox.showerror("Error", "Processed data not found.")
                return
            
            # Create info window
            info_window = tk.Toplevel(self.window)
            info_window.title(f"Processed Data Info - {processed_data.data_name}")
            info_window.geometry("600x500")
            info_window.transient(self.window)
            
            # Info text
            info_text = tk.Text(info_window, wrap=tk.WORD, font=("Consolas", 10))
            info_scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=info_text.yview)
            info_text.configure(yscrollcommand=info_scrollbar.set)
            
            # Format info content
            info_content = f"Processed Data Information\n{'='*50}\n\n"
            info_content += f"Data Name: {processed_data.data_name}\n"
            info_content += f"Data Type: {processed_data.data_type}\n"
            info_content += f"File Path: {processed_data.file_path}\n"
            info_content += f"File Size: {processed_data.file_size or 'Unknown'} bytes\n"
            info_content += f"Created: {processed_data.created_at or 'Unknown'}\n\n"
            
            if processed_data.parameters:
                info_content += f"Processing Parameters:\n{'-'*30}\n"
                import json
                try:
                    formatted_params = json.dumps(processed_data.parameters, indent=2)
                    info_content += formatted_params
                except:
                    info_content += str(processed_data.parameters)
            
            info_text.insert(1.0, info_content)
            info_text.config(state=tk.DISABLED)
            
            info_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            info_scrollbar.pack(side="right", fill="y", pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view info: {str(e)}")
    
    def delete_processed_data(self):
        """Delete selected processed data."""
        selection = self.processed_data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select processed data first.")
            return
        
        try:
            item = self.processed_data_tree.item(selection[0])
            processed_data_id = int(item['text'])
            
            processed_data = ProcessedDataOperations.get_processed_data(processed_data_id)
            if not processed_data:
                messagebox.showerror("Error", "Processed data not found.")
                return
            
            # Confirmation dialog
            result = messagebox.askyesnocancel(
                "Confirm Delete",
                f"Delete processed data '{processed_data.data_name}'?\n\n"
                f"YES = Delete database record AND file\n"
                f"NO = Delete database record only (keep file)\n"
                f"CANCEL = Don't delete anything"
            )
            
            if result is None:  # Cancel
                return
            elif result is True:  # Yes - delete both
                delete_file = True
                action_description = "Processed data and file deleted successfully"
            else:  # No - delete database only
                delete_file = False
                action_description = "Processed data deleted successfully (file kept)"
            
            success = ProcessedDataOperations.delete_processed_data(processed_data_id, delete_file=delete_file)
            if success:
                messagebox.showinfo("Success", action_description)
                self.update_processed_data_list()  # Refresh the list
            else:
                messagebox.showerror("Error", "Failed to delete processed data")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete processed data: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    app = DataBrowserGUI()
    root.mainloop()
