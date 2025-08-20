"""
Data Import GUI - Interface for importing and managing datasets.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations
from src.utils.folder_manager import DatasetFolderManager


class DataImportGUI:
    """GUI for data import functionality."""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Data Import")
        self.window.geometry("700x780")
        self.window.minsize(700, 750)
        self.window.resizable(True, True)
        self.window.configure(bg='#f0f0f0')
        
        self.selected_files = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = ttk.Label(self.window, text="Data Import", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # File selection frame
        file_frame = ttk.LabelFrame(self.window, text="File Selection", padding=10)
        file_frame.pack(fill="x", padx=20, pady=5)
        
        # File selection buttons
        buttons_frame = ttk.Frame(file_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        ttk.Button(buttons_frame, text="Select Files", 
                  command=self.select_files).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Select Directory", 
                  command=self.select_directory).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Clear Selection", 
                  command=self.clear_selection).pack(side="left", padx=5)
        
        # Selected files list
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        
        ttk.Label(list_frame, text="Selected Files:").pack(anchor="w")
        
        self.files_listbox = tk.Listbox(list_frame, height=8)
        self.files_listbox.pack(side="left", fill="both", expand=True)
        
        files_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        files_scrollbar.pack(side="right", fill="y")
        
        self.files_listbox.config(yscrollcommand=files_scrollbar.set)
        files_scrollbar.config(command=self.files_listbox.yview)
        
        # Import options frame
        options_frame = ttk.LabelFrame(self.window, text="Import Options", padding=10)
        options_frame.pack(fill="x", padx=20, pady=5)
        
        # Dataset name
        ttk.Label(options_frame, text="Dataset Name:").grid(row=0, column=0, sticky="w", padx=5)
        self.dataset_name_var = tk.StringVar()
        self.dataset_name_entry = ttk.Entry(options_frame, textvariable=self.dataset_name_var, width=40)
        self.dataset_name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # File format
        ttk.Label(options_frame, text="File Format:").grid(row=1, column=0, sticky="w", padx=5)
        self.format_var = tk.StringVar()
        format_combo = ttk.Combobox(options_frame, textvariable=self.format_var, 
                                   values=["csv", "xlsx", "txt", "mat", "h5", "json", "other"], 
                                   state="readonly", width=37)
        format_combo.grid(row=1, column=1, padx=5, pady=2)
        
        # Description
        ttk.Label(options_frame, text="Description:").grid(row=2, column=0, sticky="nw", padx=5)
        self.description_text = tk.Text(options_frame, width=40, height=4)
        self.description_text.grid(row=2, column=1, padx=5, pady=2)
        
        # Copy to data directory option
        self.copy_files_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Copy files to data/raw directory", 
                       variable=self.copy_files_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=5)
        
        # Advanced import options frame
        advanced_frame = ttk.LabelFrame(self.window, text="Advanced Import Options", padding=10)
        advanced_frame.pack(fill="x", padx=20, pady=5)
        
        # Skip rows option
        ttk.Label(advanced_frame, text="Skip rows at beginning:").grid(row=0, column=0, sticky="w", padx=5)
        self.skip_rows_var = tk.StringVar(value="0")
        skip_rows_entry = ttk.Entry(advanced_frame, textvariable=self.skip_rows_var, width=10)
        skip_rows_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        # Header row option
        ttk.Label(advanced_frame, text="Header row number:").grid(row=0, column=2, sticky="w", padx=5)
        self.header_row_var = tk.StringVar(value="0")
        header_row_entry = ttk.Entry(advanced_frame, textvariable=self.header_row_var, width=10)
        header_row_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        
        # Data type options
        self.convert_numeric_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Convert to numeric where possible", 
                       variable=self.convert_numeric_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        # Raw import option
        self.raw_import_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="Import entire file (ignore headers)", 
                       variable=self.raw_import_var, 
                       command=self.on_raw_import_toggle).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        self.handle_errors_var = tk.StringVar(value="coerce")
        ttk.Label(advanced_frame, text="Handle conversion errors:").grid(row=1, column=2, sticky="w", padx=5)
        error_combo = ttk.Combobox(advanced_frame, textvariable=self.handle_errors_var,
                                  values=["coerce", "skip_row", "keep_text"], 
                                  state="readonly", width=12)
        error_combo.grid(row=1, column=3, padx=5, pady=2)
        
        # Preview and configure button
        preview_button_frame = ttk.Frame(advanced_frame)
        preview_button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(preview_button_frame, text="Preview & Configure Import", 
                  command=self.preview_and_configure).pack(side="left", padx=5)
        ttk.Button(preview_button_frame, text="Auto-Detect Settings", 
                  command=self.auto_detect_settings).pack(side="left", padx=5)
        
        # Progress frame
        progress_frame = ttk.Frame(self.window)
        progress_frame.pack(fill="x", padx=20, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready to import")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.pack(anchor="w")
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill="x", pady=2)
        
        # Action buttons frame
        action_frame = ttk.Frame(self.window)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Button(action_frame, text="Import Data", 
                  command=self.import_data).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Preview Data", 
                  command=self.preview_data).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Close", 
                  command=self.window.destroy).pack(side="right", padx=5)
    
    def select_files(self):
        """Open file dialog to select files."""
        files = filedialog.askopenfilenames(
            title="Select Data Files",
            filetypes=[
                ("All supported", "*.csv;*.xlsx;*.txt;*.mat;*.h5;*.json"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("Text files", "*.txt"),
                ("MATLAB files", "*.mat"),
                ("HDF5 files", "*.h5"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            self.selected_files.extend(files)
            self.update_files_list()
            self.auto_fill_dataset_name()
    
    def select_directory(self):
        """Open directory dialog to select all files in a directory."""
        directory = filedialog.askdirectory(title="Select Directory with Data Files")
        
        if directory:
            # Find all data files in directory
            data_extensions = {'.csv', '.xlsx', '.txt', '.mat', '.h5', '.json'}
            directory_path = Path(directory)
            
            for file_path in directory_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in data_extensions:
                    self.selected_files.append(str(file_path))
            
            self.update_files_list()
            self.auto_fill_dataset_name()
    
    def clear_selection(self):
        """Clear the selected files list."""
        self.selected_files = []
        self.update_files_list()
        self.dataset_name_var.set("")
    
    def update_files_list(self):
        """Update the files listbox with selected files."""
        self.files_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
    
    def auto_fill_dataset_name(self):
        """Auto-fill dataset name based on selected files."""
        if self.selected_files and not self.dataset_name_var.get():
            if len(self.selected_files) == 1:
                # Single file - use filename without extension
                name = Path(self.selected_files[0]).stem
            else:
                # Multiple files - use directory name or generic name
                common_dir = os.path.commonpath(self.selected_files)
                name = os.path.basename(common_dir) if common_dir else "MultiFile_Dataset"
            
            self.dataset_name_var.set(name)
            
            # Auto-detect format if possible
            if self.selected_files:
                ext = Path(self.selected_files[0]).suffix.lower()
                format_map = {'.csv': 'csv', '.xlsx': 'xlsx', '.txt': 'txt', 
                             '.mat': 'mat', '.h5': 'h5', '.json': 'json'}
                if ext in format_map:
                    self.format_var.set(format_map[ext])
    
    def preview_data(self):
        """Preview the selected data files."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to preview.")
            return
        
        # Create preview window
        preview_window = tk.Toplevel(self.window)
        preview_window.title("Data Preview")
        preview_window.geometry("800x400")
        
        # For now, just show file information
        preview_text = tk.Text(preview_window, wrap=tk.WORD)
        preview_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        preview_content = "Data Preview:\\n\\n"
        for i, file_path in enumerate(self.selected_files[:5]):  # Show first 5 files
            file_info = f"File {i+1}: {os.path.basename(file_path)}\\n"
            file_info += f"Path: {file_path}\\n"
            file_info += f"Size: {os.path.getsize(file_path)} bytes\\n"
            file_info += f"Modified: {os.path.getmtime(file_path)}\\n\\n"
            preview_content += file_info
        
        if len(self.selected_files) > 5:
            preview_content += f"... and {len(self.selected_files) - 5} more files\\n"
        
        preview_text.insert(tk.END, preview_content)
        preview_text.config(state=tk.DISABLED)
    
    def preview_and_configure(self):
        """Preview file structure and configure import settings."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to preview.")
            return
        
        # For now, preview the first selected file
        file_path = self.selected_files[0]
        
        # Create preview window
        preview_window = tk.Toplevel(self.window)
        preview_window.title(f"Import Preview - {os.path.basename(file_path)}")
        preview_window.geometry("1000x600")
        preview_window.transient(self.window)
        
        # Create main frame with notebook
        main_frame = ttk.Frame(preview_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # File info
        info_label = ttk.Label(main_frame, text=f"File: {os.path.basename(file_path)}", 
                              font=("Arial", 12, "bold"))
        info_label.pack(pady=5)
        
        # Preview notebook
        preview_notebook = ttk.Notebook(main_frame)
        preview_notebook.pack(fill="both", expand=True, pady=5)
        
        try:
            # Raw preview tab
            self.create_raw_preview_tab(preview_notebook, file_path)
            
            # Structured preview tab
            self.create_structured_preview_tab(preview_notebook, file_path)
            
            # Configuration tab
            self.create_config_tab(preview_notebook, preview_window)
            
        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to create preview: {str(e)}")
            preview_window.destroy()
    
    def create_raw_preview_tab(self, notebook, file_path):
        """Create raw file preview tab."""
        raw_frame = ttk.Frame(notebook)
        notebook.add(raw_frame, text="Raw File View")
        
        # Info
        ttk.Label(raw_frame, text="First 15 lines of the file:", 
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Text widget for raw content
        text_frame = ttk.Frame(raw_frame)
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        raw_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 9))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=raw_text.yview)
        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=raw_text.xview)
        raw_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 15:
                        break
                    lines.append(f"{i:2d}: {line.rstrip()}")
                
                raw_content = "\n".join(lines)
                raw_text.insert(1.0, raw_content)
                
        except Exception as e:
            raw_text.insert(1.0, f"Error reading file: {str(e)}")
        
        raw_text.config(state=tk.DISABLED)
        
        # Pack widgets
        raw_text.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
    
    def create_structured_preview_tab(self, notebook, file_path):
        """Create structured preview tab with import options applied."""
        struct_frame = ttk.Frame(notebook)
        notebook.add(struct_frame, text="Import Preview")
        
        # Controls frame
        controls_frame = ttk.Frame(struct_frame)
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(controls_frame, text="Preview with current settings:", 
                 font=("Arial", 10, "bold")).pack(anchor="w")
        
        ttk.Button(controls_frame, text="Refresh Preview", 
                  command=lambda: self.refresh_structured_preview(struct_frame, file_path)).pack(anchor="w", pady=2)
        
        # Preview area
        self.preview_area = ttk.Frame(struct_frame)
        self.preview_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Initial preview
        self.refresh_structured_preview(struct_frame, file_path)
    
    def refresh_structured_preview(self, parent_frame, file_path):
        """Refresh the structured preview with current settings."""
        # Clear existing preview
        for widget in self.preview_area.winfo_children():
            widget.destroy()
        
        try:
            # Get current settings
            skip_rows = int(self.skip_rows_var.get()) if self.skip_rows_var.get().isdigit() else 0
            header_row = int(self.header_row_var.get()) if self.header_row_var.get().isdigit() else 0
            
            # Import with current settings
            from src.data_processing.importers import DataImportManager
            import_manager = DataImportManager()
            
            # Preview with settings
            result = self.import_with_settings(file_path, max_rows=10)
            
            if not result['success']:
                error_label = ttk.Label(self.preview_area, text=f"Preview Error: {result['message']}", 
                                       foreground="red")
                error_label.pack(pady=10)
                return
            
            data = result['data']
            
            # Show settings info
            raw_import_text = ", Raw import: ON" if self.raw_import_var.get() else ""
            settings_text = f"Settings: Skip {skip_rows} rows, Header at row {header_row}, Convert numeric: {self.convert_numeric_var.get()}{raw_import_text}"
            ttk.Label(self.preview_area, text=settings_text, font=("Arial", 9, "italic")).pack(anchor="w", pady=2)
            
            if hasattr(data, 'columns'):
                # DataFrame preview
                preview_tree = ttk.Treeview(self.preview_area, height=12)
                preview_scrollbar = ttk.Scrollbar(self.preview_area, orient="vertical", command=preview_tree.yview)
                preview_tree.configure(yscrollcommand=preview_scrollbar.set)
                
                # Configure columns (show first 10 columns max)
                columns_to_show = list(data.columns)[:10]
                preview_tree["columns"] = columns_to_show
                preview_tree["show"] = "tree headings"
                
                # Set column headings and widths
                preview_tree.heading("#0", text="Row")
                preview_tree.column("#0", width=50)
                
                for col in columns_to_show:
                    preview_tree.heading(col, text=str(col)[:20])
                    preview_tree.column(col, width=100)
                
                # Add data rows
                import pandas as pd
                for i, row in data.iterrows():
                    values = []
                    for col in columns_to_show:
                        val = str(row[col])[:20] if not pd.isna(row[col]) else "NaN"
                        values.append(val)
                    preview_tree.insert("", "end", text=str(i), values=values)
                
                preview_tree.pack(side="left", fill="both", expand=True)
                preview_scrollbar.pack(side="right", fill="y")
                
                # Show data info
                info_text = f"Preview Shape: {data.shape}, Data Types: {len(data.dtypes.unique())} unique types"
                if len(columns_to_show) < len(data.columns):
                    info_text += f" (showing first {len(columns_to_show)} of {len(data.columns)} columns)"
                
                ttk.Label(self.preview_area, text=info_text, font=("Arial", 9)).pack(anchor="w", pady=2)
            
        except Exception as e:
            error_label = ttk.Label(self.preview_area, text=f"Preview Error: {str(e)}", 
                                   foreground="red")
            error_label.pack(pady=10)
    
    def create_config_tab(self, notebook, preview_window):
        """Create configuration tab with import settings."""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Import Configuration")
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                                text="Configure import settings based on the preview, then apply to main import dialog.",
                                font=("Arial", 10))
        instructions.pack(padx=10, pady=10, anchor="w")
        
        # Configuration options (mirror main dialog)
        config_options = ttk.LabelFrame(config_frame, text="Import Settings", padding=10)
        config_options.pack(fill="x", padx=10, pady=5)
        
        # Skip rows
        ttk.Label(config_options, text="Skip rows at beginning:").grid(row=0, column=0, sticky="w", padx=5)
        skip_entry = ttk.Entry(config_options, textvariable=self.skip_rows_var, width=10)
        skip_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Header row
        ttk.Label(config_options, text="Header row number:").grid(row=0, column=2, sticky="w", padx=10)
        header_entry = ttk.Entry(config_options, textvariable=self.header_row_var, width=10)
        header_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # Convert numeric
        ttk.Checkbutton(config_options, text="Convert to numeric where possible", 
                       variable=self.convert_numeric_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        # Raw import option
        ttk.Checkbutton(config_options, text="Import entire file (ignore headers)", 
                       variable=self.raw_import_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        # Handle errors
        ttk.Label(config_options, text="Handle conversion errors:").grid(row=1, column=2, sticky="w", padx=10)
        ttk.Combobox(config_options, textvariable=self.handle_errors_var,
                    values=["coerce", "skip_row", "keep_text"], 
                    state="readonly", width=12).grid(row=1, column=3, padx=5, pady=2)
        
        # Action buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply Settings & Close", 
                  command=preview_window.destroy).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_import_settings).pack(side="right", padx=5)
    
    def auto_detect_settings(self):
        """Auto-detect optimal import settings."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files first.")
            return
        
        file_path = self.selected_files[0]
        
        try:
            # Analyze first few rows to detect structure
            detected_settings = self.analyze_file_structure(file_path)
            
            # Apply detected settings
            self.skip_rows_var.set(str(detected_settings.get('skip_rows', 0)))
            self.header_row_var.set(str(detected_settings.get('header_row', 0)))
            self.convert_numeric_var.set(detected_settings.get('convert_numeric', True))
            
            # Show detection results
            message = f"Auto-detected settings:\n"
            message += f"Skip rows: {detected_settings.get('skip_rows', 0)}\n"
            message += f"Header row: {detected_settings.get('header_row', 0)}\n"
            message += f"Reason: {detected_settings.get('reason', 'Standard detection')}"
            
            messagebox.showinfo("Auto-Detection Results", message)
            
        except Exception as e:
            messagebox.showerror("Detection Error", f"Failed to auto-detect settings: {str(e)}")
    
    def analyze_file_structure(self, file_path):
        """Analyze file structure to suggest optimal import settings."""
        import pandas as pd
        
        try:
            # Read first 10 rows without any processing
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(10)]
            
            # Analyze each row
            analysis = []
            for i, line in enumerate(lines):
                if not line:
                    continue
                
                parts = line.split(',')
                numeric_count = 0
                text_count = 0
                
                for part in parts:
                    part = part.strip().strip('"\'')
                    if part:
                        try:
                            float(part)
                            numeric_count += 1
                        except ValueError:
                            text_count += 1
                
                analysis.append({
                    'row': i,
                    'numeric_count': numeric_count,
                    'text_count': text_count,
                    'total_parts': len(parts),
                    'line': line[:100]  # First 100 chars for inspection
                })
            
            # Find likely header row (high text count, reasonable structure)
            header_candidates = []
            for row_info in analysis:
                if row_info['text_count'] > row_info['numeric_count'] and row_info['total_parts'] > 5:
                    header_candidates.append(row_info['row'])
            
            # Find likely data rows (high numeric count)
            data_candidates = []
            for row_info in analysis:
                if row_info['numeric_count'] > row_info['text_count'] and row_info['total_parts'] > 5:
                    data_candidates.append(row_info['row'])
            
            # Determine settings
            if header_candidates and data_candidates:
                header_row = min(header_candidates)
                first_data_row = min(data_candidates)
                skip_rows = max(0, header_row)  # Skip everything before header
                
                reason = f"Detected header at row {header_row}, data starts at row {first_data_row}"
            else:
                # Default fallback
                header_row = 0
                skip_rows = 0
                reason = "Could not detect clear structure, using defaults"
            
            return {
                'skip_rows': skip_rows,
                'header_row': header_row - skip_rows,  # Relative to after skipping
                'convert_numeric': True,
                'reason': reason
            }
            
        except Exception as e:
            return {
                'skip_rows': 0,
                'header_row': 0,
                'convert_numeric': True,
                'reason': f"Detection failed: {str(e)}"
            }
    
    def on_raw_import_toggle(self):
        """Handle raw import toggle - disable header settings when enabled."""
        if self.raw_import_var.get():
            # Raw import enabled - disable header settings
            self.header_row_var.set("0")
            # You could disable the header row entry here if you have a reference to it
        # When raw import is disabled, header settings remain enabled
    
    def reset_import_settings(self):
        """Reset import settings to defaults."""
        self.skip_rows_var.set("0")
        self.header_row_var.set("0")
        self.convert_numeric_var.set(True)
        self.handle_errors_var.set("coerce")
        self.raw_import_var.set(False)
    
    def import_with_settings(self, file_path, max_rows=None):
        """Import file with current advanced settings."""
        try:
            # Get settings
            skip_rows = int(self.skip_rows_var.get()) if self.skip_rows_var.get().isdigit() else 0
            header_row = int(self.header_row_var.get()) if self.header_row_var.get().isdigit() else 0
            convert_numeric = self.convert_numeric_var.get()
            handle_errors = self.handle_errors_var.get()
            raw_import = self.raw_import_var.get()
            
            # Use the DataImportManager for consistent import behavior
            from src.data_processing.importers import DataImportManager
            
            import_manager = DataImportManager()
            
            # Prepare import settings
            import_settings = {
                'skip_rows': skip_rows,
                'convert_numeric': convert_numeric,
                'handle_errors': handle_errors,
                'raw_import': raw_import
            }
            
            # Only add header_row if not in raw import mode
            if not raw_import:
                import_settings['header_row'] = header_row
            
            # Add row limit for preview
            if max_rows:
                import_settings['nrows'] = max_rows
            
            # Use the importer's preview method if available, otherwise import directly
            if hasattr(import_manager, 'preview_file') and max_rows:
                result = import_manager.preview_file(file_path, max_rows, **import_settings)
            else:
                # Get the appropriate importer and import directly
                importer = import_manager.get_importer(file_path)
                if importer:
                    result = importer.import_file(file_path, **import_settings)
                else:
                    return {
                        'success': False,
                        'data': None,
                        'message': f"No importer available for file: {file_path}",
                        'statistics': None
                    }
            
            # Return the complete result structure that the calling code expects
            if result['success']:
                return {
                    'success': True,
                    'data': result['data'],
                    'message': result['message'],
                    'statistics': result.get('statistics', {})
                }
            else:
                return {
                    'success': False,
                    'data': None,
                    'message': result['message'],
                    'statistics': None
                }
            
        except Exception as e:
            print(f"Import error: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f"Import failed: {str(e)}",
                'statistics': None
            }

    def import_data(self):
        """Import the selected data files."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to import.")
            return
        
        dataset_name = self.dataset_name_var.get().strip()
        if not dataset_name:
            messagebox.showwarning("No Name", "Please enter a dataset name.")
            return
        
        try:
            self.progress_var.set("Starting import...")
            self.progress_bar['value'] = 0
            self.window.update()
            
            # Check if dataset name already exists
            existing_dataset = DatasetOperations.get_dataset_by_name(dataset_name)
            if existing_dataset:
                if not messagebox.askyesno("Dataset Exists", 
                                         f"Dataset '{dataset_name}' already exists. Continue anyway?"):
                    return
            
            total_files = len(self.selected_files)
            
            for i, file_path in enumerate(self.selected_files):
                self.progress_var.set(f"Processing file {i+1} of {total_files}: {os.path.basename(file_path)}")
                self.progress_bar['value'] = (i / total_files) * 100
                self.window.update()
                
                # Create dataset first to get ID for folder creation
                temp_dataset_id = DatasetOperations.create_dataset(
                    name=dataset_name if len(self.selected_files) == 1 else f"{dataset_name}_{i+1:03d}_{os.path.splitext(os.path.basename(file_path))[0]}",
                    file_path="temp_path",  # Will be updated after file copy
                    file_format=self.format_var.get(),
                    description=self.description_text.get(1.0, tk.END).strip(),
                    metadata={}  # Will be updated with import settings
                )
                
                # Create dataset folder structure
                folder_manager = DatasetFolderManager()
                dataset_folder = folder_manager.create_dataset_folder(
                    temp_dataset_id, 
                    dataset_name if len(self.selected_files) == 1 else f"{dataset_name}_{i+1:03d}"
                )
                
                # Determine final file path
                if self.copy_files_var.get():
                    # Copy to dataset's raw directory
                    raw_dir = folder_manager.get_raw_data_path(dataset_folder)
                    final_path = os.path.join(raw_dir, os.path.basename(file_path))
                    
                    # Copy file
                    if not os.path.exists(final_path) or os.path.getsize(file_path) != os.path.getsize(final_path):
                        import shutil
                        shutil.copy2(file_path, final_path)
                    
                    # Convert to absolute path to ensure 'Open File Location' works
                    final_path = os.path.abspath(final_path)
                else:
                    # For original files, still use absolute path but store folder info in metadata
                    final_path = os.path.abspath(file_path)
                
                # Test import with advanced settings to validate
                test_result = self.import_with_settings(file_path, max_rows=5)
                if not test_result['success']:
                    messagebox.showerror("Import Error", 
                                       f"Failed to import {os.path.basename(file_path)} with current settings:\n{test_result['message']}")
                    continue
                
                # Prepare metadata with import settings and folder info
                import_metadata = {
                    'import_source': file_path, 
                    'original_path': file_path,
                    'dataset_folder': dataset_folder,
                    'folder_structure': 'hybrid_v1',  # Version for future compatibility
                    'import_settings': {
                        'skip_rows': int(self.skip_rows_var.get()) if self.skip_rows_var.get().isdigit() else 0,
                        'header_row': int(self.header_row_var.get()) if self.header_row_var.get().isdigit() else 0,
                        'convert_numeric': self.convert_numeric_var.get(),
                        'handle_errors': self.handle_errors_var.get(),
                        'raw_import': self.raw_import_var.get()
                    },
                    'validation_result': test_result['statistics']
                }
                
                # Update the dataset with final file path and metadata
                if len(self.selected_files) > 1:
                    import_metadata.update({
                        'batch_name': dataset_name,
                        'file_index': i+1
                    })
                
                # Update the temporary dataset with correct information
                DatasetOperations.update_dataset(
                    temp_dataset_id,
                    file_path=final_path,
                    metadata=import_metadata
                )
            
            self.progress_var.set("Import completed successfully!")
            self.progress_bar['value'] = 100
            self.window.update()
            
            messagebox.showinfo("Success", f"Successfully imported {total_files} file(s) as dataset(s).")
            
            # Clear form
            self.clear_selection()
            self.dataset_name_var.set("")
            self.format_var.set("")
            self.description_text.delete(1.0, tk.END)
            
        except Exception as e:
            self.progress_var.set("Import failed!")
            messagebox.showerror("Import Error", f"Failed to import data: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    app = DataImportGUI()
    root.mainloop()
