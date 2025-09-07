"""
Database selection GUI for choosing workspace locations.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path
from typing import Optional, Dict, Any

from ..database.workspace import get_workspace_manager, DatabaseWorkspace


class DatabaseSelectionGUI:
    """GUI for selecting and managing database workspaces."""
    
    def __init__(self, parent=None, callback=None):
        """Initialize database selection GUI.
        
        Args:
            parent: Parent window (optional)
            callback: Function to call when workspace is changed (optional)
        """
        self.parent = parent
        self.callback = callback
        
        # Create window
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Choose Database Workspace")
        self.window.geometry("700x500")
        self.window.configure(bg='#f0f0f0')
        
        # Make window modal if parent exists
        if parent:
            self.window.transient(parent)
            self.window.grab_set()
        
        # Center window
        self.center_window()
        
        # Get workspace manager
        self.workspace_manager = get_workspace_manager()
        
        # Variables
        self.selected_path = tk.StringVar()
        self.workspace_info_text = tk.StringVar()
        
        # Setup UI
        self.setup_ui()
        self.load_current_workspace()
    
    def center_window(self):
        """Center the window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_frame = ttk.Frame(self.window)
        title_frame.pack(pady=10, padx=20, fill="x")
        
        title_label = ttk.Label(
            title_frame,
            text="Choose Database Workspace",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Select the folder containing your database and datasets",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Current workspace frame
        current_frame = ttk.LabelFrame(self.window, text="Current Workspace", padding=10)
        current_frame.pack(pady=10, padx=20, fill="x")
        
        # Current path display
        path_frame = ttk.Frame(current_frame)
        path_frame.pack(fill="x", pady=5)
        
        ttk.Label(path_frame, text="Location:").pack(side="left")
        self.current_path_label = ttk.Label(
            path_frame, 
            textvariable=self.selected_path,
            font=("Courier", 9),
            foreground="blue"
        )
        self.current_path_label.pack(side="left", padx=(10, 0))
        
        # Workspace info display
        info_frame = ttk.Frame(current_frame)
        info_frame.pack(fill="both", expand=True, pady=5)
        
        self.info_text = tk.Text(
            info_frame,
            height=6,
            width=70,
            wrap=tk.WORD,
            font=("Courier", 9),
            state=tk.DISABLED
        )
        self.info_text.pack(side="left", fill="both", expand=True)
        
        info_scrollbar = ttk.Scrollbar(info_frame, orient="vertical")
        info_scrollbar.pack(side="right", fill="y")
        
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        info_scrollbar.config(command=self.info_text.yview)
        
        # File browser frame
        browser_frame = ttk.LabelFrame(self.window, text="Browse Contents", padding=10)
        browser_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Create treeview for file browser
        tree_frame = ttk.Frame(browser_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.file_tree = ttk.Treeview(tree_frame, columns=("type", "size"), show="tree headings")
        self.file_tree.heading("#0", text="Name")
        self.file_tree.heading("type", text="Type")
        self.file_tree.heading("size", text="Size")
        
        self.file_tree.column("#0", width=300)
        self.file_tree.column("type", width=100)
        self.file_tree.column("size", width=100)
        
        self.file_tree.pack(side="left", fill="both", expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")
        
        self.file_tree.config(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.file_tree.yview)
        
        # Action buttons frame
        actions_frame = ttk.LabelFrame(self.window, text="Actions", padding=10)
        actions_frame.pack(pady=10, padx=20, fill="x")
        
        buttons_frame = ttk.Frame(actions_frame)
        buttons_frame.pack()
        
        # Select new database folder button
        select_btn = ttk.Button(
            buttons_frame,
            text="Select New Database Folder",
            command=self.select_database_folder,
            width=25
        )
        select_btn.pack(side="left", padx=5)
        
        # Generate new database folder button
        generate_btn = ttk.Button(
            buttons_frame,
            text="Generate New Database Folder",
            command=self.generate_database_folder,
            width=25
        )
        generate_btn.pack(side="left", padx=5)
        
        # Bottom buttons frame
        bottom_frame = ttk.Frame(self.window)
        bottom_frame.pack(pady=10, padx=20, fill="x")
        
        # Refresh button
        refresh_btn = ttk.Button(
            bottom_frame,
            text="Refresh",
            command=self.refresh_display,
            width=15
        )
        refresh_btn.pack(side="left")
        
        # Close button
        close_btn = ttk.Button(
            bottom_frame,
            text="Close",
            command=self.close_window,
            width=15
        )
        close_btn.pack(side="right")
    
    def load_current_workspace(self):
        """Load and display current workspace information."""
        try:
            workspace_info = self.workspace_manager.get_workspace_info()
            
            if 'error' in workspace_info:
                self.selected_path.set("No workspace selected")
                self.update_info_display("Error: " + workspace_info['error'])
                return
            
            # Update path display
            self.selected_path.set(workspace_info['workspace_path'])
            
            # Update info display
            self.update_workspace_info(workspace_info)
            
            # Update file browser
            self.update_file_browser(workspace_info['workspace_path'])
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load workspace information: {str(e)}")
    
    def update_workspace_info(self, workspace_info: Dict[str, Any]):
        """Update workspace information display."""
        validation = workspace_info.get('validation', {})
        
        info_lines = [
            f"Workspace Path: {workspace_info.get('workspace_path', 'Unknown')}",
            f"Database Path: {workspace_info.get('database_path', 'Unknown')}",
            f"Datasets Path: {workspace_info.get('datasets_path', 'Unknown')}",
            "",
            "Validation Status:",
            f"  Valid: {'Yes' if validation.get('is_valid', False) else 'No'}",
            f"  Has Database: {'Yes' if validation.get('has_database', False) else 'No'}",
            f"  Has Datasets Folder: {'Yes' if validation.get('has_datasets_folder', False) else 'No'}",
            f"  Database Size: {validation.get('database_size', 0):,} bytes",
            f"  Dataset Count: {validation.get('dataset_count', 0)}",
        ]
        
        if validation.get('issues'):
            info_lines.append("")
            info_lines.append("Issues:")
            for issue in validation['issues']:
                info_lines.append(f"  - {issue}")
        
        info_text = "\n".join(info_lines)
        self.update_info_display(info_text)
    
    def update_info_display(self, text: str):
        """Update the info text display."""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)
        self.info_text.config(state=tk.DISABLED)
    
    def update_file_browser(self, workspace_path: str):
        """Update file browser with workspace contents."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        try:
            workspace_path = Path(workspace_path)
            if not workspace_path.exists():
                return
            
            # Add items to tree
            for item in sorted(workspace_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                
                item_type = "File" if item.is_file() else "Folder"
                
                if item.is_file():
                    size = f"{item.stat().st_size:,} bytes"
                else:
                    try:
                        # Count items in folder
                        item_count = len(list(item.iterdir()))
                        size = f"{item_count} items"
                    except (PermissionError, OSError):
                        size = "Access denied"
                
                # Highlight important files/folders
                tags = []
                if item.name == "pipeline.db":
                    tags.append("database")
                elif item.name == "datasets":
                    tags.append("datasets")
                
                self.file_tree.insert(
                    "",
                    "end",
                    text=item.name,
                    values=(item_type, size),
                    tags=tags
                )
            
            # Configure tags for highlighting
            self.file_tree.tag_configure("database", background="#e6ffe6")
            self.file_tree.tag_configure("datasets", background="#e6f3ff")
            
        except Exception as e:
            print(f"Error updating file browser: {e}")
    
    def select_database_folder(self):
        """Open dialog to select existing database folder."""
        folder_path = filedialog.askdirectory(
            title="Select Database Folder",
            initialdir=self.selected_path.get() or os.path.expanduser("~")
        )
        
        if not folder_path:
            return
        
        # Validate the selected folder
        workspace = DatabaseWorkspace(folder_path)
        validation = workspace.validate_workspace()
        
        if not validation['has_database']:
            # Ask if user wants to create database in this folder
            result = messagebox.askyesno(
                "No Database Found",
                f"No database file found in:\n{folder_path}\n\n"
                "Would you like to create a new database in this folder?"
            )
            
            if result:
                if not workspace.initialize_workspace(create_missing=True):
                    messagebox.showerror(
                        "Error",
                        "Failed to create database in selected folder."
                    )
                    return
            else:
                return
        
        # Set the new workspace
        if self.workspace_manager.set_workspace(folder_path):
            messagebox.showinfo(
                "Success",
                f"Successfully switched to database workspace:\n{folder_path}"
            )
            self.load_current_workspace()
            
            # Call callback if provided
            if self.callback:
                self.callback()
        else:
            messagebox.showerror(
                "Error",
                "Failed to switch to selected workspace."
            )
    
    def generate_database_folder(self):
        """Open dialog to create new database folder."""
        folder_path = filedialog.askdirectory(
            title="Select Parent Folder for New Database",
            initialdir=os.path.expanduser("~")
        )
        
        if not folder_path:
            return
        
        # Ask for folder name
        folder_name = tk.simpledialog.askstring(
            "Folder Name",
            "Enter name for new database folder:",
            initialvalue="my_database"
        )
        
        if not folder_name:
            return
        
        # Create full path
        new_workspace_path = Path(folder_path) / folder_name
        
        # Check if folder already exists
        if new_workspace_path.exists():
            if not messagebox.askyesno(
                "Folder Exists",
                f"Folder '{folder_name}' already exists in:\n{folder_path}\n\n"
                "Continue anyway?"
            ):
                return
        
        # Create new workspace
        if self.workspace_manager.create_new_workspace(str(new_workspace_path)):
            messagebox.showinfo(
                "Success",
                f"Successfully created new database workspace:\n{new_workspace_path}"
            )
            self.load_current_workspace()
            
            # Call callback if provided
            if self.callback:
                self.callback()
        else:
            messagebox.showerror(
                "Error",
                "Failed to create new workspace."
            )
    
    def refresh_display(self):
        """Refresh the workspace display."""
        self.load_current_workspace()
    
    def close_window(self):
        """Close the window."""
        if self.parent:
            self.window.grab_release()
        self.window.destroy()
    
    def run(self):
        """Run the GUI (if standalone)."""
        if not self.parent:
            self.window.mainloop()


# Add missing import for simpledialog
import tkinter.simpledialog


if __name__ == "__main__":
    # Test the GUI
    app = DatabaseSelectionGUI()
    app.run()
