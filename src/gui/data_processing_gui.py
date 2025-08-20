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
                                       values=["Matrix Extraction"], 
                                       state="readonly", width=30)
        processing_combo.grid(row=0, column=1, padx=5, pady=2)
        processing_combo.bind('<<ComboboxSelected>>', self.on_processing_type_change)
        

        
        # Parameters frame
        params_frame = ttk.LabelFrame(processing_frame, text="Parameters", padding=5)
        params_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
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
        
        ttk.Button(action_frame, text="Preview Matrix", 
                  command=self.preview_matrix).pack(side="left", padx=5)
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
    
    def create_default_params(self):
        """Create default parameter widgets."""
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
    
    def on_processing_type_change(self, event=None):
        """Update parameters based on processing type."""
        processing_type = self.processing_type_var.get()
        
        # Matrix Extraction parameters are already set in create_default_params
        # Could add dynamic parameter updates here if needed
    
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
            
            # Generate job name from matrix name
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
        """Preview the matrix extraction."""
        if not self.selected_dataset:
            messagebox.showwarning("No Dataset", "Please select a dataset to preview.")
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
