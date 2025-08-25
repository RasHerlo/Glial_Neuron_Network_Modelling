"""
Data Processing GUI - Interface for processing datasets.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
import threading
import time
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, ProcessingJobOperations


class DataProcessingGUI:
    """GUI for data processing functionality."""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Data Processing")
        self.window.geometry("800x1000")
        self.window.configure(bg='#f0f0f0')
        
        self.selected_dataset = None
        self.setup_ui()
        self.load_datasets()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = ttk.Label(self.window, text="Data Processing", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Dataset selection frame
        dataset_frame = ttk.LabelFrame(self.window, text="Dataset Selection", padding=10)
        dataset_frame.pack(fill="x", padx=20, pady=5)
        
        # Dataset listbox
        list_frame = ttk.Frame(dataset_frame)
        list_frame.pack(fill="both", expand=True)
        
        ttk.Label(list_frame, text="Available Datasets:").pack(anchor="w")
        
        datasets_list_frame = ttk.Frame(list_frame)
        datasets_list_frame.pack(fill="both", expand=True, pady=5)
        
        self.datasets_listbox = tk.Listbox(datasets_list_frame, height=6)
        self.datasets_listbox.pack(side="left", fill="both", expand=True)
        self.datasets_listbox.bind('<<ListboxSelect>>', self.on_dataset_select)
        
        datasets_scrollbar = ttk.Scrollbar(datasets_list_frame, orient="vertical")
        datasets_scrollbar.pack(side="right", fill="y")
        
        self.datasets_listbox.config(yscrollcommand=datasets_scrollbar.set)
        datasets_scrollbar.config(command=self.datasets_listbox.yview)
        
        # Dataset info
        self.dataset_info_var = tk.StringVar(value="Select a dataset to view information")
        ttk.Label(dataset_frame, textvariable=self.dataset_info_var, 
                 font=("Arial", 9)).pack(anchor="w", pady=5)
        
        # Processing options frame
        processing_frame = ttk.LabelFrame(self.window, text="Processing Options", padding=10)
        processing_frame.pack(fill="x", padx=20, pady=5)
        
        # Processing type
        ttk.Label(processing_frame, text="Processing Type:").grid(row=0, column=0, sticky="w", padx=5)
        self.processing_type_var = tk.StringVar()
        
        # Get available processors dynamically
        from src.data_processing.processors import DataProcessingManager
        manager = DataProcessingManager()
        available_processors = manager.get_available_processors()
        
        self.processing_combo = ttk.Combobox(processing_frame, textvariable=self.processing_type_var,
                                           values=available_processors, 
                                           state="readonly", width=30)
        self.processing_combo.grid(row=0, column=1, padx=5, pady=2)
        self.processing_combo.bind('<<ComboboxSelected>>', self.on_processing_type_change)
        
        # Set default to Matrix Extraction to maintain backward compatibility
        if "Matrix Extraction" in available_processors:
            self.processing_type_var.set("Matrix Extraction")
        
        # Parameters frame
        params_frame = ttk.LabelFrame(processing_frame, text="Parameters", padding=5)
        params_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Dynamic parameters based on processing type
        self.params_frame = ttk.Frame(params_frame)
        self.params_frame.pack(fill="both", expand=True)
        
        self.param_vars = {}
        self.create_matrix_extraction_params()  # Default to Matrix Extraction parameters
        
        # Active jobs frame
        jobs_frame = ttk.LabelFrame(self.window, text="Active Jobs", padding=10)
        jobs_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Jobs treeview
        self.jobs_tree = ttk.Treeview(jobs_frame, columns=("dataset", "type", "status", "progress"), 
                                     show="tree headings", height=8)
        self.jobs_tree.pack(side="left", fill="both", expand=True)
        
        # Tree headings
        self.jobs_tree.heading("#0", text="Job Name")
        self.jobs_tree.heading("dataset", text="Dataset")
        self.jobs_tree.heading("type", text="Type")
        self.jobs_tree.heading("status", text="Status")
        self.jobs_tree.heading("progress", text="Progress")
        
        # Tree columns width
        self.jobs_tree.column("#0", width=150)
        self.jobs_tree.column("dataset", width=120)
        self.jobs_tree.column("type", width=100)
        self.jobs_tree.column("status", width=80)
        self.jobs_tree.column("progress", width=80)
        
        jobs_scrollbar = ttk.Scrollbar(jobs_frame, orient="vertical")
        jobs_scrollbar.pack(side="right", fill="y")
        
        self.jobs_tree.config(yscrollcommand=jobs_scrollbar.set)
        jobs_scrollbar.config(command=self.jobs_tree.yview)
        
        # Action buttons frame
        action_frame = ttk.Frame(self.window)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        self.preview_button = ttk.Button(action_frame, text="Preview Matrix", 
                  command=self.preview_matrix)
        self.preview_button.pack(side="left", padx=5)
        ttk.Button(action_frame, text="Start Processing", 
                  command=self.start_processing).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Refresh Jobs", 
                  command=self.refresh_jobs).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Cancel Selected Job", 
                  command=self.cancel_job).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Remove Finished Job", 
                  command=self.remove_finished_job).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Close", 
                  command=self.window.destroy).pack(side="right", padx=5)
        
        # Start job refresh timer
        self.refresh_jobs()
        self.schedule_job_refresh()
    
    def create_matrix_extraction_params(self):
        """Create parameter widgets for Matrix Extraction."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Matrix Extraction parameters
        params = [
            ("matrix_name", "Matrix Name:", "extracted_matrix", "str"),
            ("matrix_range", "Matrix Range:", "B3:AJW1217", "str"),
            ("column_labels_range", "Column Labels Range:", "B1:AJW1", "str"),
            ("row_labels_range", "Row Labels Range:", "A3:A1217", "str"),
            ("transpose_matrix", "Transpose Matrix:", False, "bool"),
            ("auto_detect", "Auto-detect Ranges:", False, "bool")
        ]
        
        for i, (key, label, default, param_type) in enumerate(params):
            ttk.Label(self.params_frame, text=label).grid(row=i, column=0, sticky="w", padx=5)
            
            if param_type == "bool":
                self.param_vars[key] = tk.BooleanVar(value=default)
                ttk.Checkbutton(self.params_frame, variable=self.param_vars[key]).grid(
                    row=i, column=1, sticky="w", padx=5)
            elif param_type == "combo":
                self.param_vars[key] = tk.StringVar(value=default[0] if isinstance(default, list) else default)
                combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars[key],
                                   values=default if isinstance(default, list) else [default],
                                   state="readonly", width=18)
                combo.grid(row=i, column=1, padx=5)
            else:
                self.param_vars[key] = tk.StringVar(value=str(default))
                ttk.Entry(self.params_frame, textvariable=self.param_vars[key], 
                         width=20).grid(row=i, column=1, padx=5)
    
    def create_matrix_modification_params(self):
        """Create parameter widgets for Matrix Modification."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Matrix dropdown (will be populated based on selected dataset)
        ttk.Label(self.params_frame, text="Matrix:").grid(row=0, column=0, sticky="w", padx=5)
        self.param_vars['matrix'] = tk.StringVar()
        self.matrix_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['matrix'],
                                        values=[], state="readonly", width=20)
        self.matrix_combo.grid(row=0, column=1, padx=5)
        self.matrix_combo.bind('<<ComboboxSelected>>', self.on_matrix_selection_change)
        
        # Operation dropdown
        ttk.Label(self.params_frame, text="Operation:").grid(row=1, column=0, sticky="w", padx=5)
        self.param_vars['operation'] = tk.StringVar(value='Z-scoring')
        operation_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['operation'],
                                      values=['Z-scoring', '[0,1] normalization'], 
                                      state="readonly", width=20)
        operation_combo.grid(row=1, column=1, padx=5)
        operation_combo.bind('<<ComboboxSelected>>', self.on_operation_change)
        
        # Output filename
        ttk.Label(self.params_frame, text="Output Filename:").grid(row=2, column=0, sticky="w", padx=5)
        self.param_vars['output_filename'] = tk.StringVar()
        ttk.Entry(self.params_frame, textvariable=self.param_vars['output_filename'], 
                 width=20).grid(row=2, column=1, padx=5)
        
        # File format dropdown
        ttk.Label(self.params_frame, text="File Format:").grid(row=3, column=0, sticky="w", padx=5)
        self.param_vars['fileformat'] = tk.StringVar(value='.npy')
        format_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['fileformat'],
                                   values=['.npy', '.csv'], state="readonly", width=20)
        format_combo.grid(row=3, column=1, padx=5)
        
        # Update matrix dropdown based on currently selected dataset
        self.update_matrix_dropdown()
    
    def update_matrix_dropdown(self):
        """Update matrix dropdown based on selected dataset."""
        if not self.selected_dataset:
            self.matrix_combo['values'] = []
            return
        
        # Get available matrices for the selected dataset
        from src.data_processing.processors import DataProcessingManager
        manager = DataProcessingManager()
        matrix_processor = manager.get_processor("Matrix Modification")
        
        if matrix_processor:
            available_matrices = matrix_processor.find_matrix_files(self.selected_dataset.name)
            self.matrix_combo['values'] = available_matrices
            
            # Clear current selection if no matrices available
            if not available_matrices:
                self.param_vars['matrix'].set('')
            elif len(available_matrices) == 1:
                # Auto-select if only one matrix available
                self.param_vars['matrix'].set(available_matrices[0])
                self.on_matrix_selection_change()
    
    def on_matrix_selection_change(self, event=None):
        """Handle matrix selection change - update output filename."""
        self.update_output_filename()
    
    def on_operation_change(self, event=None):
        """Handle operation change - update output filename."""
        self.update_output_filename()
    
    def update_output_filename(self):
        """Update output filename based on selected matrix and operation."""
        matrix_name = self.param_vars['matrix'].get()
        operation = self.param_vars['operation'].get()
        
        if matrix_name and operation:
            # Generate suggested filename
            from src.data_processing.processors import DataProcessingManager
            manager = DataProcessingManager()
            matrix_processor = manager.get_processor("Matrix Modification")
            
            if matrix_processor:
                suggested_name = matrix_processor.generate_output_filename(matrix_name, operation)
                self.param_vars['output_filename'].set(suggested_name)
    
    def create_data_annotation_params(self):
        """Create parameter widgets for Data Annotation."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Create main container with two columns
        main_frame = ttk.Frame(self.params_frame)
        main_frame.pack(fill="both", expand=True)
        
        # Left side - Required Files parameters
        left_frame = ttk.LabelFrame(main_frame, text="Required Files", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Right side - Stimulation Periods
        right_frame = ttk.LabelFrame(main_frame, text="Stimulation Periods (sec)", padding=5)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Left side parameters
        # Annotation Name
        ttk.Label(left_frame, text="Annotation Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['annotation_name'] = tk.StringVar(value='annotation_vector')
        ttk.Entry(left_frame, textvariable=self.param_vars['annotation_name'], 
                 width=20).grid(row=0, column=1, padx=5, pady=2)
        
        # Vector Dimension
        ttk.Label(left_frame, text="Vector Dimension:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['vector_dimension'] = tk.StringVar()
        self.dimension_combo = ttk.Combobox(left_frame, textvariable=self.param_vars['vector_dimension'],
                                          values=[], state="readonly", width=18)
        self.dimension_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # FrameRate
        ttk.Label(left_frame, text="FrameRate (fr/s):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['framerate'] = tk.StringVar(value='10.02')
        ttk.Entry(left_frame, textvariable=self.param_vars['framerate'], 
                 width=20).grid(row=2, column=1, padx=5, pady=2)
        
        # Right side - Stimulation Periods
        # Container for periods with scrollbar
        periods_container = ttk.Frame(right_frame)
        periods_container.pack(fill="both", expand=True)
        
        # Scrollable frame for periods
        canvas = tk.Canvas(periods_container, height=200)
        scrollbar = ttk.Scrollbar(periods_container, orient="vertical", command=canvas.yview)
        self.periods_scrollable_frame = ttk.Frame(canvas)
        
        self.periods_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.periods_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for later updates
        self.periods_canvas = canvas
        
        # Initialize periods list and variables
        self.stimulation_periods = []
        self.period_vars = []
        
        # Add initial 5 periods
        for i in range(5):
            self.add_stimulation_period()
        
        # Add/Remove buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Add Period", 
                  command=self.add_stimulation_period).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Remove Period", 
                  command=self.remove_stimulation_period).pack(side="left", padx=2)
        
        # Update dimension dropdown based on currently selected dataset
        self.update_dimension_dropdown()
    
    def add_stimulation_period(self):
        """Add a new stimulation period input row."""
        period_index = len(self.stimulation_periods)
        
        # Create frame for this period
        period_frame = ttk.Frame(self.periods_scrollable_frame)
        period_frame.pack(fill="x", pady=2)
        
        # Period label
        ttk.Label(period_frame, text=f"Period {period_index + 1}:").pack(side="left", padx=5)
        
        # Start time
        ttk.Label(period_frame, text="start:").pack(side="left", padx=2)
        start_var = tk.StringVar()
        start_entry = ttk.Entry(period_frame, textvariable=start_var, width=8)
        start_entry.pack(side="left", padx=2)
        
        # End time
        ttk.Label(period_frame, text="end:").pack(side="left", padx=2)
        end_var = tk.StringVar()
        end_entry = ttk.Entry(period_frame, textvariable=end_var, width=8)
        end_entry.pack(side="left", padx=2)
        
        # Store period data
        period_data = {
            'frame': period_frame,
            'start_var': start_var,
            'end_var': end_var,
            'start_entry': start_entry,
            'end_entry': end_entry
        }
        
        self.stimulation_periods.append(period_data)
        self.period_vars.extend([start_var, end_var])
        
        # Update canvas scroll region
        self.periods_scrollable_frame.update_idletasks()
        self.periods_canvas.configure(scrollregion=self.periods_canvas.bbox("all"))
    
    def remove_stimulation_period(self):
        """Remove the last stimulation period input row."""
        if len(self.stimulation_periods) <= 1:
            return  # Keep at least one period
        
        # Remove the last period
        last_period = self.stimulation_periods.pop()
        
        # Remove from period_vars
        self.period_vars.remove(last_period['start_var'])
        self.period_vars.remove(last_period['end_var'])
        
        # Destroy the frame
        last_period['frame'].destroy()
        
        # Update canvas scroll region
        self.periods_scrollable_frame.update_idletasks()
        self.periods_canvas.configure(scrollregion=self.periods_canvas.bbox("all"))
    
    def update_dimension_dropdown(self):
        """Update dimension dropdown based on selected dataset."""
        if not self.selected_dataset:
            self.dimension_combo['values'] = []
            return
        
        # Get available matrix dimensions for the selected dataset
        from src.data_processing.processors import DataProcessingManager
        manager = DataProcessingManager()
        annotation_processor = manager.get_processor("Data Annotation")
        
        if annotation_processor:
            try:
                matrix_dimensions = annotation_processor.find_matrix_files(self.selected_dataset.name)
                
                dimension_options = []
                if matrix_dimensions:
                    # Use actual matrix dimensions
                    first_shape = next(iter(matrix_dimensions.values()))
                    rows, cols = first_shape
                    dimension_options = [f"rows = {rows}", f"columns = {cols}"]
                else:
                    # Fallback dimensions
                    dimension_options = ["rows = 1215", "columns = 1000"]
                
                self.dimension_combo['values'] = dimension_options
                
                # Auto-select first option if available
                if dimension_options:
                    self.param_vars['vector_dimension'].set(dimension_options[0])
                    
            except Exception as e:
                print(f"Error updating dimension dropdown: {e}")
                self.dimension_combo['values'] = ["rows = 1215", "columns = 1000"]
    
    def create_indexing_params(self):
        """Create parameter widgets for Indexing."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Create main container with two columns
        main_frame = ttk.Frame(self.params_frame)
        main_frame.pack(fill="both", expand=True)
        
        # Left side - Main parameters
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Right side - Column Name
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Left side parameters
        # Indexing Type
        ttk.Label(left_frame, text="Indexing Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['indexing_type'] = tk.StringVar(value='Row Indexing')
        indexing_combo = ttk.Combobox(left_frame, textvariable=self.param_vars['indexing_type'],
                                    values=['Row Indexing', 'Column Indexing'], 
                                    state="readonly", width=18)
        indexing_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # File Selection
        ttk.Label(left_frame, text="Select CSV File:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        file_frame = ttk.Frame(left_frame)
        file_frame.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        self.param_vars['selected_file'] = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.param_vars['selected_file'], 
                                   width=25, state="readonly")
        self.file_entry.pack(side="left", fill="x", expand=True)
        
        ttk.Button(file_frame, text="Browse...", 
                  command=self.browse_csv_file, width=8).pack(side="right", padx=(2, 0))
        
        # Vector Selection
        ttk.Label(left_frame, text="Choose Vector:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['vector_column'] = tk.StringVar()
        self.vector_combo = ttk.Combobox(left_frame, textvariable=self.param_vars['vector_column'],
                                       values=[], state="readonly", width=18)
        self.vector_combo.grid(row=2, column=1, padx=5, pady=2)
        self.vector_combo.bind('<<ComboboxSelected>>', self.on_vector_selection_change)
        
        # Right side - Column Name
        ttk.Label(right_frame, text="Column Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.param_vars['column_name'] = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.param_vars['column_name'], 
                 width=20).grid(row=0, column=1, padx=5, pady=2)
        
        # Initialize file browser with dataset path if available
        self.update_default_browse_path()
    
    def create_ruzicka_similarity_params(self):
        """Create parameter widgets for Ruzicka Similarity."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Matrix dropdown (will be populated based on selected dataset)
        ttk.Label(self.params_frame, text="Matrix:").grid(row=0, column=0, sticky="w", padx=5)
        self.param_vars['matrix'] = tk.StringVar()
        self.ruzicka_matrix_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['matrix'],
                                                values=[], state="readonly", width=20)
        self.ruzicka_matrix_combo.grid(row=0, column=1, padx=5)
        self.ruzicka_matrix_combo.bind('<<ComboboxSelected>>', self.on_ruzicka_matrix_selection_change)
        
        # Matrix Name
        ttk.Label(self.params_frame, text="Matrix Name:").grid(row=1, column=0, sticky="w", padx=5)
        self.param_vars['matrix_name'] = tk.StringVar(value='Ruzicka Matrix')
        ttk.Entry(self.params_frame, textvariable=self.param_vars['matrix_name'], 
                 width=20).grid(row=1, column=1, padx=5)
        
        # Update matrix dropdown based on currently selected dataset
        self.update_ruzicka_matrix_dropdown()
    
    def update_ruzicka_matrix_dropdown(self):
        """Update matrix dropdown based on selected dataset for Ruzicka Similarity."""
        if not self.selected_dataset:
            self.ruzicka_matrix_combo['values'] = []
            return
        
        # Get available matrices for the selected dataset
        from src.data_processing.processors import DataProcessingManager
        manager = DataProcessingManager()
        ruzicka_processor = manager.get_processor("Ruzicka Similarity")
        
        if ruzicka_processor:
            available_matrices = ruzicka_processor.find_matrix_files(self.selected_dataset.name)
            self.ruzicka_matrix_combo['values'] = available_matrices
            
            # Clear current selection if no matrices available
            if not available_matrices:
                self.param_vars['matrix'].set('')
            elif len(available_matrices) == 1:
                # Auto-select if only one matrix available
                self.param_vars['matrix'].set(available_matrices[0])
                self.on_ruzicka_matrix_selection_change()
    
    def on_ruzicka_matrix_selection_change(self, event=None):
        """Handle matrix selection change for Ruzicka Similarity - update matrix name."""
        self.update_ruzicka_matrix_name()
    
    def update_ruzicka_matrix_name(self):
        """Update matrix name based on selected matrix for Ruzicka Similarity."""
        matrix_name = self.param_vars['matrix'].get()
        
        if matrix_name:
            # Generate suggested name with matrix suffix
            matrix_suffix = matrix_name.split('_')[-1] if '_' in matrix_name else matrix_name
            suggested_name = f"Ruzicka Matrix_{matrix_suffix}"
            self.param_vars['matrix_name'].set(suggested_name)
    
    def create_hierarchical_clustering_params(self):
        """Create parameter widgets for Hierarchical Clustering."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Matrix dropdown (will be populated based on selected dataset)
        ttk.Label(self.params_frame, text="Matrix:").grid(row=0, column=0, sticky="w", padx=5)
        self.param_vars['matrix'] = tk.StringVar()
        self.hierarchical_matrix_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['matrix'],
                                                     values=[], state="readonly", width=20)
        self.hierarchical_matrix_combo.grid(row=0, column=1, padx=5)
        self.hierarchical_matrix_combo.bind('<<ComboboxSelected>>', self.on_hierarchical_matrix_selection_change)
        
        # Clustering Method dropdown
        ttk.Label(self.params_frame, text="Clustering Method:").grid(row=1, column=0, sticky="w", padx=5)
        self.param_vars['clustering_method'] = tk.StringVar(value='ward')
        clustering_method_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['clustering_method'],
                                             values=['ward', 'complete', 'average', 'single'], 
                                             state="readonly", width=20)
        clustering_method_combo.grid(row=1, column=1, padx=5)
        
        # Distance Metric dropdown
        ttk.Label(self.params_frame, text="Distance Metric:").grid(row=2, column=0, sticky="w", padx=5)
        self.param_vars['distance_metric'] = tk.StringVar(value='euclidean')
        distance_metric_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['distance_metric'],
                                           values=['euclidean', 'correlation', 'cosine', 'manhattan'], 
                                           state="readonly", width=20)
        distance_metric_combo.grid(row=2, column=1, padx=5)
        
        # Add help label for Ward method compatibility
        ward_help_label = ttk.Label(self.params_frame, text="(Note: Ward method auto-switches to Euclidean if needed)", 
                                   font=("Arial", 8), foreground="gray")
        ward_help_label.grid(row=2, column=2, sticky="w", padx=5)
        
        # Clustering Dimension dropdown
        ttk.Label(self.params_frame, text="Clustering Dimension:").grid(row=3, column=0, sticky="w", padx=5)
        self.param_vars['clustering_dimension'] = tk.StringVar(value='Cluster Rows (Neurons)')
        clustering_dimension_combo = ttk.Combobox(self.params_frame, textvariable=self.param_vars['clustering_dimension'],
                                                 values=['Cluster Rows (Neurons)', 'Cluster Columns (Time Points)'], 
                                                 state="readonly", width=20)
        clustering_dimension_combo.grid(row=3, column=1, padx=5)
        
        # Output Name Prefix (auto-generated, read-only display)
        ttk.Label(self.params_frame, text="Output Name Prefix:").grid(row=4, column=0, sticky="w", padx=5)
        self.param_vars['output_name_prefix'] = tk.StringVar(value='HAC')
        prefix_entry = ttk.Entry(self.params_frame, textvariable=self.param_vars['output_name_prefix'], 
                                width=20, state="readonly")
        prefix_entry.grid(row=4, column=1, padx=5)
        
        # Update matrix dropdown based on currently selected dataset
        self.update_hierarchical_matrix_dropdown()
    
    def update_hierarchical_matrix_dropdown(self):
        """Update matrix dropdown based on selected dataset for Hierarchical Clustering."""
        if not self.selected_dataset:
            self.hierarchical_matrix_combo['values'] = []
            return
        
        # Get available matrices for the selected dataset
        from src.data_processing.processors import DataProcessingManager
        manager = DataProcessingManager()
        hierarchical_processor = manager.get_processor("Hierarchical Clustering")
        
        if hierarchical_processor:
            available_matrices = hierarchical_processor.find_matrix_files(self.selected_dataset.name)
            self.hierarchical_matrix_combo['values'] = available_matrices
            
            # Clear current selection if no matrices available
            if not available_matrices:
                self.param_vars['matrix'].set('')
            elif len(available_matrices) == 1:
                # Auto-select if only one matrix available
                self.param_vars['matrix'].set(available_matrices[0])
                self.on_hierarchical_matrix_selection_change()
            else:
                # Prefer normalized matrices if available
                preferred_matrices = [m for m in available_matrices if 'norm01' in m or 'zscore' in m]
                if preferred_matrices:
                    self.param_vars['matrix'].set(preferred_matrices[0])
                    self.on_hierarchical_matrix_selection_change()
    
    def on_hierarchical_matrix_selection_change(self, event=None):
        """Handle matrix selection change for Hierarchical Clustering."""
        matrix_name = self.param_vars['matrix'].get()
        if matrix_name:
            # Update output prefix to HAC + matrix suffix (e.g., HAC_norm01)
            matrix_suffix = matrix_name.split('_')[-1] if '_' in matrix_name else matrix_name
            suggested_prefix = f"HAC_{matrix_suffix}"
            self.param_vars['output_name_prefix'].set(suggested_prefix)
    
    def update_default_browse_path(self):
        """Update the default browse path based on selected dataset."""
        if hasattr(self, 'selected_dataset') and self.selected_dataset:
            self.default_browse_path = os.path.join("data", "datasets", 
                                                  self.selected_dataset.name, "processed")
        else:
            self.default_browse_path = os.path.join("data", "datasets")
    
    def browse_csv_file(self):
        """Open file browser to select CSV file."""
        # Ensure we have a valid browse path
        if not hasattr(self, 'default_browse_path'):
            self.update_default_browse_path()
        
        # Make sure the path exists
        if not os.path.exists(self.default_browse_path):
            self.default_browse_path = os.path.join("data", "datasets")
        
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            initialdir=self.default_browse_path,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            # Convert to relative path if possible
            try:
                rel_path = os.path.relpath(file_path)
                self.param_vars['selected_file'].set(rel_path)
            except ValueError:
                # If relative path conversion fails, use absolute path
                self.param_vars['selected_file'].set(file_path)
            
            # Update vector dropdown with columns from selected file
            self.update_vector_dropdown(file_path)
    
    def update_vector_dropdown(self, file_path):
        """Update vector dropdown with columns from selected CSV file."""
        try:
            # Read the CSV file to get column names
            df = pd.read_csv(file_path)
            
            # Filter for numerical columns only
            numerical_columns = []
            for col in df.columns:
                try:
                    # Try to convert column to numeric
                    pd.to_numeric(df[col], errors='raise')
                    numerical_columns.append(col)
                except (ValueError, TypeError):
                    # Skip non-numerical columns
                    continue
            
            # Update the dropdown
            self.vector_combo['values'] = numerical_columns
            
            # Clear current selection
            self.param_vars['vector_column'].set('')
            self.param_vars['column_name'].set('')
            
            if len(numerical_columns) == 1:
                # Auto-select if only one numerical column
                self.param_vars['vector_column'].set(numerical_columns[0])
                self.on_vector_selection_change()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
            self.vector_combo['values'] = []
            self.param_vars['vector_column'].set('')
            self.param_vars['column_name'].set('')
    
    def on_vector_selection_change(self, event=None):
        """Handle vector selection change - update column name."""
        selected_vector = self.param_vars['vector_column'].get()
        if selected_vector:
            # Auto-populate column name with selected vector name + "_index"
            suggested_name = f"{selected_vector}_index"
            self.param_vars['column_name'].set(suggested_name)
    
    def check_indexing_column_collision(self, indexing_type, column_name):
        """Check if column name already exists in target file and handle collision."""
        if not self.selected_dataset:
            return True
        
        # Determine target file path
        if indexing_type == 'Row Indexing':
            target_file = f"Raster_row_labels_and_indices.csv"
        else:  # Column Indexing
            target_file = f"Raster_column_labels_and_indices.csv"
        
        target_path = os.path.join("data", "datasets", self.selected_dataset.name, 
                                 "processed", "matrices", target_file)
        
        # Check if target file exists and if column already exists
        if os.path.exists(target_path):
            try:
                target_df = pd.read_csv(target_path)
                
                if column_name in target_df.columns:
                    # Column already exists - show warning dialog
                    result = messagebox.askyesnocancel(
                        "Column Already Exists",
                        f"A column named '{column_name}' already exists in {target_file}.\n\n"
                        f"Do you want to overwrite it?\n\n"
                        f"Yes: Overwrite the existing column\n"
                        f"No: Cancel and choose a different name\n"
                        f"Cancel: Cancel the operation"
                    )
                    
                    if result is True:
                        # User chose to overwrite
                        return True
                    elif result is False:
                        # User chose to change the name - focus on column name field
                        messagebox.showinfo("Choose Different Name", 
                                          f"Please choose a different column name to avoid overwriting '{column_name}'.")
                        return False
                    else:
                        # User cancelled
                        return False
                        
            except Exception as e:
                # If we can't read the file, proceed anyway
                print(f"Warning: Could not check for column collision: {e}")
                return True
        
        # No collision or file doesn't exist
        return True
    
    def on_processing_type_change(self, event=None):
        """Update parameters based on processing type."""
        processing_type = self.processing_type_var.get()
        
        if processing_type == "Matrix Extraction":
            self.create_matrix_extraction_params()
            self.preview_button.config(text="Preview Matrix")
        elif processing_type == "Matrix Modification":
            self.create_matrix_modification_params()
            self.preview_button.config(text="Preview Matrix")
        elif processing_type == "Data Annotation":
            self.create_data_annotation_params()
            self.preview_button.config(text="Preview Matrix")
        elif processing_type == "Indexing":
            self.create_indexing_params()
            self.preview_button.config(text="Preview Indexing")
        elif processing_type == "Ruzicka Similarity":
            self.create_ruzicka_similarity_params()
            self.preview_button.config(text="Preview Matrix")
        elif processing_type == "Hierarchical Clustering":
            self.create_hierarchical_clustering_params()
            self.preview_button.config(text="Preview Clustering")
        else:
            # Fallback to Matrix Extraction for unknown types
            self.create_matrix_extraction_params()
            self.preview_button.config(text="Preview Matrix")
    
    def load_datasets(self):
        """Load available datasets."""
        try:
            datasets = DatasetOperations.list_datasets()
            self.datasets_listbox.delete(0, tk.END)
            
            self.dataset_objects = {}
            for dataset in datasets:
                display_text = f"{dataset.name} ({dataset.file_format or 'unknown'})"
                self.datasets_listbox.insert(tk.END, display_text)
                self.dataset_objects[display_text] = dataset
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load datasets: {str(e)}")
    
    def on_dataset_select(self, event=None):
        """Handle dataset selection."""
        selection = self.datasets_listbox.curselection()
        if selection:
            selected_text = self.datasets_listbox.get(selection[0])
            self.selected_dataset = self.dataset_objects.get(selected_text)
            
            if self.selected_dataset:
                info_text = f"Dataset: {self.selected_dataset.name}\\n"
                info_text += f"File: {os.path.basename(self.selected_dataset.file_path)}\\n"
                info_text += f"Format: {self.selected_dataset.file_format or 'unknown'}\\n"
                info_text += f"Size: {self.selected_dataset.file_size or 'unknown'} bytes\\n"
                info_text += f"Imported: {self.selected_dataset.import_date.strftime('%Y-%m-%d %H:%M') if self.selected_dataset.import_date else 'unknown'}"
                
                self.dataset_info_var.set(info_text)
                
                # Update matrix dropdown if Matrix Modification is selected
                if self.processing_type_var.get() == "Matrix Modification":
                    self.update_matrix_dropdown()
                # Update dimension dropdown if Data Annotation is selected
                elif self.processing_type_var.get() == "Data Annotation":
                    self.update_dimension_dropdown()
                # Update browse path if Indexing is selected
                elif self.processing_type_var.get() == "Indexing":
                    self.update_default_browse_path()
                # Update matrix dropdown if Ruzicka Similarity is selected
                elif self.processing_type_var.get() == "Ruzicka Similarity":
                    self.update_ruzicka_matrix_dropdown()
                # Update matrix dropdown if Hierarchical Clustering is selected
                elif self.processing_type_var.get() == "Hierarchical Clustering":
                    self.update_hierarchical_matrix_dropdown()
    
    def start_processing(self):
        """Start a processing job."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset to process.")
            return
        
        processing_type = self.processing_type_var.get()
        if not processing_type:
            messagebox.showwarning("No Processing Type", "Please select a processing type.")
            return
        
        # Additional validation for Matrix Modification
        if processing_type == "Matrix Modification":
            matrix_selected = self.param_vars.get('matrix', tk.StringVar()).get()
            if not matrix_selected:
                messagebox.showwarning("No Matrix Selected", "Please select a matrix to modify.")
                return
        
        # Additional validation for Data Annotation
        if processing_type == "Data Annotation":
            annotation_name = self.param_vars.get('annotation_name', tk.StringVar()).get().strip()
            if not annotation_name:
                messagebox.showwarning("Missing Annotation Name", "Please provide an annotation name.")
                return
            
            vector_dimension = self.param_vars.get('vector_dimension', tk.StringVar()).get()
            if not vector_dimension:
                messagebox.showwarning("Missing Vector Dimension", "Please select a vector dimension.")
                return
            
            # Check if at least one valid stimulation period is provided
            valid_periods = 0
            for period_data in getattr(self, 'stimulation_periods', []):
                start_str = period_data['start_var'].get().strip()
                end_str = period_data['end_var'].get().strip()
                if start_str and end_str:
                    valid_periods += 1
            
            if valid_periods == 0:
                messagebox.showwarning("Missing Stimulation Periods", 
                                     "Please provide at least one stimulation period with start and end times.")
                return
        
        # Additional validation for Indexing
        if processing_type == "Indexing":
            indexing_type = self.param_vars.get('indexing_type', tk.StringVar()).get()
            if not indexing_type:
                messagebox.showwarning("Missing Indexing Type", "Please select an indexing type (Row or Column).")
                return
            
            selected_file = self.param_vars.get('selected_file', tk.StringVar()).get().strip()
            if not selected_file:
                messagebox.showwarning("Missing CSV File", "Please select a CSV file containing the vector data.")
                return
            
            vector_column = self.param_vars.get('vector_column', tk.StringVar()).get().strip()
            if not vector_column:
                messagebox.showwarning("Missing Vector Column", "Please select a vector column from the CSV file.")
                return
            
            column_name = self.param_vars.get('column_name', tk.StringVar()).get().strip()
            if not column_name:
                messagebox.showwarning("Missing Column Name", "Please provide a name for the index column.")
                return
            
            # Check for column name collision
            if not self.check_indexing_column_collision(indexing_type, column_name):
                return  # User cancelled due to collision
        
        # Additional validation for Ruzicka Similarity
        if processing_type == "Ruzicka Similarity":
            matrix_selected = self.param_vars.get('matrix', tk.StringVar()).get()
            if not matrix_selected:
                messagebox.showwarning("No Matrix Selected", "Please select a matrix to calculate Ruzicka similarity.")
                return
            
            matrix_name = self.param_vars.get('matrix_name', tk.StringVar()).get().strip()
            if not matrix_name:
                messagebox.showwarning("Missing Matrix Name", "Please provide a name for the similarity matrix.")
                return
        
        # Additional validation for Hierarchical Clustering
        if processing_type == "Hierarchical Clustering":
            matrix_selected = self.param_vars.get('matrix', tk.StringVar()).get()
            if not matrix_selected:
                messagebox.showwarning("No Matrix Selected", "Please select a matrix for hierarchical clustering.")
                return
        
        try:
            # Collect parameters
            parameters = {}
            for key, var in self.param_vars.items():
                if isinstance(var, tk.BooleanVar):
                    parameters[key] = var.get()
                else:
                    value = var.get().strip()
                    
                    # Handle string parameters
                    parameters[key] = value if value else None
            
            # Handle Data Annotation specific parameters
            if processing_type == "Data Annotation":
                # Collect stimulation periods from the dynamic UI
                stimulation_periods = []
                for period_data in self.stimulation_periods:
                    start_str = period_data['start_var'].get().strip()
                    end_str = period_data['end_var'].get().strip()
                    
                    # Only add periods with both start and end values
                    if start_str and end_str:
                        try:
                            start_time = float(start_str)
                            end_time = float(end_str)
                            stimulation_periods.append((start_time, end_time))
                        except ValueError:
                            continue  # Skip invalid periods
                
                parameters['stimulation_periods'] = stimulation_periods
                
                # Generate job name from annotation name
                annotation_name = parameters.get('annotation_name', 'annotation_vector')
                job_name = f"Data_Annotation_{annotation_name}"
            elif processing_type == "Indexing":
                # Generate job name for Indexing
                column_name = parameters.get('column_name', 'index')
                indexing_type = parameters.get('indexing_type', 'Row Indexing')
                job_name = f"Indexing_{column_name}_{indexing_type.replace(' ', '_')}"
            elif processing_type == "Ruzicka Similarity":
                # Generate job name for Ruzicka Similarity
                matrix_name = parameters.get('matrix_name', 'Ruzicka Matrix')
                job_name = f"Ruzicka_Similarity_{matrix_name.replace(' ', '_')}"
            elif processing_type == "Hierarchical Clustering":
                # Generate job name for Hierarchical Clustering
                output_prefix = parameters.get('output_name_prefix', 'HAC')
                clustering_method = parameters.get('clustering_method', 'ward')
                distance_metric = parameters.get('distance_metric', 'euclidean')[:4]  # First 4 letters
                job_name = f"HAC_{output_prefix}_{clustering_method}_{distance_metric}"
            else:
                # Generate job name from matrix name for other processing types
                matrix_name = parameters.get('matrix_name', 'extracted_matrix')
                job_name = f"Matrix_Extraction_{matrix_name}"
            
            # Create processing job
            job_id = ProcessingJobOperations.create_job(
                dataset_id=self.selected_dataset.id,
                job_name=job_name,
                job_type=processing_type,
                parameters=parameters
            )
            
            # Start processing in background thread
            ProcessingJobOperations.update_job_status(job_id, "running", progress=0.0)
            
            # Start real processing with a background thread
            threading.Thread(target=self.real_processing, args=(job_id, processing_type, parameters), daemon=True).start()
            
            messagebox.showinfo("Success", f"Processing job '{job_name}' started successfully!")
            self.refresh_jobs()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start processing: {str(e)}")
    
    def preview_matrix(self):
        """Preview the processing operation."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset to preview.")
            return
        
        processing_type = self.processing_type_var.get()
        
        # Handle Indexing preview differently
        if processing_type == "Indexing":
            self.preview_indexing()
            return
        
        # Handle Ruzicka Similarity preview
        if processing_type == "Ruzicka Similarity":
            self.preview_ruzicka_similarity()
            return
        
        try:
            # Collect parameters
            parameters = {}
            for key, var in self.param_vars.items():
                if isinstance(var, tk.BooleanVar):
                    parameters[key] = var.get()
                else:
                    value = var.get().strip()
                    parameters[key] = value if value else None
            
            # Load data
            if self.selected_dataset.file_format == 'csv':
                import pandas as pd
                data = pd.read_csv(self.selected_dataset.file_path, header=None)
            elif self.selected_dataset.file_format in ['xlsx', 'xls']:
                import pandas as pd
                data = pd.read_excel(self.selected_dataset.file_path, header=None)
            else:
                messagebox.showerror("Error", f"Unsupported file format: {self.selected_dataset.file_format}")
                return
            
            # Get processor and generate preview
            from src.data_processing.processors import MatrixExtractionProcessor
            processor = MatrixExtractionProcessor()
            preview_result = processor.get_preview(data, parameters)
            
            if preview_result['success']:
                self.show_preview_window(preview_result)
            else:
                messagebox.showerror("Preview Error", preview_result['message'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {str(e)}")
    
    def preview_ruzicka_similarity(self):
        """Preview the Ruzicka similarity calculation."""
        # Validate required parameters
        matrix_selected = self.param_vars.get('matrix', tk.StringVar()).get().strip()
        if not matrix_selected:
            messagebox.showwarning("No Matrix Selected", "Please select a matrix to calculate Ruzicka similarity.")
            return
        
        matrix_name = self.param_vars.get('matrix_name', tk.StringVar()).get().strip()
        if not matrix_name:
            messagebox.showwarning("Missing Matrix Name", "Please provide a name for the similarity matrix.")
            return
        
        try:
            # Collect parameters
            parameters = {}
            for key, var in self.param_vars.items():
                if isinstance(var, tk.BooleanVar):
                    parameters[key] = var.get()
                else:
                    value = var.get().strip()
                    parameters[key] = value if value else None
            
            # Add dataset information
            parameters['dataset_name'] = self.selected_dataset.name
            
            # Get Ruzicka Similarity processor and generate preview
            from src.data_processing.processors import DataProcessingManager
            manager = DataProcessingManager()
            ruzicka_processor = manager.get_processor("Ruzicka Similarity")
            
            if ruzicka_processor:
                preview_result = ruzicka_processor.get_preview(parameters)
                
                if preview_result['success']:
                    self.show_preview_window(preview_result)
                else:
                    messagebox.showerror("Preview Error", preview_result['message'])
            else:
                messagebox.showerror("Error", "Ruzicka Similarity processor not found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate Ruzicka similarity preview: {str(e)}")
    
    def preview_indexing(self):
        """Preview the indexing operation."""
        # Validate required parameters
        selected_file = self.param_vars.get('selected_file', tk.StringVar()).get().strip()
        if not selected_file:
            messagebox.showwarning("Missing CSV File", "Please select a CSV file containing the vector data.")
            return
        
        vector_column = self.param_vars.get('vector_column', tk.StringVar()).get().strip()
        if not vector_column:
            messagebox.showwarning("Missing Vector Column", "Please select a vector column from the CSV file.")
            return
        
        column_name = self.param_vars.get('column_name', tk.StringVar()).get().strip()
        if not column_name:
            messagebox.showwarning("Missing Column Name", "Please provide a name for the index column.")
            return
        
        try:
            # Load the source CSV file
            if not os.path.exists(selected_file):
                messagebox.showerror("File Not Found", f"Source CSV file not found: {selected_file}")
                return
            
            source_df = pd.read_csv(selected_file)
            
            # Check if the specified column exists
            if vector_column not in source_df.columns:
                messagebox.showerror("Column Not Found", f"Column '{vector_column}' not found in {selected_file}")
                return
            
            # Extract the vector data
            vector_data = source_df[vector_column]
            
            # Convert to numeric, handling any non-numeric values
            try:
                vector_numeric = pd.to_numeric(vector_data, errors='coerce')
            except Exception:
                messagebox.showerror("Data Error", f"Column '{vector_column}' contains non-numeric data that cannot be converted")
                return
            
            # Check for NaN values after conversion
            if vector_numeric.isna().any():
                messagebox.showerror("Data Error", f"Column '{vector_column}' contains non-numeric values that cannot be processed")
                return
            
            # Generate indices: highest value gets index 1, second highest gets index 2, etc.
            indices = vector_numeric.rank(method='first', ascending=False).astype(int)
            
            # Create sorted values based on indices
            sorted_values = vector_numeric.iloc[indices.argsort()]
            
            # Prepare preview data
            preview_data = pd.DataFrame({
                'Original_Values': vector_numeric,
                'Indices': indices,
                'Sorted_Values': sorted_values.values
            })
            
            # Show the indexing preview window
            self.show_indexing_preview_window(preview_data, column_name, vector_column)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate indexing preview: {str(e)}")
    
    def show_preview_window(self, preview_result):
        """Show preview in a separate window."""
        preview_window = tk.Toplevel(self.window)
        preview_window.title(f"Matrix Preview - {preview_result['matrix_name']}")
        preview_window.geometry("800x600")
        
        # Info frame
        info_frame = ttk.Frame(preview_window)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = f"Matrix: {preview_result['matrix_name']}\n"
        info_text += f"Full Size: {preview_result['full_shape']}\n"
        info_text += f"Preview Size: {preview_result['preview_shape']}\n"
        info_text += f"Transposed: {preview_result['transposed']}"
        
        ttk.Label(info_frame, text=info_text, font=("Arial", 10)).pack(anchor="w")
        
        # Preview frame with scrollbars
        preview_frame = ttk.Frame(preview_window)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create text widget with scrollbars
        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill="both", expand=True)
        
        preview_text = tk.Text(text_frame, wrap=tk.NONE, font=("Courier", 9))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=preview_text.yview)
        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=preview_text.xview)
        
        preview_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and text
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        preview_text.pack(side="left", fill="both", expand=True)
        
        # Insert preview data
        preview_matrix = preview_result['preview_matrix']
        preview_text.insert("1.0", preview_matrix.to_string())
        preview_text.config(state="disabled")
        
        # Close button
        ttk.Button(preview_window, text="Close", command=preview_window.destroy).pack(pady=10)
    
    def show_indexing_preview_window(self, preview_data, column_name, vector_column):
        """Show indexing preview in a separate window with three columns."""
        preview_window = tk.Toplevel(self.window)
        preview_window.title(f"Indexing Preview - {column_name}")
        preview_window.geometry("900x700")
        
        # Info frame
        info_frame = ttk.Frame(preview_window)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = f"Vector Column: {vector_column}\n"
        info_text += f"Index Column Name: {column_name}\n"
        info_text += f"Total Values: {len(preview_data)}\n"
        info_text += f"Unique Values: {preview_data['Original_Values'].nunique()}"
        
        ttk.Label(info_frame, text=info_text, font=("Arial", 10)).pack(anchor="w")
        
        # Preview frame with scrollbars
        preview_frame = ttk.Frame(preview_window)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create Treeview for tabular display
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill="both", expand=True)
        
        # Treeview with three columns
        columns = ('original', 'indices', 'sorted')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)
        
        # Define column headings
        tree.heading('original', text='Original Values')
        tree.heading('indices', text='Indices')
        tree.heading('sorted', text='Sorted Values')
        
        # Configure column widths
        tree.column('original', width=200, anchor='center')
        tree.column('indices', width=100, anchor='center')
        tree.column('sorted', width=200, anchor='center')
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and tree
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        
        # Insert data into the tree
        for i in range(len(preview_data)):
            original_val = f"{preview_data.iloc[i]['Original_Values']:.6f}"
            index_val = str(preview_data.iloc[i]['Indices'])
            sorted_val = f"{preview_data.iloc[i]['Sorted_Values']:.6f}"
            
            tree.insert('', 'end', values=(original_val, index_val, sorted_val))
        
        # Button frame
        button_frame = ttk.Frame(preview_window)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=preview_window.destroy).pack(side="right", padx=5)
    
    def real_processing(self, job_id, processing_type, parameters):
        """Perform actual matrix extraction processing."""
        try:
            def progress_callback(progress):
                ProcessingJobOperations.update_job_status(job_id, "running", progress=progress)
                self.window.after(0, self.refresh_jobs)
            
            # Import the processing manager
            from src.data_processing.processors import DataProcessingManager
            
            # Create processing manager
            manager = DataProcessingManager()
            
            # Get the job details to find the dataset
            from src.database.connection import get_database
            db = get_database()
            job_query = "SELECT dataset_id, job_name FROM processing_jobs WHERE id = ?"
            job_result = db.execute_query(job_query, (job_id,))
            
            if not job_result:
                raise Exception(f"Job {job_id} not found in database")
            
            dataset_id, job_name = job_result[0]
            
            # Process the dataset
            result = manager.process_dataset(
                dataset_id=dataset_id,
                processor_name=processing_type,
                job_name=job_name,
                parameters=parameters,
                progress_callback=progress_callback
            )
            
            if result['success']:
                # Complete the job with actual output path
                output_path = result.get('output_path', 'No output file')
                ProcessingJobOperations.update_job_status(
                    job_id, "completed", progress=100.0, 
                    output_path=output_path
                )
            else:
                # Job failed
                ProcessingJobOperations.update_job_status(
                    job_id, "failed", error_message=result.get('message', 'Unknown error')
                )
            
            # Final GUI update
            self.window.after(0, self.refresh_jobs)
            
        except Exception as e:
            ProcessingJobOperations.update_job_status(
                job_id, "failed", error_message=str(e)
            )
            self.window.after(0, self.refresh_jobs)
    
    def refresh_jobs(self):
        """Refresh the active jobs list."""
        try:
            # Clear existing items
            for item in self.jobs_tree.get_children():
                self.jobs_tree.delete(item)
            
            # Get active jobs
            active_jobs = ProcessingJobOperations.get_active_jobs()
            
            # Add completed jobs from today
            from datetime import datetime, timedelta
            today = datetime.now() - timedelta(days=1)
            
            all_jobs_query = """
                SELECT * FROM processing_jobs 
                WHERE start_time > ? OR status IN ('running', 'pending')
                ORDER BY start_time DESC
            """
            
            from src.database.connection import get_database
            db = get_database()
            results = db.execute_query(all_jobs_query, (today.isoformat(),))
            
            for result in results:
                job_id = result[0]
                dataset_id = result[1]
                job_name = result[2]
                job_type = result[3]
                status = result[7]
                progress = result[10] or 0.0
                
                # Get dataset name
                dataset = DatasetOperations.get_dataset(dataset_id)
                dataset_name = dataset.name if dataset else f"Dataset {dataset_id}"
                
                # Insert into tree
                self.jobs_tree.insert("", "end", text=job_name, 
                                     values=(dataset_name, job_type, status, f"{progress:.1f}%"))
                
        except Exception as e:
            print(f"Error refreshing jobs: {e}")
    
    def cancel_job(self):
        """Cancel selected job."""
        selection = self.jobs_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to cancel.")
            return
        
        # This would require more complex job management
        messagebox.showinfo("Coming Soon", "Job cancellation will be implemented soon!")
    
    def remove_finished_job(self):
        """Remove selected finished or failed job."""
        selection = self.jobs_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to remove.")
            return
        
        try:
            # Get selected job info
            item = self.jobs_tree.item(selection[0])
            job_name = item['text']
            job_status = item['values'][2]  # Status column
            
            # Only allow removal of completed or failed jobs
            if job_status not in ['completed', 'failed']:
                messagebox.showwarning("Cannot Remove", 
                                     f"Cannot remove job with status '{job_status}'. "
                                     "Only completed or failed jobs can be removed.")
                return
            
            # Confirm removal
            confirm = messagebox.askyesno("Confirm Removal", 
                                        f"Are you sure you want to remove the job '{job_name}'?\n"
                                        "This action cannot be undone.")
            
            if confirm:
                # Find the job ID from the database
                from src.database.connection import get_database
                db = get_database()
                
                # Get job ID by name and status
                job_query = """
                    SELECT id FROM processing_jobs 
                    WHERE job_name = ? AND status = ?
                    ORDER BY start_time DESC LIMIT 1
                """
                job_result = db.execute_query(job_query, (job_name, job_status))
                
                if job_result:
                    job_id = job_result[0][0]
                    
                    # Delete the job from database
                    delete_query = "DELETE FROM processing_jobs WHERE id = ?"
                    db.execute_query(delete_query, (job_id,))
                    
                    # Refresh the jobs list
                    self.refresh_jobs()
                    
                    messagebox.showinfo("Success", f"Job '{job_name}' has been removed.")
                else:
                    messagebox.showerror("Error", "Could not find job in database.")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove job: {str(e)}")
    
    def schedule_job_refresh(self):
        """Schedule periodic job refresh."""
        self.refresh_jobs()
        self.window.after(5000, self.schedule_job_refresh)  # Refresh every 5 seconds


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    app = DataProcessingGUI()
    root.mainloop()
