"""
Main Menu GUI - Central hub for the data processing pipeline.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.operations import DatasetOperations, ProcessingJobOperations
from src.database.connection import get_database


class MainMenuGUI:
    """Main menu interface for the data processing pipeline."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Glial Neuron Network Modelling - Data Processing Pipeline")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize database
        self.db = get_database()
        
        self.setup_ui()
        self.load_dashboard_data()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="Glial Neuron Network Modelling",
            font=("Arial", 20, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Data Processing Pipeline",
            font=("Arial", 12)
        )
        subtitle_label.pack()
        
        # Create main content area with notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Dashboard tab
        self.create_dashboard_tab()
        
        # Navigation buttons tab
        self.create_navigation_tab()
        
        # Settings tab
        self.create_settings_tab()
    
    def create_dashboard_tab(self):
        """Create the dashboard tab with overview information."""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(dashboard_frame, text="System Overview", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Create statistics labels
        self.stats_labels = {}
        stats_info = [
            ("total_datasets", "Total Datasets:"),
            ("active_jobs", "Active Jobs:"),
            ("completed_jobs", "Completed Jobs:"),
            ("total_figures", "Generated Figures:")
        ]
        
        for i, (key, label_text) in enumerate(stats_info):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(stats_frame, text=label_text).grid(row=row, column=col, sticky="w", padx=5)
            self.stats_labels[key] = ttk.Label(stats_frame, text="0", font=("Arial", 10, "bold"))
            self.stats_labels[key].grid(row=row, column=col+1, sticky="w", padx=5)
        
        # Recent activity frame
        activity_frame = ttk.LabelFrame(dashboard_frame, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Recent datasets listbox
        ttk.Label(activity_frame, text="Recent Datasets:").pack(anchor="w")
        
        self.recent_datasets_frame = ttk.Frame(activity_frame)
        self.recent_datasets_frame.pack(fill="both", expand=True, pady=5)
        
        self.recent_datasets_listbox = tk.Listbox(self.recent_datasets_frame, height=8)
        self.recent_datasets_listbox.pack(side="left", fill="both", expand=True)
        
        datasets_scrollbar = ttk.Scrollbar(self.recent_datasets_frame, orient="vertical")
        datasets_scrollbar.pack(side="right", fill="y")
        
        self.recent_datasets_listbox.config(yscrollcommand=datasets_scrollbar.set)
        datasets_scrollbar.config(command=self.recent_datasets_listbox.yview)
        
        # Refresh button
        ttk.Button(activity_frame, text="Refresh Dashboard", 
                  command=self.load_dashboard_data).pack(pady=10)
    
    def create_navigation_tab(self):
        """Create the navigation tab with buttons to open other GUIs."""
        nav_frame = ttk.Frame(self.notebook)
        self.notebook.add(nav_frame, text="Tools")
        
        # Main navigation buttons
        nav_buttons_frame = ttk.Frame(nav_frame)
        nav_buttons_frame.pack(expand=True)
        
        # Data Import button
        data_import_btn = ttk.Button(
            nav_buttons_frame,
            text="Data Import",
            command=self.open_data_import,
            width=20
        )
        data_import_btn.pack(pady=10)
        
        # Data Processing button
        processing_btn = ttk.Button(
            nav_buttons_frame,
            text="Data Processing",
            command=self.open_data_processing,
            width=20
        )
        processing_btn.pack(pady=10)
        
        # Figure Generation button
        figure_btn = ttk.Button(
            nav_buttons_frame,
            text="Figure Generation",
            command=self.open_figure_generation,
            width=20
        )
        figure_btn.pack(pady=10)
        
        # Data Browser button
        browser_btn = ttk.Button(
            nav_buttons_frame,
            text="Data Browser",
            command=self.open_data_browser,
            width=20
        )
        browser_btn.pack(pady=10)
        
        # Analysis Results button
        results_btn = ttk.Button(
            nav_buttons_frame,
            text="Analysis Results",
            command=self.open_analysis_results,
            width=20
        )
        results_btn.pack(pady=10)
    
    def create_settings_tab(self):
        """Create the settings tab."""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Database info
        db_frame = ttk.LabelFrame(settings_frame, text="Database Information", padding=10)
        db_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(db_frame, text="View Database Info", 
                  command=self.show_database_info).pack(pady=5)
        
        ttk.Button(db_frame, text="Backup Database", 
                  command=self.backup_database).pack(pady=5)
        
        # Application settings
        app_frame = ttk.LabelFrame(settings_frame, text="Application Settings", padding=10)
        app_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(app_frame, text="Theme:").grid(row=0, column=0, sticky="w", padx=5)
        self.theme_var = tk.StringVar(value="light")
        theme_combo = ttk.Combobox(app_frame, textvariable=self.theme_var, 
                                  values=["light", "dark"], state="readonly")
        theme_combo.grid(row=0, column=1, padx=5)
        
        ttk.Button(app_frame, text="Apply Settings", 
                  command=self.apply_settings).grid(row=1, column=0, columnspan=2, pady=10)
    
    def load_dashboard_data(self):
        """Load and display dashboard statistics."""
        try:
            # Get statistics
            datasets = DatasetOperations.list_datasets()
            active_jobs = ProcessingJobOperations.get_active_jobs()
            
            # Update statistics labels
            self.stats_labels["total_datasets"].config(text=str(len(datasets)))
            self.stats_labels["active_jobs"].config(text=str(len(active_jobs)))
            
            # Get completed jobs count
            completed_jobs_query = """
                SELECT COUNT(*) FROM processing_jobs WHERE status = 'completed'
            """
            completed_count = self.db.execute_one(completed_jobs_query)
            self.stats_labels["completed_jobs"].config(
                text=str(completed_count[0] if completed_count else 0)
            )
            
            # Get figures count
            figures_query = "SELECT COUNT(*) FROM figures"
            figures_count = self.db.execute_one(figures_query)
            self.stats_labels["total_figures"].config(
                text=str(figures_count[0] if figures_count else 0)
            )
            
            # Update recent datasets list
            self.recent_datasets_listbox.delete(0, tk.END)
            for dataset in datasets[:10]:  # Show last 10 datasets
                display_text = f"{dataset.name} ({dataset.file_format or 'unknown'}) - {dataset.import_date.strftime('%Y-%m-%d %H:%M') if dataset.import_date else 'No date'}"
                self.recent_datasets_listbox.insert(tk.END, display_text)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dashboard data: {str(e)}")
    
    def show_database_info(self):
        """Show database information dialog."""
        try:
            db_info = self.db.get_database_info()
            
            info_text = f"""Database Information:
            
Path: {db_info['database_path']}
Size: {db_info['database_size_bytes']} bytes
Last Modified: {db_info['last_modified']}

Tables and Row Counts:
"""
            for table, count in db_info['table_row_counts'].items():
                info_text += f"  {table}: {count} rows\n"
            
            messagebox.showinfo("Database Information", info_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get database info: {str(e)}")
    
    def backup_database(self):
        """Create a database backup."""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            default_name = f"pipeline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = filedialog.asksaveasfilename(
                title="Save Database Backup",
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                initialvalue=default_name
            )
            
            if backup_path:
                self.db.backup_database(backup_path)
                messagebox.showinfo("Success", f"Database backed up to: {backup_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup database: {str(e)}")
    
    def apply_settings(self):
        """Apply application settings."""
        # This would normally save settings to database
        messagebox.showinfo("Settings", "Settings applied successfully!")
    
    def open_data_import(self):
        """Open the data import GUI."""
        try:
            from .data_import_gui import DataImportGUI
            DataImportGUI()
        except ImportError:
            messagebox.showinfo("Coming Soon", "Data Import GUI will be implemented soon!")
    
    def open_data_processing(self):
        """Open the data processing GUI."""
        try:
            from .data_processing_gui import DataProcessingGUI
            DataProcessingGUI()
        except ImportError:
            messagebox.showinfo("Coming Soon", "Data Processing GUI will be implemented soon!")
    
    def open_figure_generation(self):
        """Open the figure generation GUI."""
        try:
            from .figure_generation_gui import FigureGenerationGUI
            FigureGenerationGUI()
        except ImportError:
            messagebox.showinfo("Coming Soon", "Figure Generation GUI will be implemented soon!")
    
    def open_data_browser(self):
        """Open the data browser GUI."""
        try:
            from .data_browser_gui import DataBrowserGUI
            DataBrowserGUI()
        except ImportError:
            messagebox.showinfo("Coming Soon", "Data Browser GUI will be implemented soon!")
    
    def open_analysis_results(self):
        """Open the analysis results GUI."""
        try:
            from .analysis_results_gui import AnalysisResultsGUI
            AnalysisResultsGUI()
        except ImportError:
            messagebox.showinfo("Coming Soon", "Analysis Results GUI will be implemented soon!")
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainMenuGUI()
    app.run()
