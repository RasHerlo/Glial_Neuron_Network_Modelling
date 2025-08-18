"""
Figure Generation GUI - Interface for creating visualizations and figures.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, FigureOperations, ProcessingJobOperations


class FigureGenerationGUI:
    """GUI for figure generation functionality."""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Figure Generation")
        self.window.geometry("900x700")
        self.window.configure(bg='#f0f0f0')
        
        self.selected_dataset = None
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
