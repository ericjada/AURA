import random
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path
from typing import Union, Any
import json
import shutil
from datetime import datetime
import time

# Replace hard-coded db_path with config-based path
def get_db_path():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return Path(config.get('database_path', 'group_memories/aura_memory.db'))
    except FileNotFoundError:
        return Path('group_memories/aura_memory.db')

db_path = get_db_path()

class DatabaseViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("AURA Database Viewer")

        # Add style configuration
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=25)
        self.style.map('Treeview', background=[('alternate', '#f0f0f0')])

        # Add check for database existence
        if not db_path.exists():
            messagebox.showerror("Error", f"Database file not found at {db_path}")
            root.destroy()
            return

        # Create UI components
        self.create_widgets()

        # Add backup directory
        self.backup_dir = Path('database_backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        # Add edit mode tracking
        self.edit_mode = False

    def create_widgets(self):
        # Table selection dropdown
        self.table_label = tk.Label(self.root, text="Select Table:")
        self.table_label.grid(row=0, column=0, padx=10, pady=10)

        self.table_var = tk.StringVar()
        self.table_dropdown = ttk.Combobox(self.root, textvariable=self.table_var, state="readonly")
        self.table_dropdown['values'] = ("guilds", "memories", "user_profiles", "logs", "auracoin_ledger", "blackjack_game")  # Added new tables
        self.table_dropdown.grid(row=0, column=1, padx=10, pady=10)
        self.table_dropdown.bind("<<ComboboxSelected>>", self.display_table_data)

        # Display Button
        self.display_button = tk.Button(self.root, text="Display Data", command=self.display_table_data)
        self.display_button.grid(row=0, column=2, padx=10, pady=10)

        # Treeview (Table to display data)
        self.tree = ttk.Treeview(self.root)
        self.tree.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.tree.bind("<Double-1>", self.show_full_content)  # Bind double-click event to show full content

        # Add vertical scrollbar
        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=1, column=3, sticky='ns')

        # Delete selected row button
        self.delete_button = tk.Button(self.root, text="Delete Selected Row", command=self.delete_selected_row)
        self.delete_button.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

        # Configure grid weight for resizing
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

        # Add search frame
        self.search_frame = ttk.Frame(self.root)
        self.search_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_label.pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_var.trace('w', self.filter_table_data)

        # Add export button
        self.export_button = ttk.Button(self.root, text="Export to CSV", command=self.export_to_csv)
        self.export_button.grid(row=2, column=2, padx=10, pady=10)

        # Add refresh button
        self.refresh_button = ttk.Button(self.root, text="Refresh", command=self.display_table_data)
        self.refresh_button.grid(row=0, column=3, padx=10, pady=10)

        # Configure the Treeview for sorting
        self.tree.bind('<Button-1>', self.handle_click)
        self.sort_reverse = False
        self.last_sort_col = None

        # Add edit mode toggle button
        self.edit_button = ttk.Button(self.root, text="Toggle Edit Mode", command=self.toggle_edit_mode)
        self.edit_button.grid(row=2, column=3, padx=10, pady=10)
        
        # Make columns resizable
        self.tree.bind('<ButtonRelease-1>', self.handle_click)
        self.tree.bind('<Motion>', self.handle_motion)
        self.resize_column = None

    def connect_db(self):
        """Connect to the SQLite database with retry logic."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                conn = sqlite3.connect(db_path, timeout=5)
                return conn
            except sqlite3.Error as e:
                if attempt == max_attempts - 1:
                    messagebox.showerror("Database Error", f"Failed to connect after {max_attempts} attempts: {e}")
                    return None
                time.sleep(1)  # Wait before retry

    def get_table_list(self):
        """Dynamically fetch available tables from the database."""
        conn = self.connect_db()
        if not conn:
            return []
        
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Failed to fetch tables: {e}")
            return []
        finally:
            conn.close()

    def create_backup(self):
        """Create a backup of the database before making changes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"aura_memory_backup_{timestamp}.db"
        try:
            shutil.copy2(db_path, backup_path)
            return True
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to create backup: {e}")
            return False

    def toggle_edit_mode(self):
        """Toggle edit mode for the table."""
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.tree.bind('<Double-1>', self.edit_cell)
            self.edit_button.configure(text="Exit Edit Mode")
        else:
            self.tree.bind('<Double-1>', self.show_full_content)
            self.edit_button.configure(text="Enter Edit Mode")

    def edit_cell(self, event):
        """Handle cell editing."""
        if not self.edit_mode:
            return
            
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        col_name = self.tree["columns"][int(column[1]) - 1]
        
        # Don't allow editing of primary key columns
        if col_name in self.get_primary_key_columns():
            messagebox.showwarning("Edit Error", "Cannot edit primary key column")
            return
            
        # Create edit popup
        value = self.tree.set(item, column)
        popup = tk.Toplevel(self.root)
        popup.title(f"Edit {col_name}")
        
        entry = ttk.Entry(popup)
        entry.insert(0, value)
        entry.pack(padx=10, pady=5)
        
        def save_edit():
            new_value = entry.get()
            if self.update_database_value(item, col_name, new_value):
                self.tree.set(item, column, new_value)
            popup.destroy()
            
        save_button = ttk.Button(popup, text="Save", command=save_edit)
        save_button.pack(pady=5)

    def update_database_value(self, item, column, new_value):
        """Update a value in the database."""
        table_name = self.table_var.get()
        primary_key_col = self.get_primary_key_columns().get(table_name)
        primary_key_val = self.tree.item(item)['values'][0]
        
        if self.create_backup():
            conn = self.connect_db()
            if not conn:
                return False
                
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE {table_name} SET {column} = ? WHERE {primary_key_col} = ?",
                    (new_value, primary_key_val)
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                messagebox.showerror("Update Error", f"Failed to update database: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_primary_key_columns(self):
        """Return dictionary of primary key columns for each table."""
        return {
            "guilds": "guild_id",
            "memories": "memory_id",
            "user_profiles": "profile_id",
            "logs": "log_id",
            "auracoin_ledger": "transaction_id",
            "blackjack_game": "game_id"
        }

    def display_table_data(self, event=None):
        """Fetch and display data from the selected table."""
        table_name = self.table_var.get()
        if not table_name:  # Add check for selected table
            messagebox.showwarning("Selection Error", "Please select a table first")
            return

        # Clear the tree view
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch data from the database
        conn = self.connect_db()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            # First check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if not cursor.fetchone():
                messagebox.showerror("Table Error", f"Table '{table_name}' does not exist in the database")
                return

            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            table_info = cursor.fetchall()
            print(f"Table structure for {table_name}:")  # Debug info
            for col in table_info:
                print(f"Column: {col}")  # Debug info

            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            print(f"Found {len(rows)} rows in {table_name}")  # Debug info

            # Set up the Treeview columns and headings
            self.tree['columns'] = columns
            self.tree["show"] = "headings"  # Hide the first empty column
            for col in columns:
                self.tree.heading(col, text=col)
                max_width = len(str(col)) * 10  # Base width on header
                
                # Check content width
                for row in rows:
                    cell_width = len(str(row[columns.index(col)])) * 10
                    max_width = max(max_width, cell_width)
                
                # Cap maximum width at 300 pixels
                max_width = min(max_width, 300)
                self.tree.column(col, minwidth=50, width=max_width, stretch=True)

            # Insert rows
            for row in rows:
                self.tree.insert("", "end", values=row)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to retrieve data: {e}")
        finally:
            conn.close()

    def delete_selected_row(self):
        """Delete the selected row from the currently displayed table."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "No row selected for deletion.")
            return

        table_name = self.table_var.get()
        item_values = self.tree.item(selected_item)['values']

        # Fetch the primary key column for each table
        primary_key_column = {
            "guilds": "guild_id",
            "memories": "memory_id",
            "user_profiles": "profile_id",
            "logs": "log_id",
            "auracoin_ledger": "transaction_id",  # Added auracoin_ledger primary key
            "blackjack_game": "game_id"  # Added blackjack_game primary key
        }

        primary_key = primary_key_column.get(table_name)
        if not primary_key:
            messagebox.showerror("Error", "Unknown table selected.")
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the selected row from {table_name}?"):
            return

        # Delete the row from the database
        conn = self.connect_db()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key} = ?", (item_values[0],))
            conn.commit()
            messagebox.showinfo("Success", "Row deleted successfully.")
            self.display_table_data()  # Refresh table data after deletion
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete row: {e}")
        finally:
            conn.close()

    def show_full_content(self, event):
        """Show the full content of a selected row in a pop-up window."""
        selected_item = self.tree.selection()
        if not selected_item:
            return

        # Get the entire row's content
        item_values = self.tree.item(selected_item)['values']

        # Create a new pop-up window to display the full row content
        popup = tk.Toplevel(self.root)
        popup.title("Full Row Content")

        # Add a Text widget and Scrollbar for the content
        text_frame = tk.Frame(popup)
        text_frame.pack(expand=True, fill="both")

        text_widget = tk.Text(text_frame, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        # Insert the full row's content as text
        full_content = "\n".join([f"{col}: {val}" for col, val in zip(self.tree["columns"], item_values)])
        text_widget.insert("1.0", full_content)
        text_widget.config(state=tk.DISABLED)  # Make the text widget read-only

        # Pack the Text widget and Scrollbar
        text_widget.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Set a good size for the popup window and bring it to the front
        popup.geometry("600x400")  # Set a reasonable size for the popup window
        popup.lift()  # Bring the pop-up window to the front

    def handle_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "heading":
            column = self.tree.identify_column(event.x)
            column_id = self.tree["columns"][int(column[1]) - 1]
            self.sort_treeview_column(column_id)

    def sort_treeview_column(self, col):
        """Enhanced sorting with type handling."""
        if self.last_sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
        
        self.last_sort_col = col
        
        def convert_value(value: str) -> Union[int, float, str]:
            """Convert string value to appropriate type for sorting."""
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return str(value).lower()
        
        items = [(convert_value(self.tree.set(item, col)), item) for item in self.tree.get_children('')]
        items.sort(reverse=self.sort_reverse, key=lambda x: x[0])
        
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

    def filter_table_data(self, *args):
        """Filter table data based on search input."""
        search_term = self.search_var.get().lower()
        
        for item in self.tree.get_children():
            values = [str(v).lower() for v in self.tree.item(item)['values']]
            if any(search_term in value for value in values):
                self.tree.item(item, tags=())
            else:
                self.tree.item(item, tags=('hidden',))
        
        self.tree.tag_configure('hidden', hide=True)

    def export_to_csv(self):
        """Export the current table view to a CSV file."""
        import csv
        from tkinter import filedialog
        
        table_name = self.table_var.get()
        filename = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"{table_name}_export.csv"
        )
        
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write headers
                writer.writerow(self.tree["columns"])
                # Write data
                for item in self.tree.get_children():
                    if not self.tree.tag_has('hidden', item):
                        writer.writerow(self.tree.item(item)['values'])
            messagebox.showinfo("Export Complete", f"Data exported to {filename}")

    def handle_motion(self, event):
        """Handle mouse motion for column resizing."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            self.tree.config(cursor="sb_h_double_arrow")
        else:
            self.tree.config(cursor="")

# Create the Tkinter window and run the application
if __name__ == "__main__":
    root = tk.Tk()
    viewer = DatabaseViewer(root)
    root.geometry("800x600")  # Set initial window size
    root.mainloop()
