"""
Figure Generation GUI - Interface for creating visualizations and figures.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, FigureOperations, ProcessingJobOperations

# Import matplotlib for figure display
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class FigureGenerationGUI:
    """GUI for figure generation functionality."""
    
    # Mode definitions - will be populated with custom modes
    # This dictionary will store mode configurations as they are added
    MODE_DEFINITIONS = {
        "RasterPlot": {
            "description": "Visualize raster matrix data with customizable labels and colormaps",
            "file_types": [".npy", ".csv"],
            "required_files": [
                {"name": "raster_matrix", "label": "Raster", "description": "Raster matrix file (.npy)", "pattern": "Raster_matrix*", "extension": ".npy"},
                {"name": "row_labels", "label": "Row Labels", "description": "Row labels file (.csv)", "pattern": "*row_labels", "extension": ".csv", "optional": True},
                {"name": "column_labels", "label": "Column Labels", "description": "Column labels file (.csv)", "pattern": "*column_labels", "extension": ".csv", "optional": True}
            ],
            "controls": {
                "colormap": ["binary", "jet", "viridis", "gist_earth"],
                "row_title_default": "Neurons",
                "column_title_default": "Time",
                "label_count_default": 6
            }
        }
    }
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Figure Generation")
        self.window.geometry("1200x1200")  # Increased size for new tab
        self.window.configure(bg='#f0f0f0')
        
        # Initialize variables
        self.selected_dataset = None
        self.selected_file = None
        self.current_data = None
        self.figure_canvas = None
        self.mode_controls_frame = None
        
        # Check matplotlib availability
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning("Missing Dependencies", 
                                 "Matplotlib is not available. Figure Inspection functionality will be limited.")
        
        self.setup_ui()
        self.load_datasets()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = ttk.Label(self.window, text="Figure Generation", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Create figure tab
        self.create_figure_tab(notebook)
        
        # Browse figures tab
        self.create_browse_tab(notebook)
        
        # Figure Inspection tab
        self.create_inspection_tab(notebook)
    
    def create_figure_tab(self, parent):
        """Create the figure generation tab."""
        fig_frame = ttk.Frame(parent)
        parent.add(fig_frame, text="Create Figure")
        
        # Dataset selection frame
        dataset_frame = ttk.LabelFrame(fig_frame, text="Data Selection", padding=10)
        dataset_frame.pack(fill="x", padx=10, pady=5)
        
        # Dataset selection
        ttk.Label(dataset_frame, text="Select Dataset:").grid(row=0, column=0, sticky="w", padx=5)
        
        self.dataset_combo_var = tk.StringVar()
        self.dataset_combo = ttk.Combobox(dataset_frame, textvariable=self.dataset_combo_var,
                                         state="readonly", width=40)
        self.dataset_combo.grid(row=0, column=1, padx=5, pady=2)
        self.dataset_combo.bind('<<ComboboxSelected>>', self.on_dataset_select)
        
        # Processing job selection (optional)
        ttk.Label(dataset_frame, text="Processing Job (optional):").grid(row=1, column=0, sticky="w", padx=5)
        
        self.job_combo_var = tk.StringVar()
        self.job_combo = ttk.Combobox(dataset_frame, textvariable=self.job_combo_var,
                                     state="readonly", width=40)
        self.job_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # Figure options frame
        options_frame = ttk.LabelFrame(fig_frame, text="Figure Options", padding=10)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        # Figure type
        ttk.Label(options_frame, text="Figure Type:").grid(row=0, column=0, sticky="w", padx=5)
        self.figure_type_var = tk.StringVar()
        figure_type_combo = ttk.Combobox(options_frame, textvariable=self.figure_type_var,
                                        values=["Line Plot", "Scatter Plot", "Histogram", 
                                               "Box Plot", "Heatmap", "3D Plot", "Custom"],
                                        state="readonly", width=20)
        figure_type_combo.grid(row=0, column=1, padx=5, pady=2)
        figure_type_combo.bind('<<ComboboxSelected>>', self.on_figure_type_change)
        
        # Figure name
        ttk.Label(options_frame, text="Figure Name:").grid(row=0, column=2, sticky="w", padx=5)
        self.figure_name_var = tk.StringVar()
        figure_name_entry = ttk.Entry(options_frame, textvariable=self.figure_name_var, width=25)
        figure_name_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # Output format
        ttk.Label(options_frame, text="Output Format:").grid(row=1, column=0, sticky="w", padx=5)
        self.output_format_var = tk.StringVar(value="png")
        format_combo = ttk.Combobox(options_frame, textvariable=self.output_format_var,
                                   values=["png", "pdf", "svg", "jpg", "eps"],
                                   state="readonly", width=20)
        format_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # DPI/Quality
        ttk.Label(options_frame, text="DPI/Quality:").grid(row=1, column=2, sticky="w", padx=5)
        self.dpi_var = tk.StringVar(value="300")
        dpi_entry = ttk.Entry(options_frame, textvariable=self.dpi_var, width=25)
        dpi_entry.grid(row=1, column=3, padx=5, pady=2)
        
        # Plot parameters frame
        params_frame = ttk.LabelFrame(fig_frame, text="Plot Parameters", padding=10)
        params_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dynamic parameters based on figure type
        self.params_container = ttk.Frame(params_frame)
        self.params_container.pack(fill="both", expand=True)
        
        self.param_widgets = {}
        self.create_default_plot_params()
        
        # Preview and generation frame
        action_frame = ttk.Frame(fig_frame)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(action_frame, text="Preview Figure", 
                  command=self.preview_figure).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Generate Figure", 
                  command=self.generate_figure).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Batch Generate", 
                  command=self.batch_generate).pack(side="left", padx=5)
    
    def create_browse_tab(self, parent):
        """Create the figure browsing tab."""
        browse_frame = ttk.Frame(parent)
        parent.add(browse_frame, text="Browse Figures")
        
        # Filter frame
        filter_frame = ttk.LabelFrame(browse_frame, text="Filters", padding=10)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        # Dataset filter
        ttk.Label(filter_frame, text="Dataset:").grid(row=0, column=0, sticky="w", padx=5)
        self.filter_dataset_var = tk.StringVar()
        filter_dataset_combo = ttk.Combobox(filter_frame, textvariable=self.filter_dataset_var,
                                           state="readonly", width=20)
        filter_dataset_combo.grid(row=0, column=1, padx=5)
        
        # Figure type filter
        ttk.Label(filter_frame, text="Type:").grid(row=0, column=2, sticky="w", padx=5)
        self.filter_type_var = tk.StringVar()
        filter_type_combo = ttk.Combobox(filter_frame, textvariable=self.filter_type_var,
                                        values=["All", "Line Plot", "Scatter Plot", "Histogram"],
                                        state="readonly", width=15)
        filter_type_combo.grid(row=0, column=3, padx=5)
        filter_type_combo.set("All")
        
        # Search
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=4, sticky="w", padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=20)
        search_entry.grid(row=0, column=5, padx=5)
        
        ttk.Button(filter_frame, text="Apply Filters", 
                  command=self.apply_filters).grid(row=0, column=6, padx=5)
        
        # Figures list frame
        list_frame = ttk.Frame(browse_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Figures treeview
        self.figures_tree = ttk.Treeview(list_frame, 
                                        columns=("dataset", "type", "created", "path"), 
                                        show="tree headings", height=15)
        self.figures_tree.pack(side="left", fill="both", expand=True)
        
        # Tree headings
        self.figures_tree.heading("#0", text="Figure Name")
        self.figures_tree.heading("dataset", text="Dataset")
        self.figures_tree.heading("type", text="Type")
        self.figures_tree.heading("created", text="Created")
        self.figures_tree.heading("path", text="File Path")
        
        # Tree column widths
        self.figures_tree.column("#0", width=150)
        self.figures_tree.column("dataset", width=120)
        self.figures_tree.column("type", width=100)
        self.figures_tree.column("created", width=120)
        self.figures_tree.column("path", width=200)
        
        figures_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        figures_scrollbar.pack(side="right", fill="y")
        
        self.figures_tree.config(yscrollcommand=figures_scrollbar.set)
        figures_scrollbar.config(command=self.figures_tree.yview)
        
        # Figure actions frame
        fig_actions_frame = ttk.Frame(browse_frame)
        fig_actions_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(fig_actions_frame, text="Open Figure", 
                  command=self.open_figure).pack(side="left", padx=5)
        ttk.Button(fig_actions_frame, text="Copy Path", 
                  command=self.copy_figure_path).pack(side="left", padx=5)
        ttk.Button(fig_actions_frame, text="Delete Figure", 
                  command=self.delete_figure).pack(side="left", padx=5)
        ttk.Button(fig_actions_frame, text="Export Figure", 
                  command=self.export_figure).pack(side="left", padx=5)
        
        # Load figures initially
        self.load_figures()
    
    def create_inspection_tab(self, parent):
        """Create the figure inspection tab."""
        if not MATPLOTLIB_AVAILABLE:
            # Create a simple message frame if matplotlib is not available
            inspection_frame = ttk.Frame(parent)
            parent.add(inspection_frame, text="Figure Inspection")
            
            message_label = ttk.Label(inspection_frame, 
                                    text="Matplotlib is required for Figure Inspection functionality.\nPlease install matplotlib to use this feature.",
                                    font=("Arial", 12), justify="center")
            message_label.pack(expand=True)
            return
        
        inspection_frame = ttk.Frame(parent)
        parent.add(inspection_frame, text="Figure Inspection")
        
        # Data Selection Section (Top)
        self.create_inspection_data_selection(inspection_frame)
        
        # Required Files Section (Between Data Selection and Figure Display)
        self.create_required_files_section(inspection_frame)
        
        # Figure Display Section (Middle)
        self.create_inspection_figure_display(inspection_frame)
        
        # Controls Section (Bottom)
        self.create_inspection_controls(inspection_frame)
        
        # Action buttons
        self.create_inspection_actions(inspection_frame)
    
    def create_inspection_data_selection(self, parent):
        """Create the data selection section for inspection tab."""
        selection_frame = ttk.LabelFrame(parent, text="Data Selection", padding=10)
        selection_frame.pack(fill="x", padx=10, pady=5)
        
        # Dataset selection
        ttk.Label(selection_frame, text="Dataset:").grid(row=0, column=0, sticky="w", padx=5)
        self.inspection_dataset_var = tk.StringVar()
        self.inspection_dataset_combo = ttk.Combobox(selection_frame, 
                                                   textvariable=self.inspection_dataset_var,
                                                   state="readonly", width=35)
        self.inspection_dataset_combo.grid(row=0, column=1, padx=5, pady=2)
        self.inspection_dataset_combo.bind('<<ComboboxSelected>>', self.on_inspection_dataset_select)
        
        # Mode selection
        ttk.Label(selection_frame, text="Mode:").grid(row=0, column=2, sticky="w", padx=5)
        self.inspection_mode_var = tk.StringVar()
        self.inspection_mode_combo = ttk.Combobox(selection_frame, 
                                                textvariable=self.inspection_mode_var,
                                                state="readonly", width=35)
        self.inspection_mode_combo.grid(row=0, column=3, padx=5, pady=2)
        self.inspection_mode_combo.bind('<<ComboboxSelected>>', self.on_inspection_mode_select)
        
        # Load datasets for inspection
        self.load_inspection_datasets()
    
    def create_required_files_section(self, parent):
        """Create the required files section for mode-specific file selection."""
        self.required_files_frame = ttk.LabelFrame(parent, text="Required Files", padding=10)
        self.required_files_frame.pack(fill="x", padx=10, pady=5)
        
        # This will be populated dynamically based on selected mode
        self.file_requirements_container = ttk.Frame(self.required_files_frame)
        self.file_requirements_container.pack(fill="x")
        
        # Initially empty with instruction text
        self.files_instruction_label = ttk.Label(self.file_requirements_container, 
                                               text="Select a dataset and mode to see file requirements",
                                               font=("Arial", 10), foreground="gray")
        self.files_instruction_label.pack(pady=10)
        
        # Store file selection widgets for dynamic access
        self.file_selection_widgets = {}
    
    def create_inspection_figure_display(self, parent):
        """Create the figure display section."""
        display_frame = ttk.LabelFrame(parent, text="Figure Display", padding=5)
        display_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create matplotlib figure and canvas
        self.inspection_fig = Figure(figsize=(10, 6), dpi=100)
        self.inspection_ax = self.inspection_fig.add_subplot(111)
        
        self.figure_canvas = FigureCanvasTkAgg(self.inspection_fig, display_frame)
        self.figure_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Initialize with empty plot
        self.inspection_ax.text(0.5, 0.5, 'Select dataset, file, and mode to display figure', 
                              ha='center', va='center', transform=self.inspection_ax.transAxes,
                              fontsize=12, alpha=0.7)
        self.figure_canvas.draw()
    
    def create_inspection_controls(self, parent):
        """Create the mode-specific controls section."""
        self.controls_frame = ttk.LabelFrame(parent, text="Figure Controls", padding=10)
        self.controls_frame.pack(fill="x", padx=10, pady=5)
        
        # This will be populated dynamically based on selected mode
        self.mode_controls_frame = ttk.Frame(self.controls_frame)
        self.mode_controls_frame.pack(fill="x")
        
        # Common controls that are always visible
        common_frame = ttk.Frame(self.controls_frame)
        common_frame.pack(fill="x", pady=5)
        
        ttk.Label(common_frame, text="Figure Title:").grid(row=0, column=0, sticky="w", padx=5)
        self.inspection_title_var = tk.StringVar()
        ttk.Entry(common_frame, textvariable=self.inspection_title_var, width=30).grid(row=0, column=1, padx=5)
        
        ttk.Label(common_frame, text="DPI:").grid(row=0, column=2, sticky="w", padx=5)
        self.inspection_dpi_var = tk.StringVar(value="300")
        ttk.Entry(common_frame, textvariable=self.inspection_dpi_var, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(common_frame, text="Format:").grid(row=0, column=4, sticky="w", padx=5)
        self.inspection_format_var = tk.StringVar(value="png")
        format_combo = ttk.Combobox(common_frame, textvariable=self.inspection_format_var,
                                  values=["png", "pdf", "svg", "jpg"], state="readonly", width=8)
        format_combo.grid(row=0, column=5, padx=5)
    
    def create_inspection_actions(self, parent):
        """Create action buttons for inspection tab."""
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Reset View", 
                  command=self.reset_inspection_view).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="Refresh Data", 
                  command=self.refresh_inspection_data).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="Save Figure", 
                  command=self.save_inspection_figure).pack(side="right", padx=5)
    
    def load_inspection_datasets(self):
        """Load datasets for the inspection tab."""
        try:
            datasets = DatasetOperations.list_datasets()
            dataset_names = [f"{dataset.name} (ID: {dataset.id})" for dataset in datasets]
            
            self.inspection_dataset_combo['values'] = dataset_names
            
            # Store dataset objects for reference
            self.inspection_dataset_objects = {f"{dataset.name} (ID: {dataset.id})": dataset 
                                             for dataset in datasets}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load datasets: {str(e)}")
    
    def on_inspection_dataset_select(self, event=None):
        """Handle dataset selection in inspection tab."""
        selected = self.inspection_dataset_var.get()
        if selected and selected in self.inspection_dataset_objects:
            self.selected_dataset = self.inspection_dataset_objects[selected]
            
            # Load files for this dataset (for later use in Required Files section)
            self.load_dataset_files()
            
            # Load all available modes (no longer file-type dependent)
            self.load_all_modes()
            
            # Clear mode selection and required files
            self.inspection_mode_var.set("")
            self.clear_required_files_section()
            
            # Clear figure
            self.clear_inspection_figure()
    
    def load_dataset_files(self):
        """Load available files for the selected dataset."""
        if not self.selected_dataset:
            return
        
        files = []
        
        try:
            # Get raw files from filesystem
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            
            # Raw files
            raw_path = os.path.join(dataset_path, "raw")
            if os.path.exists(raw_path):
                for file in os.listdir(raw_path):
                    if file.endswith(('.csv', '.txt', '.xlsx', '.npy', '.npz')):
                        files.append(f"raw/{file}")
            
            # Processed files
            processed_path = os.path.join(dataset_path, "processed")
            if os.path.exists(processed_path):
                for root, dirs, filenames in os.walk(processed_path):
                    for file in filenames:
                        if file.endswith(('.csv', '.txt', '.xlsx', '.npy', '.npz')):
                            rel_path = os.path.relpath(os.path.join(root, file), dataset_path)
                            files.append(rel_path.replace('\\', '/'))  # Normalize path separators
            
            # Store available files for use in Required Files section
            self.available_files = sorted(files)
            
        except Exception as e:
            print(f"Error loading dataset files: {e}")
            messagebox.showerror("Error", f"Failed to load dataset files: {str(e)}")
    
    def load_all_modes(self):
        """Load all available modes for the inspection tab."""
        # Get all available modes from MODE_DEFINITIONS
        all_modes = list(self.MODE_DEFINITIONS.keys())
        
        self.inspection_mode_combo['values'] = all_modes
    
    def clear_required_files_section(self):
        """Clear the required files section."""
        # Clear all file selection widgets
        for widget in self.file_requirements_container.winfo_children():
            widget.destroy()
        
        # Reset instruction label
        self.files_instruction_label = ttk.Label(self.file_requirements_container, 
                                               text="Select a dataset and mode to see file requirements",
                                               font=("Arial", 10), foreground="gray")
        self.files_instruction_label.pack(pady=10)
        
        # Clear stored widgets
        self.file_selection_widgets = {}
    
    def create_required_files_widgets(self, mode):
        """Create file selection widgets based on mode requirements."""
        # Clear existing widgets
        self.clear_required_files_section()
        
        # Get mode configuration from MODE_DEFINITIONS
        if mode not in self.MODE_DEFINITIONS:
            # Show message that mode is not configured yet
            info_label = ttk.Label(self.file_requirements_container, 
                                 text=f"Mode '{mode}' is not configured yet.\nFile requirements will be defined when the mode is implemented.",
                                 font=("Arial", 10), foreground="gray", justify="center")
            info_label.pack(pady=20)
            return
        
        mode_config = self.MODE_DEFINITIONS[mode]
        
        if not mode_config or 'required_files' not in mode_config:
            return
        
        # Handle RasterPlot mode specifically
        if mode == "RasterPlot":
            self.create_rasterplot_file_widgets(mode_config)
        else:
            # Generic file widgets for other modes
            self.create_generic_file_widgets(mode_config)
    
    def create_generic_file_widgets(self, mode_config):
        """Create generic file selection widgets."""
        # Create widgets for each required file
        for i, file_req in enumerate(mode_config['required_files']):
            file_frame = ttk.Frame(self.file_requirements_container)
            file_frame.pack(fill="x", pady=2)
            
            # Label
            label_text = file_req['label']
            if file_req.get('optional', False):
                label_text += " (Optional)"
            
            ttk.Label(file_frame, text=f"{label_text}:").grid(row=0, column=0, sticky="w", padx=5)
            
            # File selection dropdown
            file_var = tk.StringVar()
            file_combo = ttk.Combobox(file_frame, textvariable=file_var, state="readonly", width=40)
            file_combo.grid(row=0, column=1, padx=5, pady=2)
            
            # Populate with appropriate files based on file types
            if hasattr(self, 'available_files'):
                compatible_files = self.filter_files_by_type(mode_config['file_types'])
                file_combo['values'] = compatible_files
            
            # Bind change event
            file_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
            
            # Description label
            if 'description' in file_req:
                desc_label = ttk.Label(file_frame, text=file_req['description'], 
                                     font=("Arial", 8), foreground="gray")
                desc_label.grid(row=1, column=1, sticky="w", padx=5)
            
            # Store reference
            self.file_selection_widgets[file_req['name']] = {
                'var': file_var,
                'combo': file_combo,
                'frame': file_frame,
                'config': file_req
            }
    
    def create_rasterplot_file_widgets(self, mode_config):
        """Create RasterPlot-specific file selection widgets."""
        # Initialize RasterPlot-specific variables
        self.raster_row_labels_enabled = tk.BooleanVar(value=True)
        self.raster_row_label_count = tk.StringVar(value=str(mode_config['controls']['label_count_default']))
        self.raster_row_title = tk.StringVar(value=mode_config['controls']['row_title_default'])
        
        self.raster_column_labels_enabled = tk.BooleanVar(value=True)
        self.raster_column_label_count = tk.StringVar(value=str(mode_config['controls']['label_count_default']))
        self.raster_column_title = tk.StringVar(value=mode_config['controls']['column_title_default'])
        
        # Raster Matrix selection
        raster_frame = ttk.Frame(self.file_requirements_container)
        raster_frame.pack(fill="x", pady=2)
        
        ttk.Label(raster_frame, text="Raster:").grid(row=0, column=0, sticky="w", padx=5)
        
        raster_var = tk.StringVar()
        raster_combo = ttk.Combobox(raster_frame, textvariable=raster_var, state="readonly", width=40)
        raster_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Filter for Raster_matrix* .npy files
        if hasattr(self, 'available_files'):
            raster_files = self.filter_files_by_type([".npy"], "Raster_matrix*")
            raster_combo['values'] = raster_files
        
        raster_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
        
        # Store reference
        self.file_selection_widgets['raster_matrix'] = {
            'var': raster_var,
            'combo': raster_combo,
            'frame': raster_frame,
            'config': mode_config['required_files'][0]
        }
        
        # Row Labels section
        row_labels_frame = ttk.Frame(self.file_requirements_container)
        row_labels_frame.pack(fill="x", pady=2)
        
        ttk.Label(row_labels_frame, text="Row Labels:").grid(row=0, column=0, sticky="w", padx=5)
        
        row_labels_var = tk.StringVar()
        row_labels_combo = ttk.Combobox(row_labels_frame, textvariable=row_labels_var, state="readonly", width=30)
        row_labels_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Filter for *row_labels .csv files
        if hasattr(self, 'available_files'):
            row_label_files = self.filter_files_by_type([".csv"], "*row_labels")
            row_labels_combo['values'] = row_label_files
        
        row_labels_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
        
        # Checkbox for row labels
        ttk.Checkbutton(row_labels_frame, variable=self.raster_row_labels_enabled, 
                       command=self.update_inspection_figure).grid(row=0, column=2, padx=5)
        
        # Number input for row label count
        row_count_entry = ttk.Entry(row_labels_frame, textvariable=self.raster_row_label_count, width=5)
        row_count_entry.grid(row=0, column=3, padx=2)
        row_count_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Row title input
        row_title_frame = ttk.Frame(self.file_requirements_container)
        row_title_frame.pack(fill="x", pady=2)
        ttk.Label(row_title_frame, text="Row Title:").grid(row=0, column=0, sticky="w", padx=5)
        row_title_entry = ttk.Entry(row_title_frame, textvariable=self.raster_row_title, width=20)
        row_title_entry.grid(row=0, column=1, padx=5, pady=2)
        row_title_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Store reference
        self.file_selection_widgets['row_labels'] = {
            'var': row_labels_var,
            'combo': row_labels_combo,
            'frame': row_labels_frame,
            'config': mode_config['required_files'][1]
        }
        
        # Column Labels section
        column_labels_frame = ttk.Frame(self.file_requirements_container)
        column_labels_frame.pack(fill="x", pady=2)
        
        ttk.Label(column_labels_frame, text="Column Labels:").grid(row=0, column=0, sticky="w", padx=5)
        
        column_labels_var = tk.StringVar()
        column_labels_combo = ttk.Combobox(column_labels_frame, textvariable=column_labels_var, state="readonly", width=30)
        column_labels_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Filter for *column_labels .csv files
        if hasattr(self, 'available_files'):
            column_label_files = self.filter_files_by_type([".csv"], "*column_labels")
            column_labels_combo['values'] = column_label_files
        
        column_labels_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
        
        # Checkbox for column labels
        ttk.Checkbutton(column_labels_frame, variable=self.raster_column_labels_enabled,
                       command=self.update_inspection_figure).grid(row=0, column=2, padx=5)
        
        # Number input for column label count
        column_count_entry = ttk.Entry(column_labels_frame, textvariable=self.raster_column_label_count, width=5)
        column_count_entry.grid(row=0, column=3, padx=2)
        column_count_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Column title input
        column_title_frame = ttk.Frame(self.file_requirements_container)
        column_title_frame.pack(fill="x", pady=2)
        ttk.Label(column_title_frame, text="Column Title:").grid(row=0, column=0, sticky="w", padx=5)
        column_title_entry = ttk.Entry(column_title_frame, textvariable=self.raster_column_title, width=20)
        column_title_entry.grid(row=0, column=1, padx=5, pady=2)
        column_title_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Store reference
        self.file_selection_widgets['column_labels'] = {
            'var': column_labels_var,
            'combo': column_labels_combo,
            'frame': column_labels_frame,
            'config': mode_config['required_files'][2]
        }
    
    def filter_files_by_type(self, allowed_extensions, pattern=None):
        """Filter available files by allowed extensions and optional pattern."""
        if not hasattr(self, 'available_files'):
            return []
        
        filtered_files = []
        for file_path in self.available_files:
            file_ext = os.path.splitext(file_path)[1].lower()
            filename = os.path.basename(file_path)
            
            # Check extension
            if file_ext not in allowed_extensions:
                continue
                
            # Check pattern if provided
            if pattern:
                import fnmatch
                if not fnmatch.fnmatch(filename, pattern + file_ext):
                    continue
            
            filtered_files.append(file_path)
        
        return filtered_files
    
    def on_required_file_change(self, event=None):
        """Handle changes in required file selections."""
        # Check if all required files are selected
        if self.validate_required_files():
            # Load data and update figure
            self.load_selected_files_and_display()
        else:
            # Clear figure if requirements not met
            self.clear_inspection_figure()
    
    def validate_required_files(self):
        """Validate that all required (non-optional) files are selected."""
        # For RasterPlot, only raster_matrix is required
        mode = self.inspection_mode_var.get()
        if mode == "RasterPlot":
            return 'raster_matrix' in self.file_selection_widgets and self.file_selection_widgets['raster_matrix']['var'].get()
        
        # For other modes, check all non-optional files
        for file_name, widget_info in self.file_selection_widgets.items():
            if not widget_info['config'].get('optional', False):
                if not widget_info['var'].get():
                    return False
        return True
    
    def load_selected_files_and_display(self):
        """Load all selected files and display the figure."""
        if not self.selected_dataset or not self.inspection_mode_var.get():
            return
        
        try:
            # Load all selected files
            self.selected_files = {}
            for file_name, widget_info in self.file_selection_widgets.items():
                file_path = widget_info['var'].get()
                if file_path:
                    self.selected_files[file_name] = file_path
            
            # Load the primary data file for figure generation
            if self.selected_files:
                primary_file_name = list(self.selected_files.keys())[0]
                self.selected_file = self.selected_files[primary_file_name]
                self.load_and_display_data()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load selected files: {str(e)}")
    

    
    def on_inspection_mode_select(self, event=None):
        """Handle mode selection in inspection tab."""
        mode = self.inspection_mode_var.get()
        if not mode:
            return
        
        # Create required files widgets based on mode
        self.create_required_files_widgets(mode)
        
        # Clear existing mode controls
        for widget in self.mode_controls_frame.winfo_children():
            widget.destroy()
        
        # Create mode-specific controls
        self.create_mode_controls(mode)
        
        # Clear figure until files are selected
        self.clear_inspection_figure()
    
    def create_mode_controls(self, mode):
        """Create controls specific to the selected mode."""
        if mode not in self.MODE_DEFINITIONS:
            # Show placeholder for unconfigured modes
            placeholder_frame = ttk.LabelFrame(self.mode_controls_frame, text=f"{mode} Controls", padding=5)
            placeholder_frame.pack(fill="x", pady=5)
            
            placeholder_label = ttk.Label(placeholder_frame, 
                                        text=f"Controls for '{mode}' will be implemented when the mode is configured.",
                                        font=("Arial", 10), foreground="gray")
            placeholder_label.pack(pady=10)
            return
        
        # Mode-specific controls will be implemented based on MODE_DEFINITIONS
        mode_config = self.MODE_DEFINITIONS[mode]
        self.create_custom_mode_controls(mode, mode_config)
    
    def create_custom_mode_controls(self, mode, mode_config):
        """Create controls for custom modes based on their configuration."""
        frame = ttk.LabelFrame(self.mode_controls_frame, text=f"{mode} Controls", padding=5)
        frame.pack(fill="x", pady=5)
        
        if mode == "RasterPlot":
            self.create_rasterplot_controls(frame, mode_config)
        else:
            # Placeholder for other custom modes
            placeholder_label = ttk.Label(frame, 
                                        text=f"Custom controls for '{mode}' will be implemented based on mode configuration.",
                                        font=("Arial", 10), foreground="gray")
            placeholder_label.pack(pady=10)
    
    def create_rasterplot_controls(self, parent_frame, mode_config):
        """Create RasterPlot-specific controls."""
        # Initialize colormap variable
        self.raster_colormap = tk.StringVar(value=mode_config['controls']['colormap'][0])
        
        # Colormap selection
        ttk.Label(parent_frame, text="Colormap:").grid(row=0, column=0, sticky="w", padx=5)
        colormap_combo = ttk.Combobox(parent_frame, textvariable=self.raster_colormap,
                                    values=mode_config['controls']['colormap'], state="readonly", width=15)
        colormap_combo.grid(row=0, column=1, padx=5, pady=2)
        colormap_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
    

    

    
    def load_and_display_data(self):
        """Load the selected file and display initial figure."""
        if not self.selected_file or not self.selected_dataset:
            return
        
        try:
            # Construct full file path
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            file_path = os.path.join(dataset_path, self.selected_file)
            
            # Load data based on file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                self.current_data = pd.read_csv(file_path)
            elif file_ext == '.txt':
                # Try to read as CSV first, then as plain text
                try:
                    self.current_data = pd.read_csv(file_path, sep='\t')
                except:
                    self.current_data = pd.read_csv(file_path, sep=None, engine='python')
            elif file_ext == '.npy':
                data_array = np.load(file_path)
                # Convert to DataFrame if 2D, otherwise create simple DataFrame
                if data_array.ndim == 2:
                    self.current_data = pd.DataFrame(data_array)
                else:
                    self.current_data = pd.DataFrame({'data': data_array})
            elif file_ext == '.npz':
                data_dict = np.load(file_path)
                # Use first array or combine multiple arrays
                if len(data_dict.files) == 1:
                    data_array = data_dict[data_dict.files[0]]
                    if data_array.ndim == 2:
                        self.current_data = pd.DataFrame(data_array)
                    else:
                        self.current_data = pd.DataFrame({'data': data_array})
                else:
                    # Combine multiple arrays as columns
                    data_dict_pd = {key: data_dict[key].flatten() for key in data_dict.files}
                    self.current_data = pd.DataFrame(data_dict_pd)
            else:
                messagebox.showerror("Error", f"Unsupported file format: {file_ext}")
                return
            
            # Update column selections for relevant controls
            self.update_column_controls()
            
            # Generate initial figure
            self.update_inspection_figure()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            print(f"Error loading data: {e}")
    
    def update_column_controls(self):
        """Update column-based controls when data is loaded."""
        if self.current_data is None:
            return
        
        # This method will be expanded when custom modes with column controls are implemented
        # For now, it's a placeholder that can be used by custom modes
        pass
    
    def update_inspection_figure(self):
        """Update the inspection figure based on current mode and parameters."""
        if self.current_data is None or not hasattr(self, 'inspection_ax'):
            return
        
        try:
            # Clear current plot
            self.inspection_ax.clear()
            
            mode = self.inspection_mode_var.get()
            
            # Generate figure based on mode configuration
            if mode in self.MODE_DEFINITIONS:
                self.generate_custom_mode_figure(mode)
            else:
                # Show placeholder for unconfigured modes
                self.inspection_ax.text(0.5, 0.5, f"Figure generation for '{mode}' will be implemented\nwhen the mode is configured.", 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, alpha=0.7)
            
            # Apply common formatting
            title = self.inspection_title_var.get()
            if title:
                self.inspection_ax.set_title(title)
            
            self.inspection_ax.grid(True, alpha=0.3)
            
            # Refresh canvas
            self.inspection_fig.tight_layout()
            self.figure_canvas.draw()
            
        except Exception as e:
            # Display error message on plot
            self.inspection_ax.clear()
            self.inspection_ax.text(0.5, 0.5, f'Error generating plot:\n{str(e)}', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=10, color='red')
            self.figure_canvas.draw()
            print(f"Error updating figure: {e}")
    
    def generate_custom_mode_figure(self, mode):
        """Generate figure for custom modes based on their configuration."""
        mode_config = self.MODE_DEFINITIONS[mode]
        
        if mode == "RasterPlot":
            self.generate_rasterplot_figure()
        else:
            # Placeholder for other custom modes
            self.inspection_ax.text(0.5, 0.5, f"Figure generation for '{mode}' mode\nwill be implemented based on:\n\n{mode_config.get('description', 'No description available')}", 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=12, alpha=0.7)
    
    def generate_rasterplot_figure(self):
        """Generate RasterPlot visualization."""
        try:
            # Check if raster matrix is selected
            if 'raster_matrix' not in self.file_selection_widgets or not self.file_selection_widgets['raster_matrix']['var'].get():
                self.inspection_ax.text(0.5, 0.5, 'Please select a Raster matrix file', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, alpha=0.7)
                return
            
            # Load raster matrix
            raster_file = self.file_selection_widgets['raster_matrix']['var'].get()
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            raster_path = os.path.join(dataset_path, raster_file)
            
            # Load matrix data
            raster_matrix = np.load(raster_path)
            
            # Create the plot
            colormap = self.raster_colormap.get()
            im = self.inspection_ax.imshow(raster_matrix, cmap=colormap, aspect='auto')
            
            # Set title
            dataset_name = self.selected_dataset.name
            raster_filename = os.path.basename(raster_file)
            # Extract last part after "Raster_matrix"
            title_suffix = raster_filename.replace("Raster_matrix", "").replace(".npy", "")
            if title_suffix.startswith("_"):
                title_suffix = title_suffix[1:]
            if not title_suffix:
                title_suffix = "matrix"
            
            figure_title = f"{dataset_name} {title_suffix}"
            self.inspection_ax.set_title(figure_title)
            
            # Set axis labels
            self.inspection_ax.set_xlabel(self.raster_column_title.get())
            self.inspection_ax.set_ylabel(self.raster_row_title.get())
            
            # Handle row labels
            if self.raster_row_labels_enabled.get() and 'row_labels' in self.file_selection_widgets:
                row_labels_file = self.file_selection_widgets['row_labels']['var'].get()
                if row_labels_file:
                    self.apply_axis_labels(raster_path, row_labels_file, 'row', raster_matrix.shape[0])
                else:
                    # Clear row labels if no file selected
                    self.inspection_ax.set_yticks([])
            else:
                # Clear row labels if checkbox unchecked
                self.inspection_ax.set_yticks([])
            
            # Handle column labels
            if self.raster_column_labels_enabled.get() and 'column_labels' in self.file_selection_widgets:
                column_labels_file = self.file_selection_widgets['column_labels']['var'].get()
                if column_labels_file:
                    self.apply_axis_labels(raster_path, column_labels_file, 'column', raster_matrix.shape[1])
                else:
                    # Clear column labels if no file selected
                    self.inspection_ax.set_xticks([])
            else:
                # Clear column labels if checkbox unchecked
                self.inspection_ax.set_xticks([])
            
            # Add colorbar
            if hasattr(self, 'raster_colorbar'):
                self.raster_colorbar.remove()
            self.raster_colorbar = self.inspection_fig.colorbar(im, ax=self.inspection_ax)
            
        except Exception as e:
            self.inspection_ax.text(0.5, 0.5, f'Error generating RasterPlot:\n{str(e)}', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=10, color='red')
            print(f"RasterPlot error: {e}")
    
    def apply_axis_labels(self, raster_path, labels_file, axis, axis_length):
        """Apply labels to the specified axis with equal spacing."""
        try:
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            labels_path = os.path.join(dataset_path, labels_file)
            
            # Load labels
            labels_df = pd.read_csv(labels_path)
            # Assume first column contains the labels
            labels = labels_df.iloc[:, 0].astype(str).tolist()
            
            # Get the number of labels to show
            if axis == 'row':
                try:
                    num_labels = int(self.raster_row_label_count.get())
                except ValueError:
                    num_labels = 6
            else:
                try:
                    num_labels = int(self.raster_column_label_count.get())
                except ValueError:
                    num_labels = 6
            
            # Calculate equally spaced positions
            if len(labels) > 0 and num_labels > 0:
                max_labels = min(num_labels, len(labels))
                if max_labels == 1:
                    positions = [len(labels) - 1]
                    selected_labels = [labels[-1]]
                else:
                    step = (len(labels) - 1) / (max_labels - 1)
                    positions = [int(round(i * step)) for i in range(max_labels)]
                    selected_labels = [labels[pos] for pos in positions]
                
                # Apply to appropriate axis
                if axis == 'row':
                    self.inspection_ax.set_yticks(positions)
                    self.inspection_ax.set_yticklabels(selected_labels)
                else:
                    self.inspection_ax.set_xticks(positions)
                    self.inspection_ax.set_xticklabels(selected_labels, rotation=45)
            
        except Exception as e:
            print(f"Error applying {axis} labels: {e}")
            # Clear labels on error
            if axis == 'row':
                self.inspection_ax.set_yticks([])
            else:
                self.inspection_ax.set_xticks([])
    

    

    

    

    

    
    def clear_inspection_figure(self):
        """Clear the inspection figure."""
        if hasattr(self, 'inspection_ax'):
            self.inspection_ax.clear()
            self.inspection_ax.text(0.5, 0.5, 'Select dataset, file, and mode to display figure', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=12, alpha=0.7)
            self.figure_canvas.draw()
    
    def reset_inspection_view(self):
        """Reset the inspection view to default state."""
        # Clear selections
        self.inspection_dataset_var.set("")
        self.inspection_mode_var.set("")
        self.inspection_title_var.set("")
        
        # Clear data
        self.selected_dataset = None
        self.selected_file = None
        self.selected_files = {}
        self.current_data = None
        self.available_files = []
        
        # Clear controls
        self.inspection_mode_combo['values'] = []
        
        # Clear required files section
        self.clear_required_files_section()
        
        # Clear mode controls
        for widget in self.mode_controls_frame.winfo_children():
            widget.destroy()
        
        # Clear figure
        self.clear_inspection_figure()
    
    def refresh_inspection_data(self):
        """Refresh the data and regenerate the figure."""
        if self.selected_dataset and self.inspection_mode_var.get():
            # Reload dataset files
            self.load_dataset_files()
            # Recreate required files widgets
            self.create_required_files_widgets(self.inspection_mode_var.get())
            # Clear figure
            self.clear_inspection_figure()
        else:
            messagebox.showinfo("Info", "Please select a dataset and mode first.")
    
    def save_inspection_figure(self):
        """Save the current inspection figure."""
        if not self.selected_dataset or not self.inspection_mode_var.get() or not hasattr(self, 'selected_files') or not self.selected_files:
            messagebox.showwarning("Incomplete Selection", 
                                 "Please select dataset, mode, and required files before saving.")
            return
        
        try:
            # Create mode-specific filename
            mode_name = self.inspection_mode_var.get().replace(" ", "_").lower()
            # Use first selected file for filename base
            first_file = list(self.selected_files.values())[0]
            file_base = os.path.splitext(os.path.basename(first_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"inspection_{mode_name}_{file_base}_{timestamp}.{self.inspection_format_var.get()}"
            
            # Create figures directory
            figures_dir = os.path.join("data", "datasets", self.selected_dataset.name, "figures")
            os.makedirs(figures_dir, exist_ok=True)
            filepath = os.path.join(figures_dir, filename)
            
            # Save figure
            dpi = int(self.inspection_dpi_var.get()) if self.inspection_dpi_var.get().isdigit() else 300
            self.inspection_fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
            
            # Collect parameters
            parameters = {
                "mode": self.inspection_mode_var.get(),
                "selected_files": self.selected_files,
                "timestamp": timestamp
            }
            
            # Add mode-specific parameters (will be expanded for custom modes)
            # Custom mode parameters will be collected here when modes are implemented
            
            # Create database record
            try:
                FigureOperations.create_figure(
                    figure_name=filename,
                    figure_path=filepath,
                    figure_type=f"Inspection - {self.inspection_mode_var.get()}",
                    dataset_id=self.selected_dataset.id,
                    parameters=parameters,
                    description=f"Figure inspection: {self.inspection_mode_var.get()} analysis using {len(self.selected_files)} file(s)"
                )
            except Exception as db_error:
                print(f"Database error (figure still saved): {db_error}")
            
            messagebox.showinfo("Success", f"Figure saved successfully!\nLocation: {filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save figure: {str(e)}")
    
    def create_default_plot_params(self):
        """Create default plot parameter widgets."""
        # Clear existing widgets
        for widget in self.params_container.winfo_children():
            widget.destroy()
        self.param_widgets.clear()
        
        # Default parameters
        params = [
            ("title", "Title:", "", "str"),
            ("xlabel", "X Label:", "X Axis", "str"),
            ("ylabel", "Y Label:", "Y Axis", "str"),
            ("grid", "Show Grid:", True, "bool"),
            ("legend", "Show Legend:", True, "bool"),
            ("figsize_width", "Figure Width (inches):", "10", "float"),
            ("figsize_height", "Figure Height (inches):", "6", "float")
        ]
        
        for i, (key, label, default, param_type) in enumerate(params):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(self.params_container, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=2)
            
            if param_type == "bool":
                self.param_widgets[key] = tk.BooleanVar(value=default)
                ttk.Checkbutton(self.params_container, variable=self.param_widgets[key]).grid(
                    row=row, column=col+1, sticky="w", padx=5, pady=2)
            else:
                self.param_widgets[key] = tk.StringVar(value=str(default))
                ttk.Entry(self.params_container, textvariable=self.param_widgets[key], 
                         width=20).grid(row=row, column=col+1, padx=5, pady=2)
    
    def load_datasets(self):
        """Load available datasets."""
        try:
            datasets = DatasetOperations.list_datasets()
            dataset_names = [f"{dataset.name} (ID: {dataset.id})" for dataset in datasets]
            
            self.dataset_combo['values'] = dataset_names
            self.filter_dataset_var.set("")  # Clear filter
            
            # Store dataset objects for reference
            self.dataset_objects = {f"{dataset.name} (ID: {dataset.id})": dataset 
                                   for dataset in datasets}
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load datasets: {str(e)}")
    
    def on_dataset_select(self, event=None):
        """Handle dataset selection."""
        selected = self.dataset_combo_var.get()
        if selected and selected in self.dataset_objects:
            self.selected_dataset = self.dataset_objects[selected]
            
            # Load processing jobs for this dataset
            try:
                jobs = ProcessingJobOperations.list_jobs_for_dataset(self.selected_dataset.id)
                job_names = [f"{job.job_name} (ID: {job.id})" for job in jobs if job.status == 'completed']
                job_names.insert(0, "None - Use raw data")
                
                self.job_combo['values'] = job_names
                self.job_combo_var.set("None - Use raw data")
                
                # Auto-fill figure name
                if not self.figure_name_var.get():
                    self.figure_name_var.set(f"Figure_{self.selected_dataset.name}")
                    
            except Exception as e:
                print(f"Error loading jobs: {e}")
    
    def on_figure_type_change(self, event=None):
        """Update parameters based on figure type."""
        figure_type = self.figure_type_var.get()
        
        # You could customize parameters based on figure type
        # For now, we'll keep default parameters
        
        # Auto-update figure name if it contains the old type
        current_name = self.figure_name_var.get()
        if self.selected_dataset and ("Figure_" in current_name or not current_name):
            new_name = f"{figure_type.replace(' ', '_')}_{self.selected_dataset.name}"
            self.figure_name_var.set(new_name)
    
    def preview_figure(self):
        """Preview the figure before generation."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset.")
            return
        
        if not self.figure_type_var.get():
            messagebox.showwarning("No Figure Type", "Please select a figure type.")
            return
        
        # Create preview window
        preview_window = tk.Toplevel(self.window)
        preview_window.title("Figure Preview")
        preview_window.geometry("600x500")
        
        # For now, show a placeholder
        preview_text = tk.Text(preview_window, wrap=tk.WORD)
        preview_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        preview_content = f"Figure Preview:\\n\\n"
        preview_content += f"Dataset: {self.selected_dataset.name}\\n"
        preview_content += f"Figure Type: {self.figure_type_var.get()}\\n"
        preview_content += f"Figure Name: {self.figure_name_var.get()}\\n"
        preview_content += f"Output Format: {self.output_format_var.get()}\\n"
        preview_content += f"DPI: {self.dpi_var.get()}\\n\\n"
        
        preview_content += "Parameters:\\n"
        for key, widget in self.param_widgets.items():
            if isinstance(widget, tk.BooleanVar):
                preview_content += f"  {key}: {widget.get()}\\n"
            else:
                preview_content += f"  {key}: {widget.get()}\\n"
        
        preview_content += "\\n[Actual figure preview would be displayed here]"
        
        preview_text.insert(tk.END, preview_content)
        preview_text.config(state=tk.DISABLED)
    
    def generate_figure(self):
        """Generate a single figure."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset.")
            return
        
        if not self.figure_type_var.get():
            messagebox.showwarning("No Figure Type", "Please select a figure type.")
            return
        
        figure_name = self.figure_name_var.get().strip()
        if not figure_name:
            messagebox.showwarning("No Figure Name", "Please enter a figure name.")
            return
        
        try:
            # Collect parameters
            parameters = {}
            for key, widget in self.param_widgets.items():
                if isinstance(widget, tk.BooleanVar):
                    parameters[key] = widget.get()
                else:
                    parameters[key] = widget.get()
            
            # Create output path
            output_dir = "data/figures"
            os.makedirs(output_dir, exist_ok=True)
            
            figure_filename = f"{figure_name}.{self.output_format_var.get()}"
            figure_path = os.path.join(output_dir, figure_filename)
            
            # Here you would implement the actual figure generation
            # For now, we'll create a placeholder file and database record
            
            # Create placeholder file
            with open(figure_path, 'w') as f:
                f.write(f"Placeholder for {figure_name}\\n")
                f.write(f"Dataset: {self.selected_dataset.name}\\n")
                f.write(f"Type: {self.figure_type_var.get()}\\n")
            
            # Create database record
            figure_id = FigureOperations.create_figure(
                figure_name=figure_name,
                figure_path=figure_path,
                figure_type=self.figure_type_var.get(),
                dataset_id=self.selected_dataset.id,
                parameters=parameters,
                description=f"Generated {self.figure_type_var.get()} for {self.selected_dataset.name}"
            )
            
            messagebox.showinfo("Success", f"Figure '{figure_name}' generated successfully!\\nSaved to: {figure_path}")
            
            # Refresh figures list if on browse tab
            self.load_figures()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate figure: {str(e)}")
    
    def batch_generate(self):
        """Generate figures for multiple datasets."""
        messagebox.showinfo("Coming Soon", "Batch figure generation will be implemented soon!")
    
    def load_figures(self):
        """Load all figures into the browse tree."""
        try:
            # Clear existing items
            for item in self.figures_tree.get_children():
                self.figures_tree.delete(item)
            
            # Get all datasets for reference
            datasets = {dataset.id: dataset.name for dataset in DatasetOperations.list_datasets()}
            
            # Get all figures
            all_figures_query = """
                SELECT f.*, d.name as dataset_name 
                FROM figures f
                LEFT JOIN datasets d ON f.dataset_id = d.id
                ORDER BY f.creation_date DESC
            """
            
            from src.database.connection import get_database
            db = get_database()
            results = db.execute_query(all_figures_query)
            
            for result in results:
                figure_name = result[3]  # figure_name
                dataset_name = result[-1] or f"Dataset {result[2]}"  # dataset_name or fallback
                figure_type = result[5] or "Unknown"  # figure_type
                creation_date = result[6] or ""  # creation_date
                figure_path = result[4]  # figure_path
                
                # Format creation date
                if creation_date:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(creation_date)
                        creation_date = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                self.figures_tree.insert("", "end", text=figure_name,
                                        values=(dataset_name, figure_type, creation_date, figure_path))
                
        except Exception as e:
            print(f"Error loading figures: {e}")
    
    def apply_filters(self):
        """Apply filters to the figures list."""
        # For now, just reload all figures
        # In a full implementation, you would filter based on the filter criteria
        self.load_figures()
    
    def open_figure(self):
        """Open selected figure."""
        selection = self.figures_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a figure to open.")
            return
        
        item = self.figures_tree.item(selection[0])
        figure_path = item['values'][3]  # path column
        
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(figure_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', figure_path])
            else:  # Linux
                subprocess.call(['xdg-open', figure_path])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open figure: {str(e)}")
    
    def copy_figure_path(self):
        """Copy figure path to clipboard."""
        selection = self.figures_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a figure.")
            return
        
        item = self.figures_tree.item(selection[0])
        figure_path = item['values'][3]
        
        self.window.clipboard_clear()
        self.window.clipboard_append(figure_path)
        messagebox.showinfo("Copied", f"Path copied to clipboard:\\n{figure_path}")
    
    def delete_figure(self):
        """Delete selected figure."""
        messagebox.showinfo("Coming Soon", "Figure deletion will be implemented soon!")
    
    def export_figure(self):
        """Export figure to different location/format."""
        messagebox.showinfo("Coming Soon", "Figure export will be implemented soon!")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    app = FigureGenerationGUI()
    root.mainloop()
