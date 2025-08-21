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
    
    # Mode definitions with file requirements
    EXPLORATION_MODES = {
        "Raw Data View": {
            "description": "Basic visualization of raw data",
            "plot_types": ["line", "scatter", "histogram"],
            "file_types": [".csv", ".txt", ".xlsx"],
            "required_files": [
                {"name": "data_file", "label": "Data File", "description": "Primary data file to visualize"}
            ]
        },
        "Statistical Overview": {
            "description": "Statistical summaries and distributions", 
            "plot_types": ["histogram", "box_plot", "violin_plot", "correlation_matrix"],
            "file_types": [".csv", ".txt", ".xlsx"],
            "required_files": [
                {"name": "data_file", "label": "Data File", "description": "Data file for statistical analysis"}
            ]
        },
        "Time Series Analysis": {
            "description": "Time-based data analysis",
            "plot_types": ["line", "area", "step"],
            "file_types": [".csv", ".txt", ".xlsx"],
            "required_files": [
                {"name": "time_series_file", "label": "Time Series Data", "description": "File containing time series data"}
            ]
        }
    }
    
    MATRIX_MODES = {
        "Heatmap Visualization": {
            "description": "2D heatmap representation",
            "plot_types": ["heatmap", "clustermap"],
            "file_types": [".npy", ".npz", ".csv"],
            "required_files": [
                {"name": "matrix_file", "label": "Matrix File", "description": "Matrix data file for heatmap"}
            ]
        },
        "Principal Component Analysis": {
            "description": "PCA visualization and analysis",
            "plot_types": ["scatter", "biplot", "scree_plot"],
            "file_types": [".npy", ".npz", ".csv"],
            "required_files": [
                {"name": "data_matrix", "label": "Data Matrix", "description": "Matrix file for PCA analysis"}
            ]
        },
        "Network Analysis": {
            "description": "Network/connectivity analysis",
            "plot_types": ["network_graph", "adjacency_matrix", "degree_distribution"],
            "file_types": [".npy", ".npz", ".csv"],
            "required_files": [
                {"name": "adjacency_matrix", "label": "Adjacency Matrix", "description": "Network adjacency matrix"},
                {"name": "node_labels", "label": "Node Labels (Optional)", "description": "Optional file with node labels", "optional": True}
            ]
        }
    }
    
    COMPARISON_MODES = {
        "Multi-File Comparison": {
            "description": "Compare multiple files from same dataset",
            "plot_types": ["overlay", "subplot_grid", "difference_plot"],
            "file_types": [".csv", ".npy", ".txt"],
            "required_files": [
                {"name": "primary_file", "label": "Primary File", "description": "First file for comparison"},
                {"name": "comparison_file", "label": "Comparison File", "description": "Second file for comparison"},
                {"name": "additional_files", "label": "Additional Files (Optional)", "description": "Additional files for multi-comparison", "optional": True, "multiple": True}
            ]
        },
        "Before/After Analysis": {
            "description": "Compare raw vs processed data",
            "plot_types": ["side_by_side", "overlay", "difference_heatmap"],
            "file_types": [".csv", ".npy", ".txt"],
            "required_files": [
                {"name": "raw_file", "label": "Raw Data File", "description": "Original/raw data file"},
                {"name": "processed_file", "label": "Processed Data File", "description": "Processed/modified data file"}
            ]
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
        all_modes = []
        all_modes.extend(list(self.EXPLORATION_MODES.keys()))
        all_modes.extend(list(self.MATRIX_MODES.keys()))
        all_modes.extend(list(self.COMPARISON_MODES.keys()))
        
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
        
        # Get mode configuration
        mode_config = None
        if mode in self.EXPLORATION_MODES:
            mode_config = self.EXPLORATION_MODES[mode]
        elif mode in self.MATRIX_MODES:
            mode_config = self.MATRIX_MODES[mode]
        elif mode in self.COMPARISON_MODES:
            mode_config = self.COMPARISON_MODES[mode]
        
        if not mode_config or 'required_files' not in mode_config:
            return
        
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
    
    def filter_files_by_type(self, allowed_extensions):
        """Filter available files by allowed extensions."""
        if not hasattr(self, 'available_files'):
            return []
        
        filtered_files = []
        for file_path in self.available_files:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in allowed_extensions:
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
        if mode in self.EXPLORATION_MODES:
            self.create_exploration_controls(mode)
        elif mode in self.MATRIX_MODES:
            self.create_matrix_controls(mode)
        elif mode in self.COMPARISON_MODES:
            self.create_comparison_controls(mode)
    
    def create_exploration_controls(self, mode):
        """Create controls for exploration modes."""
        frame = ttk.LabelFrame(self.mode_controls_frame, text=f"{mode} Controls", padding=5)
        frame.pack(fill="x", pady=5)
        
        if mode == "Raw Data View":
            # Plot type selection
            ttk.Label(frame, text="Plot Type:").grid(row=0, column=0, sticky="w", padx=5)
            self.plot_type_var = tk.StringVar(value="line")
            plot_combo = ttk.Combobox(frame, textvariable=self.plot_type_var,
                                    values=["line", "scatter", "histogram"], state="readonly")
            plot_combo.grid(row=0, column=1, padx=5)
            plot_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
            
            # Column selection (will be populated when data is loaded)
            ttk.Label(frame, text="Columns:").grid(row=0, column=2, sticky="w", padx=5)
            self.column_listbox = tk.Listbox(frame, selectmode='multiple', height=3, width=20)
            self.column_listbox.grid(row=0, column=3, padx=5)
            self.column_listbox.bind('<<ListboxSelect>>', lambda e: self.update_inspection_figure())
            
        elif mode == "Statistical Overview":
            # Statistics type
            ttk.Label(frame, text="Analysis:").grid(row=0, column=0, sticky="w", padx=5)
            self.stats_type_var = tk.StringVar(value="histogram")
            stats_combo = ttk.Combobox(frame, textvariable=self.stats_type_var,
                                     values=["histogram", "box_plot", "correlation_matrix"], state="readonly")
            stats_combo.grid(row=0, column=1, padx=5)
            stats_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
            
        elif mode == "Time Series Analysis":
            # Time column selection
            ttk.Label(frame, text="Time Column:").grid(row=0, column=0, sticky="w", padx=5)
            self.time_column_var = tk.StringVar()
            self.time_column_combo = ttk.Combobox(frame, textvariable=self.time_column_var, state="readonly")
            self.time_column_combo.grid(row=0, column=1, padx=5)
            self.time_column_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
            
            # Plot style
            ttk.Label(frame, text="Style:").grid(row=0, column=2, sticky="w", padx=5)
            self.ts_style_var = tk.StringVar(value="line")
            style_combo = ttk.Combobox(frame, textvariable=self.ts_style_var,
                                     values=["line", "area", "step"], state="readonly")
            style_combo.grid(row=0, column=3, padx=5)
            style_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
    
    def create_matrix_controls(self, mode):
        """Create controls for matrix analysis modes."""
        frame = ttk.LabelFrame(self.mode_controls_frame, text=f"{mode} Controls", padding=5)
        frame.pack(fill="x", pady=5)
        
        if mode == "Heatmap Visualization":
            # Colormap selection
            ttk.Label(frame, text="Colormap:").grid(row=0, column=0, sticky="w", padx=5)
            self.colormap_var = tk.StringVar(value="viridis")
            colormap_combo = ttk.Combobox(frame, textvariable=self.colormap_var,
                                        values=["viridis", "plasma", "coolwarm", "RdYlBu", "hot"], state="readonly")
            colormap_combo.grid(row=0, column=1, padx=5)
            colormap_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
            
            # Normalization
            ttk.Label(frame, text="Normalization:").grid(row=0, column=2, sticky="w", padx=5)
            self.norm_var = tk.StringVar(value="none")
            norm_combo = ttk.Combobox(frame, textvariable=self.norm_var,
                                    values=["none", "row", "column", "z-score"], state="readonly")
            norm_combo.grid(row=0, column=3, padx=5)
            norm_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
            
        elif mode == "Principal Component Analysis":
            # Number of components
            ttk.Label(frame, text="Components:").grid(row=0, column=0, sticky="w", padx=5)
            self.n_components_var = tk.StringVar(value="2")
            ttk.Entry(frame, textvariable=self.n_components_var, width=10).grid(row=0, column=1, padx=5)
            
            # Plot type
            ttk.Label(frame, text="Plot Type:").grid(row=0, column=2, sticky="w", padx=5)
            self.pca_plot_var = tk.StringVar(value="scatter")
            pca_combo = ttk.Combobox(frame, textvariable=self.pca_plot_var,
                                   values=["scatter", "biplot", "scree_plot"], state="readonly")
            pca_combo.grid(row=0, column=3, padx=5)
            pca_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
    
    def create_comparison_controls(self, mode):
        """Create controls for comparison modes."""
        frame = ttk.LabelFrame(self.mode_controls_frame, text=f"{mode} Controls", padding=5)
        frame.pack(fill="x", pady=5)
        
        # Comparison type selection
        ttk.Label(frame, text="Comparison Type:").grid(row=0, column=0, sticky="w", padx=5)
        self.comparison_type_var = tk.StringVar(value="overlay")
        comparison_combo = ttk.Combobox(frame, textvariable=self.comparison_type_var,
                                      values=["overlay", "side_by_side", "difference"], state="readonly")
        comparison_combo.grid(row=0, column=1, padx=5)
        comparison_combo.bind('<<ComboboxSelected>>', lambda e: self.update_inspection_figure())
        
        # Note about file selection
        note_label = ttk.Label(frame, text="Files are selected in the 'Required Files' section above", 
                             font=("Arial", 8), foreground="gray")
        note_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    
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
        
        columns = list(self.current_data.columns)
        
        # Update column listbox for Raw Data View
        if hasattr(self, 'column_listbox'):
            self.column_listbox.delete(0, tk.END)
            for col in columns:
                self.column_listbox.insert(tk.END, str(col))
            # Select first few columns by default
            for i in range(min(3, len(columns))):
                self.column_listbox.selection_set(i)
        
        # Update time column combo for Time Series Analysis
        if hasattr(self, 'time_column_combo'):
            self.time_column_combo['values'] = columns
            if columns:
                self.time_column_var.set(columns[0])
    
    def update_inspection_figure(self):
        """Update the inspection figure based on current mode and parameters."""
        if self.current_data is None or not hasattr(self, 'inspection_ax'):
            return
        
        try:
            # Clear current plot
            self.inspection_ax.clear()
            
            mode = self.inspection_mode_var.get()
            
            # Generate figure based on mode
            if mode == "Raw Data View":
                self.generate_raw_data_plot()
            elif mode == "Statistical Overview":
                self.generate_statistical_plot()
            elif mode == "Time Series Analysis":
                self.generate_time_series_plot()
            elif mode == "Heatmap Visualization":
                self.generate_heatmap_plot()
            elif mode == "Principal Component Analysis":
                self.generate_pca_plot()
            elif mode in self.COMPARISON_MODES:
                self.generate_comparison_plot()
            
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
    
    def generate_raw_data_plot(self):
        """Generate plot for Raw Data View mode."""
        if not hasattr(self, 'plot_type_var') or not hasattr(self, 'column_listbox'):
            return
        
        plot_type = self.plot_type_var.get()
        selected_indices = self.column_listbox.curselection()
        
        if not selected_indices:
            self.inspection_ax.text(0.5, 0.5, 'Please select columns to plot', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        selected_columns = [self.column_listbox.get(i) for i in selected_indices]
        
        if plot_type == "line":
            for col in selected_columns:
                if col in self.current_data.columns:
                    self.inspection_ax.plot(self.current_data[col], label=col)
            self.inspection_ax.legend()
            self.inspection_ax.set_ylabel("Value")
            self.inspection_ax.set_xlabel("Index")
            
        elif plot_type == "scatter":
            if len(selected_columns) >= 2:
                x_col, y_col = selected_columns[0], selected_columns[1]
                self.inspection_ax.scatter(self.current_data[x_col], self.current_data[y_col])
                self.inspection_ax.set_xlabel(x_col)
                self.inspection_ax.set_ylabel(y_col)
            else:
                self.inspection_ax.text(0.5, 0.5, 'Select at least 2 columns for scatter plot', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes)
                
        elif plot_type == "histogram":
            for i, col in enumerate(selected_columns):
                if col in self.current_data.columns:
                    self.inspection_ax.hist(self.current_data[col], alpha=0.7, label=col, bins=30)
            self.inspection_ax.legend()
            self.inspection_ax.set_ylabel("Frequency")
            self.inspection_ax.set_xlabel("Value")
    
    def generate_statistical_plot(self):
        """Generate plot for Statistical Overview mode."""
        if not hasattr(self, 'stats_type_var'):
            return
        
        stats_type = self.stats_type_var.get()
        numeric_columns = self.current_data.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) == 0:
            self.inspection_ax.text(0.5, 0.5, 'No numeric columns found for statistical analysis', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        if stats_type == "histogram":
            # Plot histograms for first few numeric columns
            for i, col in enumerate(numeric_columns[:4]):  # Limit to 4 columns
                self.inspection_ax.hist(self.current_data[col], alpha=0.7, label=col, bins=30)
            self.inspection_ax.legend()
            self.inspection_ax.set_ylabel("Frequency")
            self.inspection_ax.set_xlabel("Value")
            
        elif stats_type == "box_plot":
            # Box plots for numeric columns
            data_to_plot = [self.current_data[col].dropna() for col in numeric_columns[:8]]  # Limit to 8 columns
            self.inspection_ax.boxplot(data_to_plot, labels=numeric_columns[:8])
            self.inspection_ax.set_ylabel("Value")
            plt.setp(self.inspection_ax.get_xticklabels(), rotation=45)
            
        elif stats_type == "correlation_matrix":
            # Correlation matrix heatmap
            if len(numeric_columns) > 1:
                corr_matrix = self.current_data[numeric_columns].corr()
                im = self.inspection_ax.imshow(corr_matrix, cmap='coolwarm', aspect='auto')
                self.inspection_ax.set_xticks(range(len(numeric_columns)))
                self.inspection_ax.set_yticks(range(len(numeric_columns)))
                self.inspection_ax.set_xticklabels(numeric_columns, rotation=45)
                self.inspection_ax.set_yticklabels(numeric_columns)
                
                # Add colorbar
                self.inspection_fig.colorbar(im, ax=self.inspection_ax)
            else:
                self.inspection_ax.text(0.5, 0.5, 'Need at least 2 numeric columns for correlation matrix', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes)
    
    def generate_time_series_plot(self):
        """Generate plot for Time Series Analysis mode."""
        if not hasattr(self, 'time_column_var') or not hasattr(self, 'ts_style_var'):
            return
        
        time_col = self.time_column_var.get()
        style = self.ts_style_var.get()
        
        if not time_col or time_col not in self.current_data.columns:
            self.inspection_ax.text(0.5, 0.5, 'Please select a valid time column', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        # Get numeric columns for plotting
        numeric_columns = self.current_data.select_dtypes(include=[np.number]).columns
        plot_columns = [col for col in numeric_columns if col != time_col][:3]  # Limit to 3 series
        
        if not plot_columns:
            self.inspection_ax.text(0.5, 0.5, 'No numeric columns found for time series plot', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        x_data = self.current_data[time_col]
        
        for col in plot_columns:
            y_data = self.current_data[col]
            
            if style == "line":
                self.inspection_ax.plot(x_data, y_data, label=col)
            elif style == "area":
                self.inspection_ax.fill_between(x_data, y_data, alpha=0.7, label=col)
            elif style == "step":
                self.inspection_ax.step(x_data, y_data, label=col, where='mid')
        
        self.inspection_ax.legend()
        self.inspection_ax.set_xlabel(time_col)
        self.inspection_ax.set_ylabel("Value")
    
    def generate_heatmap_plot(self):
        """Generate heatmap visualization."""
        if not hasattr(self, 'colormap_var') or not hasattr(self, 'norm_var'):
            return
        
        colormap = self.colormap_var.get()
        normalization = self.norm_var.get()
        
        # Get numeric data for heatmap
        numeric_data = self.current_data.select_dtypes(include=[np.number])
        
        if numeric_data.empty:
            self.inspection_ax.text(0.5, 0.5, 'No numeric data found for heatmap', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        # Apply normalization
        plot_data = numeric_data.copy()
        
        if normalization == "row":
            plot_data = plot_data.div(plot_data.sum(axis=1), axis=0)
        elif normalization == "column":
            plot_data = plot_data.div(plot_data.sum(axis=0), axis=1)
        elif normalization == "z-score":
            plot_data = (plot_data - plot_data.mean()) / plot_data.std()
        
        # Create heatmap
        im = self.inspection_ax.imshow(plot_data.T, cmap=colormap, aspect='auto')
        
        # Set labels if data is not too large
        if plot_data.shape[1] <= 20:
            self.inspection_ax.set_yticks(range(len(plot_data.columns)))
            self.inspection_ax.set_yticklabels(plot_data.columns)
        
        if plot_data.shape[0] <= 50:
            self.inspection_ax.set_xticks(range(0, len(plot_data), max(1, len(plot_data)//10)))
        
        # Add colorbar
        self.inspection_fig.colorbar(im, ax=self.inspection_ax)
    
    def generate_pca_plot(self):
        """Generate PCA visualization."""
        try:
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            self.inspection_ax.text(0.5, 0.5, 'scikit-learn is required for PCA analysis', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        if not hasattr(self, 'n_components_var') or not hasattr(self, 'pca_plot_var'):
            return
        
        try:
            n_components = int(self.n_components_var.get())
        except ValueError:
            n_components = 2
        
        plot_type = self.pca_plot_var.get()
        
        # Get numeric data
        numeric_data = self.current_data.select_dtypes(include=[np.number]).dropna()
        
        if numeric_data.empty or numeric_data.shape[1] < 2:
            self.inspection_ax.text(0.5, 0.5, 'Need at least 2 numeric columns for PCA', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_data)
        
        # Apply PCA
        pca = PCA(n_components=min(n_components, scaled_data.shape[1]))
        pca_result = pca.fit_transform(scaled_data)
        
        if plot_type == "scatter":
            if pca_result.shape[1] >= 2:
                self.inspection_ax.scatter(pca_result[:, 0], pca_result[:, 1])
                self.inspection_ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)')
                self.inspection_ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)')
            else:
                self.inspection_ax.text(0.5, 0.5, 'Need at least 2 components for scatter plot', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes)
                
        elif plot_type == "scree_plot":
            self.inspection_ax.plot(range(1, len(pca.explained_variance_ratio_) + 1), 
                                  pca.explained_variance_ratio_, 'bo-')
            self.inspection_ax.set_xlabel('Principal Component')
            self.inspection_ax.set_ylabel('Explained Variance Ratio')
            self.inspection_ax.set_title('Scree Plot')
    
    def generate_comparison_plot(self):
        """Generate comparison plots using files from Required Files section."""
        if not hasattr(self, 'selected_files') or len(self.selected_files) < 2:
            self.inspection_ax.text(0.5, 0.5, 'Please select at least 2 files in Required Files section', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            return
        
        try:
            comparison_type = getattr(self, 'comparison_type_var', tk.StringVar(value="overlay")).get()
            dataset_path = os.path.join("data", "datasets", self.selected_dataset.name)
            
            # Load all selected files
            loaded_data = {}
            for file_name, file_path in self.selected_files.items():
                full_path = os.path.join(dataset_path, file_path)
                file_ext = os.path.splitext(full_path)[1].lower()
                
                if file_ext == '.csv':
                    data = pd.read_csv(full_path)
                elif file_ext == '.npy':
                    data_array = np.load(full_path)
                    data = pd.DataFrame(data_array) if data_array.ndim == 2 else pd.DataFrame({'data': data_array})
                else:
                    continue  # Skip unsupported formats
                
                loaded_data[file_name] = data
            
            if len(loaded_data) < 2:
                self.inspection_ax.text(0.5, 0.5, 'Could not load comparison data', 
                                      ha='center', va='center', transform=self.inspection_ax.transAxes)
                return
            
            # Generate comparison plot based on type
            file_names = list(loaded_data.keys())
            
            if comparison_type == "overlay":
                # Overlay plots
                for i, (file_name, data) in enumerate(loaded_data.items()):
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        col = numeric_cols[0]
                        self.inspection_ax.plot(data[col], label=f'{file_name}: {os.path.basename(self.selected_files[file_name])}')
                
                self.inspection_ax.legend()
                self.inspection_ax.set_ylabel('Value')
                self.inspection_ax.set_xlabel('Index')
                
            elif comparison_type == "side_by_side":
                # Side by side subplots
                fig_rows = 1
                fig_cols = len(loaded_data)
                
                # Clear current axis and create subplots
                self.inspection_ax.clear()
                
                for i, (file_name, data) in enumerate(loaded_data.items()):
                    ax = self.inspection_fig.add_subplot(fig_rows, fig_cols, i+1)
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        col = numeric_cols[0]
                        ax.plot(data[col])
                        ax.set_title(f'{file_name}')
                        ax.set_ylabel('Value')
                        ax.set_xlabel('Index')
                
            elif comparison_type == "difference":
                # Difference plot
                if len(loaded_data) >= 2:
                    data1 = list(loaded_data.values())[0]
                    data2 = list(loaded_data.values())[1]
                    
                    numeric_cols1 = data1.select_dtypes(include=[np.number]).columns
                    numeric_cols2 = data2.select_dtypes(include=[np.number]).columns
                    
                    if len(numeric_cols1) > 0 and len(numeric_cols2) > 0:
                        col1, col2 = numeric_cols1[0], numeric_cols2[0]
                        
                        # Ensure same length for subtraction
                        min_len = min(len(data1[col1]), len(data2[col2]))
                        diff = data1[col1][:min_len] - data2[col2][:min_len]
                        
                        self.inspection_ax.plot(diff, label='Difference')
                        self.inspection_ax.axhline(y=0, color='k', linestyle='--', alpha=0.5)
                        self.inspection_ax.set_ylabel('Difference')
                        self.inspection_ax.set_xlabel('Index')
                        self.inspection_ax.legend()
        
        except Exception as e:
            self.inspection_ax.text(0.5, 0.5, f'Error generating comparison plot:\n{str(e)}', 
                                  ha='center', va='center', transform=self.inspection_ax.transAxes)
            print(f"Comparison plot error: {e}")
    
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
            
            # Add mode-specific parameters
            if hasattr(self, 'plot_type_var'):
                parameters["plot_type"] = self.plot_type_var.get()
            if hasattr(self, 'colormap_var'):
                parameters["colormap"] = self.colormap_var.get()
            if hasattr(self, 'norm_var'):
                parameters["normalization"] = self.norm_var.get()
            
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
