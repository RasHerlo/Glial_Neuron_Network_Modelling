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
                {"name": "column_labels", "label": "Column Labels", "description": "Column labels file (.csv)", "pattern": "*column_labels", "extension": ".csv", "optional": True},
                {"name": "annotation", "label": "Annotation", "description": "Binary vector file for annotations (.csv)", "pattern": "*", "extension": ".csv", "optional": True}
            ],
            "controls": {
                "colormap": ["binary", "jet", "viridis", "gist_earth"],
                "row_title_default": "Neurons",
                "column_title_default": "Time",
                "label_count_default": 6,
                "annotation_height_ratio": 0.035,  # 70% of original height (0.05 * 0.7)
                "annotation_enabled_default": False
            }
        },
        "TuningCurve": {
            "description": "Analyze neuron responses around stimulus events with tuning curves",
            "file_types": [".npy", ".csv"],
            "required_files": [
                {"name": "raster_matrix", "label": "Raster", "description": "Raster matrix file (.npy)", "pattern": "Raster_matrix*", "extension": ".npy"},
                {"name": "annotation", "label": "Annotation File", "description": "Binary vector indicating stimulus periods (.csv)", "pattern": "*", "extension": ".csv"}
            ],
            "controls": {
                "frames_before_default": 20,
                "frames_after_default": 200,
                "index_point_default": 0,
                "index_point_enabled_default": False,
                "convert_to_seconds_default": False,
                "framerate_default": 10.02
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
        elif mode == "TuningCurve":
            self.create_tuning_curve_file_widgets(mode_config)
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
        
        # Initialize annotation variables
        self.raster_annotation_enabled = tk.BooleanVar(value=mode_config['controls']['annotation_enabled_default'])
        self.raster_annotation_name = tk.StringVar(value="")
        
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
        
        # Annotation section
        annotation_frame = ttk.Frame(self.file_requirements_container)
        annotation_frame.pack(fill="x", pady=2)
        
        ttk.Label(annotation_frame, text="Annotation:").grid(row=0, column=0, sticky="w", padx=5)
        
        annotation_var = tk.StringVar()
        annotation_combo = ttk.Combobox(annotation_frame, textvariable=annotation_var, state="readonly", width=30)
        annotation_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Populate with binary vector files
        if hasattr(self, 'available_files'):
            binary_vector_files = self.detect_binary_vector_files()
            annotation_combo['values'] = binary_vector_files
        
        annotation_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
        
        # Checkbox for enabling annotations
        ttk.Checkbutton(annotation_frame, text="Enable", variable=self.raster_annotation_enabled,
                       command=self.update_inspection_figure).grid(row=0, column=2, padx=5)
        
        # Annotation name input (below the dropdown)
        annotation_name_frame = ttk.Frame(self.file_requirements_container)
        annotation_name_frame.pack(fill="x", pady=2)
        ttk.Label(annotation_name_frame, text="Annotation Name:").grid(row=0, column=0, sticky="w", padx=5)
        annotation_name_entry = ttk.Entry(annotation_name_frame, textvariable=self.raster_annotation_name, width=30)
        annotation_name_entry.grid(row=0, column=1, padx=5, pady=2)
        annotation_name_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Bind annotation file selection to update name field
        def on_annotation_file_change(event=None):
            selected_file = annotation_var.get()
            if selected_file and not self.raster_annotation_name.get():
                # Set default name to filename without extension
                default_name = os.path.splitext(os.path.basename(selected_file))[0]
                self.raster_annotation_name.set(default_name)
            self.on_required_file_change(event)
        
        annotation_combo.bind('<<ComboboxSelected>>', on_annotation_file_change)
        
        # Store reference
        self.file_selection_widgets['annotation'] = {
            'var': annotation_var,
            'combo': annotation_combo,
            'frame': annotation_frame,
            'config': mode_config['required_files'][3],
            'name_var': self.raster_annotation_name,
            'name_entry': annotation_name_entry
        }
    
    def create_tuning_curve_file_widgets(self, mode_config):
        """Create TuningCurve-specific file selection widgets."""
        # Initialize TuningCurve-specific variables
        self.tuning_frames_before = tk.StringVar(value=str(mode_config['controls']['frames_before_default']))
        self.tuning_frames_after = tk.StringVar(value=str(mode_config['controls']['frames_after_default']))
        self.tuning_current_neuron = tk.StringVar(value="1")
        
        # Create main container with left and right sections
        main_container = ttk.Frame(self.file_requirements_container)
        main_container.pack(fill="x", pady=5)
        
        # Left side: File selections
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Right side: Controls
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side="right", fill="y")
        
        # === LEFT SIDE: File Selections ===
        
        # Raster Matrix selection
        raster_frame = ttk.Frame(left_frame)
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
        
        # Annotation File selection
        annotation_frame = ttk.Frame(left_frame)
        annotation_frame.pack(fill="x", pady=2)
        
        ttk.Label(annotation_frame, text="Annotation File:").grid(row=0, column=0, sticky="w", padx=5)
        
        annotation_var = tk.StringVar()
        annotation_combo = ttk.Combobox(annotation_frame, textvariable=annotation_var, state="readonly", width=40)
        annotation_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Populate with binary vector files
        if hasattr(self, 'available_files'):
            binary_vector_files = self.detect_binary_vector_files()
            annotation_combo['values'] = binary_vector_files
        
        annotation_combo.bind('<<ComboboxSelected>>', self.on_required_file_change)
        
        # Store reference
        self.file_selection_widgets['annotation'] = {
            'var': annotation_var,
            'combo': annotation_combo,
            'frame': annotation_frame,
            'config': mode_config['required_files'][1]
        }
        
        # === RIGHT SIDE: Controls ===
        
        # Time Window Controls
        time_frame = ttk.LabelFrame(right_frame, text="Time Window", padding=5)
        time_frame.pack(fill="x", pady=2)
        
        ttk.Label(time_frame, text="Before:").grid(row=0, column=0, sticky="w", padx=2)
        frames_before_spinbox = ttk.Spinbox(time_frame, textvariable=self.tuning_frames_before, 
                                          from_=0, to=1000, width=6)
        frames_before_spinbox.grid(row=0, column=1, padx=2, pady=1)
        frames_before_spinbox.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        ttk.Label(time_frame, text="After:").grid(row=1, column=0, sticky="w", padx=2)
        frames_after_spinbox = ttk.Spinbox(time_frame, textvariable=self.tuning_frames_after, 
                                         from_=0, to=1000, width=6)
        frames_after_spinbox.grid(row=1, column=1, padx=2, pady=1)
        frames_after_spinbox.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Neuron Navigation Controls
        nav_frame = ttk.LabelFrame(right_frame, text="Neuron Navigation", padding=5)
        nav_frame.pack(fill="x", pady=2)
        
        ttk.Button(nav_frame, text="◀", width=3,
                  command=self.previous_neuron).grid(row=0, column=0, padx=1)
        
        neuron_spinbox = ttk.Spinbox(nav_frame, textvariable=self.tuning_current_neuron, 
                                   from_=1, to=1000, width=6)
        neuron_spinbox.grid(row=0, column=1, padx=2, pady=1)
        neuron_spinbox.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        ttk.Button(nav_frame, text="▶", width=3,
                  command=self.next_neuron).grid(row=0, column=2, padx=1)
    
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
    
    def detect_binary_vector_files(self):
        """Detect CSV files that contain binary 1D vectors (only 0s and 1s)."""
        if not hasattr(self, 'available_files') or not self.selected_dataset:
            return []
        
        binary_vector_files = []
        dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
        
        # Only check CSV files in the matrices folder
        csv_files = [f for f in self.available_files if f.endswith('.csv') and 'matrices' in f]
        
        for file_path in csv_files:
            try:
                full_path = os.path.join(dataset_path, file_path)
                
                # Skip known 2D matrix files
                filename = os.path.basename(file_path).lower()
                if 'raster_matrix' in filename and not ('row_labels' in filename or 'column_labels' in filename):
                    continue
                
                # Read the CSV file
                df = pd.read_csv(full_path)
                
                # Check if it's a single column (1D vector)
                if df.shape[1] != 1:
                    continue
                
                # Get the data column (skip header)
                data_column = df.iloc[:, 0]
                
                # Check if all values are numeric and only 0s and 1s
                try:
                    # Convert to numeric, will raise exception if non-numeric
                    numeric_data = pd.to_numeric(data_column, errors='raise')
                    
                    # Check if all values are 0 or 1
                    unique_values = set(numeric_data.dropna().unique())
                    if unique_values.issubset({0, 1, 0.0, 1.0}):
                        binary_vector_files.append(file_path)
                        
                except (ValueError, TypeError):
                    # Skip files with non-numeric data
                    continue
                    
            except Exception as e:
                # Skip files that can't be read or processed
                print(f"Error checking file {file_path}: {e}")
                continue
        
        return binary_vector_files
    
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
        mode = self.inspection_mode_var.get()
        
        # For RasterPlot, only raster_matrix is required
        if mode == "RasterPlot":
            return 'raster_matrix' in self.file_selection_widgets and self.file_selection_widgets['raster_matrix']['var'].get()
        
        # For TuningCurve, both raster_matrix and annotation are required
        elif mode == "TuningCurve":
            return ('raster_matrix' in self.file_selection_widgets and 
                    self.file_selection_widgets['raster_matrix']['var'].get() and
                    'annotation' in self.file_selection_widgets and 
                    self.file_selection_widgets['annotation']['var'].get())
        
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
        elif mode == "TuningCurve":
            self.create_tuning_curve_controls(frame, mode_config)
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
    
    def create_tuning_curve_controls(self, parent_frame, mode_config):
        """Create TuningCurve-specific controls."""
        # Initialize control variables (only for controls that remain here)
        self.tuning_index_point = tk.StringVar(value=str(mode_config['controls']['index_point_default']))
        self.tuning_index_point_enabled = tk.BooleanVar(value=mode_config['controls']['index_point_enabled_default'])
        self.tuning_convert_to_seconds = tk.BooleanVar(value=mode_config['controls']['convert_to_seconds_default'])
        self.tuning_framerate = tk.StringVar(value=str(mode_config['controls']['framerate_default']))
        
        # Index Point Controls
        index_frame = ttk.LabelFrame(parent_frame, text="Index Point", padding=5)
        index_frame.pack(fill="x", pady=5)
        
        ttk.Checkbutton(index_frame, text="Enable Index Point", variable=self.tuning_index_point_enabled,
                       command=self.update_inspection_figure).grid(row=0, column=0, sticky="w", padx=5)
        
        ttk.Label(index_frame, text="Offset from Stimulus:").grid(row=0, column=1, sticky="w", padx=5)
        index_point_spinbox = ttk.Spinbox(index_frame, textvariable=self.tuning_index_point, 
                                        from_=-1000, to=1000, width=8)
        index_point_spinbox.grid(row=0, column=2, padx=5, pady=2)
        index_point_spinbox.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
        
        # Time Conversion Controls
        time_conv_frame = ttk.LabelFrame(parent_frame, text="Time Conversion", padding=5)
        time_conv_frame.pack(fill="x", pady=5)
        
        ttk.Checkbutton(time_conv_frame, text="Convert to Seconds", variable=self.tuning_convert_to_seconds,
                       command=self.update_inspection_figure).grid(row=0, column=0, sticky="w", padx=5)
        
        ttk.Label(time_conv_frame, text="Frame Rate (Hz):").grid(row=0, column=1, sticky="w", padx=5)
        framerate_entry = ttk.Entry(time_conv_frame, textvariable=self.tuning_framerate, width=10)
        framerate_entry.grid(row=0, column=2, padx=5, pady=2)
        framerate_entry.bind('<KeyRelease>', lambda e: self.update_inspection_figure())
    
    def previous_neuron(self):
        """Navigate to previous neuron."""
        try:
            current = int(self.tuning_current_neuron.get())
            if current > 1:
                self.tuning_current_neuron.set(str(current - 1))
                self.update_inspection_figure()
        except ValueError:
            pass
    
    def next_neuron(self):
        """Navigate to next neuron."""
        try:
            current = int(self.tuning_current_neuron.get())
            # Get maximum neuron count from raster data if available
            max_neurons = self.get_max_neurons()
            if current < max_neurons:
                self.tuning_current_neuron.set(str(current + 1))
                self.update_inspection_figure()
        except ValueError:
            pass
    
    def get_max_neurons(self):
        """Get the maximum number of neurons from the current raster data."""
        if hasattr(self, 'current_raster_data') and self.current_raster_data is not None:
            return self.current_raster_data.shape[0]
        return 1000  # Default fallback
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
        elif mode == "TuningCurve":
            self.generate_tuning_curve_figure()
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
            
            # Check if annotation is enabled and available
            show_annotation = (self.raster_annotation_enabled.get() and 
                             'annotation' in self.file_selection_widgets and 
                             self.file_selection_widgets['annotation']['var'].get())
            
            annotation_data = None
            if show_annotation:
                try:
                    annotation_file = self.file_selection_widgets['annotation']['var'].get()
                    annotation_path = os.path.join(dataset_path, annotation_file)
                    annotation_df = pd.read_csv(annotation_path)
                    annotation_data = annotation_df.iloc[:, 0].values  # Get first column as numpy array
                    
                    # Ensure annotation data matches matrix width
                    if len(annotation_data) != raster_matrix.shape[1]:
                        print(f"Warning: Annotation length ({len(annotation_data)}) doesn't match matrix width ({raster_matrix.shape[1]})")
                        # Resize annotation data to match matrix width
                        if len(annotation_data) > raster_matrix.shape[1]:
                            annotation_data = annotation_data[:raster_matrix.shape[1]]
                        else:
                            # Pad with zeros if annotation is shorter
                            padded_data = np.zeros(raster_matrix.shape[1])
                            padded_data[:len(annotation_data)] = annotation_data
                            annotation_data = padded_data
                            
                except Exception as e:
                    print(f"Error loading annotation data: {e}")
                    show_annotation = False
                    annotation_data = None
            
            # Clear the figure and create new subplots if needed
            self.inspection_fig.clear()
            
            if show_annotation and annotation_data is not None:
                # Create subplots with annotation
                height_ratios = [self.MODE_DEFINITIONS["RasterPlot"]["controls"]["annotation_height_ratio"], 1.0]
                gs = self.inspection_fig.add_gridspec(2, 1, height_ratios=height_ratios, hspace=0.02)
                
                # Annotation subplot (top)
                annotation_ax = self.inspection_fig.add_subplot(gs[0])
                annotation_name = self.raster_annotation_name.get() or os.path.splitext(os.path.basename(annotation_file))[0]
                self.render_annotation(annotation_ax, annotation_data, annotation_name)
                
                # Main raster plot subplot (bottom)
                self.inspection_ax = self.inspection_fig.add_subplot(gs[1])
            else:
                # Single subplot for raster plot only
                self.inspection_ax = self.inspection_fig.add_subplot(111)
            
            # Create the main raster plot
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
            
            # Set title on the figure or the top subplot
            if show_annotation and annotation_data is not None:
                # Move title higher when annotation is present to avoid overlap
                self.inspection_fig.suptitle(figure_title, fontsize=12, y=0.98)
            else:
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
            
            # Remove any existing colorbar
            if hasattr(self, 'raster_colorbar') and self.raster_colorbar is not None:
                try:
                    self.raster_colorbar.remove()
                except (ValueError, AttributeError):
                    # Colorbar might already be removed or invalid
                    pass
                self.raster_colorbar = None
            
        except Exception as e:
            self.inspection_ax.text(0.5, 0.5, f'Error generating RasterPlot:\n{str(e)}', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=10, color='red')
            print(f"RasterPlot error: {e}")
    
    def generate_tuning_curve_figure(self):
        """Generate Tuning Curve visualization."""
        try:
            # Check if required files are selected
            if ('raster_matrix' not in self.file_selection_widgets or 
                not self.file_selection_widgets['raster_matrix']['var'].get() or
                'annotation' not in self.file_selection_widgets or
                not self.file_selection_widgets['annotation']['var'].get()):
                
                self.inspection_ax.text(0.5, 0.5, 'Please select both Raster matrix and Annotation files', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, alpha=0.7)
                return
            
            # Load raster matrix
            raster_file = self.file_selection_widgets['raster_matrix']['var'].get()
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            raster_path = os.path.join(dataset_path, raster_file)
            raster_matrix = np.load(raster_path)
            self.current_raster_data = raster_matrix  # Store for navigation
            
            # Load annotation data
            annotation_file = self.file_selection_widgets['annotation']['var'].get()
            annotation_path = os.path.join(dataset_path, annotation_file)
            annotation_df = pd.read_csv(annotation_path)
            annotation_data = annotation_df.iloc[:, 0].values
            
            # Get parameters
            frames_before = int(self.tuning_frames_before.get())
            frames_after = int(self.tuning_frames_after.get())
            current_neuron_idx = int(self.tuning_current_neuron.get()) - 1  # Convert to 0-based index
            
            # Validate neuron index
            if current_neuron_idx < 0 or current_neuron_idx >= raster_matrix.shape[0]:
                self.inspection_ax.text(0.5, 0.5, f'Invalid neuron index. Please select between 1 and {raster_matrix.shape[0]}', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, color='red')
                return
            
            # Detect stimulus starts (0->1 transitions)
            stimulus_starts = self.detect_stimulus_starts(annotation_data)
            
            if len(stimulus_starts) == 0:
                self.inspection_ax.text(0.5, 0.5, 'No stimulus events detected in annotation file', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, color='red')
                return
            
            # Extract stimulus windows
            stimulus_windows = self.extract_stimulus_windows(raster_matrix, stimulus_starts, frames_before, frames_after)
            
            if len(stimulus_windows) == 0:
                self.inspection_ax.text(0.5, 0.5, 'No valid stimulus windows found', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes,
                                      fontsize=12, color='red')
                return
            
            # Calculate tuning curves
            single_neuron_curve, single_neuron_std = self.calculate_single_neuron_tuning_curve(
                stimulus_windows, current_neuron_idx)
            population_curve, population_std = self.calculate_population_tuning_curve(stimulus_windows)
            
            # Create time axis
            total_frames = frames_before + frames_after + 1
            time_axis = np.arange(-frames_before, frames_after + 1)
            
            # Convert to seconds if requested
            if self.tuning_convert_to_seconds.get():
                try:
                    framerate = float(self.tuning_framerate.get())
                    time_axis = time_axis / framerate
                    time_unit = "seconds"
                except ValueError:
                    time_unit = "frames"
            else:
                time_unit = "frames"
            
            # Clear figure and create subplots
            self.inspection_fig.clear()
            gs = self.inspection_fig.add_gridspec(2, 1, hspace=0.3)
            
            # Upper subplot: Single neuron
            ax_single = self.inspection_fig.add_subplot(gs[0])
            ax_single.plot(time_axis, single_neuron_curve, 'b-', linewidth=2, label=f'Neuron {current_neuron_idx + 1}')
            ax_single.fill_between(time_axis, 
                                 single_neuron_curve - single_neuron_std,
                                 single_neuron_curve + single_neuron_std,
                                 alpha=0.3, color='blue')
            ax_single.set_ylabel('Relative Activity (normalized to baseline)')
            ax_single.set_title(f'Neuron {current_neuron_idx + 1} Tuning Curve')
            ax_single.grid(True, alpha=0.3)
            
            # Add index point if enabled
            if self.tuning_index_point_enabled.get():
                try:
                    index_offset = int(self.tuning_index_point.get())
                    if self.tuning_convert_to_seconds.get():
                        index_x = index_offset / framerate
                    else:
                        index_x = index_offset
                    ax_single.axvline(x=index_x, color='red', linestyle='--', alpha=0.7, label='Index Point')
                    ax_single.legend()
                except ValueError:
                    pass
            
            # Lower subplot: Population average
            ax_pop = self.inspection_fig.add_subplot(gs[1])
            ax_pop.plot(time_axis, population_curve, 'g-', linewidth=2, label='Population Average')
            ax_pop.fill_between(time_axis, 
                               population_curve - population_std,
                               population_curve + population_std,
                               alpha=0.3, color='green')
            ax_pop.set_xlabel(f'Time relative to stimulus ({time_unit})')
            ax_pop.set_ylabel('Relative Activity (normalized to baseline)')
            ax_pop.set_title('Population Average Tuning Curve')
            ax_pop.grid(True, alpha=0.3)
            
            # Add index point if enabled
            if self.tuning_index_point_enabled.get():
                try:
                    index_offset = int(self.tuning_index_point.get())
                    if self.tuning_convert_to_seconds.get():
                        index_x = index_offset / framerate
                    else:
                        index_x = index_offset
                    ax_pop.axvline(x=index_x, color='red', linestyle='--', alpha=0.7, label='Index Point')
                    ax_pop.legend()
                except ValueError:
                    pass
            
            # Add stimulus start marker (always at 0) and baseline reference
            ax_single.axvline(x=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
            ax_single.axhline(y=1.0, color='gray', linestyle=':', alpha=0.7, linewidth=1)
            ax_pop.axvline(x=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
            ax_pop.axhline(y=1.0, color='gray', linestyle=':', alpha=0.7, linewidth=1)
            
            # Update the main inspection_ax reference for consistency
            self.inspection_ax = ax_pop
            
        except Exception as e:
            # Clear figure and show error
            self.inspection_fig.clear()
            self.inspection_ax = self.inspection_fig.add_subplot(111)
            self.inspection_ax.text(0.5, 0.5, f'Error generating Tuning Curve:\n{str(e)}', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes,
                                  fontsize=10, color='red')
            print(f"TuningCurve error: {e}")
    
    def detect_stimulus_starts(self, annotation_data):
        """Detect stimulus start points as 0->1 transitions."""
        stimulus_starts = []
        for i in range(1, len(annotation_data)):
            if annotation_data[i-1] == 0 and annotation_data[i] == 1:
                stimulus_starts.append(i)
        return stimulus_starts
    
    def extract_stimulus_windows(self, raster_matrix, stimulus_starts, frames_before, frames_after):
        """Extract time windows around stimulus events."""
        stimulus_windows = []
        
        for start_idx in stimulus_starts:
            # Calculate window boundaries
            window_start = start_idx - frames_before
            window_end = start_idx + frames_after + 1
            
            # Check if window is within bounds
            if window_start >= 0 and window_end <= raster_matrix.shape[1]:
                window_data = raster_matrix[:, window_start:window_end]
                stimulus_windows.append(window_data)
        
        return stimulus_windows
    
    def calculate_single_neuron_tuning_curve(self, stimulus_windows, neuron_idx):
        """Calculate mean and std for a single neuron across all stimulus windows."""
        if len(stimulus_windows) == 0:
            return np.array([]), np.array([])
        
        # Extract neuron data from all windows
        neuron_traces = []
        for window in stimulus_windows:
            neuron_traces.append(window[neuron_idx, :])
        
        # Convert to numpy array and calculate statistics
        neuron_traces = np.array(neuron_traces)
        mean_trace = np.mean(neuron_traces, axis=0)
        std_trace = np.std(neuron_traces, axis=0)
        
        # Normalize to baseline (average of last 20 frames before stimulus)
        # Get baseline frames (frames before stimulus start)
        frames_before = int(self.tuning_frames_before.get())
        
        # Calculate baseline as the average of the last 20 frames before stimulus
        # (or all available frames if less than 20)
        baseline_frames = min(20, frames_before)
        if baseline_frames > 0:
            # Baseline is from (frames_before - baseline_frames) to frames_before
            baseline_start = max(0, frames_before - baseline_frames)
            baseline_end = frames_before
            baseline_mean = np.mean(mean_trace[baseline_start:baseline_end])
            
            # Avoid division by zero
            if baseline_mean > 0:
                normalized_mean_trace = mean_trace / baseline_mean
                normalized_std_trace = std_trace / baseline_mean
            else:
                # If baseline is zero, add small epsilon to avoid division by zero
                baseline_mean = baseline_mean + 1e-10
                normalized_mean_trace = mean_trace / baseline_mean
                normalized_std_trace = std_trace / baseline_mean
        else:
            # If no baseline frames available, return unnormalized
            normalized_mean_trace = mean_trace
            normalized_std_trace = std_trace
        
        return normalized_mean_trace, normalized_std_trace
    
    def calculate_population_tuning_curve(self, stimulus_windows):
        """Calculate weighted population average across all neurons."""
        if len(stimulus_windows) == 0:
            return np.array([]), np.array([])
        
        # Get dimensions
        n_neurons = stimulus_windows[0].shape[0]
        window_length = stimulus_windows[0].shape[1]
        
        # Calculate individual neuron curves
        all_means = []
        all_stds = []
        
        for neuron_idx in range(n_neurons):
            mean_trace, std_trace = self.calculate_single_neuron_tuning_curve(stimulus_windows, neuron_idx)
            all_means.append(mean_trace)
            all_stds.append(std_trace)
        
        all_means = np.array(all_means)
        all_stds = np.array(all_stds)
        
        # Calculate weighted average (weight = 1/std, avoid division by zero)
        weights = np.where(all_stds > 0, 1.0 / all_stds, 0)
        
        # Normalize weights for each time point
        weight_sums = np.sum(weights, axis=0)
        weight_sums = np.where(weight_sums > 0, weight_sums, 1)  # Avoid division by zero
        
        # Calculate weighted mean
        weighted_mean = np.sum(all_means * weights, axis=0) / weight_sums
        
        # Calculate combined standard deviation
        # Using weighted standard deviation formula
        weighted_variance = np.sum(weights * (all_means - weighted_mean)**2, axis=0) / weight_sums
        combined_std = np.sqrt(weighted_variance)
        
        return weighted_mean, combined_std
    
    def render_annotation(self, annotation_ax, annotation_data, annotation_name):
        """Render the annotation bar above the raster plot."""
        try:
            # Create a 2D array for visualization (single row)
            annotation_2d = annotation_data.reshape(1, -1)
            
            # Create custom colormap: 0=white, 1=black
            from matplotlib.colors import ListedColormap
            colors = ['white', 'black']
            annotation_cmap = ListedColormap(colors)
            
            # Display the annotation as an image
            annotation_ax.imshow(annotation_2d, cmap=annotation_cmap, aspect='auto', vmin=0, vmax=1)
            
            # Remove ticks and labels from annotation subplot
            annotation_ax.set_xticks([])
            annotation_ax.set_yticks([])
            
            # Add custom annotation name on the left side in small font
            annotation_ax.text(-0.02, 0.5, annotation_name, transform=annotation_ax.transAxes, 
                             fontsize=8, ha='right', va='center', rotation=0)
            
            # Remove spines except bottom to connect with main plot
            annotation_ax.spines['top'].set_visible(False)
            annotation_ax.spines['left'].set_visible(False)
            annotation_ax.spines['right'].set_visible(False)
            annotation_ax.spines['bottom'].set_visible(True)
            
        except Exception as e:
            print(f"Error rendering annotation: {e}")
            # Show error text in annotation area
            annotation_ax.text(0.5, 0.5, f'Error: {str(e)}', 
                             ha='center', va='center', transform=annotation_ax.transAxes,
                             fontsize=8, color='red')
    
    def apply_axis_labels(self, raster_path, labels_file, axis, axis_length):
        """Apply labels to the specified axis with equal spacing."""
        try:
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            labels_path = os.path.join(dataset_path, labels_file)
            
            # Load labels
            labels_df = pd.read_csv(labels_path)
            # Assume first column contains the labels
            # Format numeric labels by rounding to integers, keep non-numeric as strings
            raw_labels = labels_df.iloc[:, 0]
            labels = []
            for label in raw_labels:
                try:
                    # Try to convert to float first
                    float_val = float(label)
                    # Round to nearest integer for display
                    labels.append(str(int(round(float_val))))
                except (ValueError, TypeError):
                    # If conversion fails, keep as string (strip whitespace)
                    labels.append(str(label).strip())
            
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
