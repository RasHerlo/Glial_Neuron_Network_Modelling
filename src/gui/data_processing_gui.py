"""
Data Processing GUI - Interface for processing datasets.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import threading
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, ProcessingJobOperations


class DataProcessingGUI:
    """GUI for data processing functionality."""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Data Processing")
        self.window.geometry("800x600")
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
        processing_combo = ttk.Combobox(processing_frame, textvariable=self.processing_type_var,
                                       values=["Data Cleaning", "Smoothing", "Filtering", 
                                              "Feature Extraction", "Statistical Analysis", 
                                              "Custom Processing"], 
                                       state="readonly", width=30)
        processing_combo.grid(row=0, column=1, padx=5, pady=2)
        processing_combo.bind('<<ComboboxSelected>>', self.on_processing_type_change)
        
        # Job name
        ttk.Label(processing_frame, text="Job Name:").grid(row=1, column=0, sticky="w", padx=5)
        self.job_name_var = tk.StringVar()
        job_name_entry = ttk.Entry(processing_frame, textvariable=self.job_name_var, width=32)
        job_name_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Parameters frame
        params_frame = ttk.LabelFrame(processing_frame, text="Parameters", padding=5)
        params_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Dynamic parameters based on processing type
        self.params_frame = ttk.Frame(params_frame)
        self.params_frame.pack(fill="both", expand=True)
        
        self.param_vars = {}
        self.create_default_params()
        
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
        
        ttk.Button(action_frame, text="Start Processing", 
                  command=self.start_processing).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Refresh Jobs", 
                  command=self.refresh_jobs).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Cancel Selected Job", 
                  command=self.cancel_job).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Close", 
                  command=self.window.destroy).pack(side="right", padx=5)
        
        # Start job refresh timer
        self.refresh_jobs()
        self.schedule_job_refresh()
    
    def create_default_params(self):
        """Create default parameter widgets."""
        # Clear existing params
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        
        # Default parameters
        params = [
            ("smoothing_factor", "Smoothing Factor:", "0.5", "float"),
            ("window_size", "Window Size:", "10", "int"),
            ("threshold", "Threshold:", "0.1", "float"),
            ("normalize", "Normalize Data:", True, "bool")
        ]
        
        for i, (key, label, default, param_type) in enumerate(params):
            ttk.Label(self.params_frame, text=label).grid(row=i, column=0, sticky="w", padx=5)
            
            if param_type == "bool":
                self.param_vars[key] = tk.BooleanVar(value=default)
                ttk.Checkbutton(self.params_frame, variable=self.param_vars[key]).grid(
                    row=i, column=1, sticky="w", padx=5)
            else:
                self.param_vars[key] = tk.StringVar(value=str(default))
                ttk.Entry(self.params_frame, textvariable=self.param_vars[key], 
                         width=20).grid(row=i, column=1, padx=5)
    
    def on_processing_type_change(self, event=None):
        """Update parameters based on processing type."""
        processing_type = self.processing_type_var.get()
        
        # Auto-fill job name if empty
        if not self.job_name_var.get() and self.selected_dataset:
            self.job_name_var.set(f"{processing_type}_{self.selected_dataset.name}")
        
        # You could customize parameters based on processing type here
        # For now, we'll keep the default parameters
    
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
    
    def start_processing(self):
        """Start a processing job."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset to process.")
            return
        
        processing_type = self.processing_type_var.get()
        if not processing_type:
            messagebox.showwarning("No Processing Type", "Please select a processing type.")
            return
        
        job_name = self.job_name_var.get().strip()
        if not job_name:
            messagebox.showwarning("No Job Name", "Please enter a job name.")
            return
        
        try:
            # Collect parameters
            parameters = {}
            for key, var in self.param_vars.items():
                if isinstance(var, tk.BooleanVar):
                    parameters[key] = var.get()
                else:
                    value = var.get()
                    # Try to convert to appropriate type
                    try:
                        if '.' in value:
                            parameters[key] = float(value)
                        else:
                            parameters[key] = int(value)
                    except ValueError:
                        parameters[key] = value
            
            # Create processing job
            job_id = ProcessingJobOperations.create_job(
                dataset_id=self.selected_dataset.id,
                job_name=job_name,
                job_type=processing_type,
                parameters=parameters
            )
            
            # Start processing in background thread
            ProcessingJobOperations.update_job_status(job_id, "running", progress=0.0)
            
            # Simulate processing with a background thread
            threading.Thread(target=self.simulate_processing, args=(job_id,), daemon=True).start()
            
            messagebox.showinfo("Success", f"Processing job '{job_name}' started successfully!")
            self.refresh_jobs()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start processing: {str(e)}")
    
    def simulate_processing(self, job_id):
        """Simulate processing job progress."""
        try:
            # Simulate processing steps
            steps = ["Initializing", "Loading data", "Processing", "Analyzing", "Saving results"]
            
            for i, step in enumerate(steps):
                time.sleep(2)  # Simulate work
                progress = (i + 1) / len(steps) * 100
                ProcessingJobOperations.update_job_status(job_id, "running", progress=progress)
                
                # Update GUI in main thread
                self.window.after(0, self.refresh_jobs)
            
            # Complete the job
            ProcessingJobOperations.update_job_status(
                job_id, "completed", progress=100.0, 
                output_path=f"data/processed/job_{job_id}_output.csv"
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
    
    def schedule_job_refresh(self):
        """Schedule periodic job refresh."""
        self.refresh_jobs()
        self.window.after(5000, self.schedule_job_refresh)  # Refresh every 5 seconds


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    app = DataProcessingGUI()
    root.mainloop()
