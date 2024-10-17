import random
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path

# Define the path to your database file
db_path = Path('C:/Users/ericj/Documents/GitHub/DiscordBot/DiscordBot/group_memories/aura_memory.db')

class DatabaseViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("AURA Database Viewer")

        # Create UI components
        self.create_widgets()

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

    def connect_db(self):
        """Connect to the SQLite database."""
        try:
            conn = sqlite3.connect(db_path)
            return conn
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to the database: {e}")
            return None

    def display_table_data(self, event=None):
        """Fetch and display data from the selected table."""
        table_name = self.table_var.get()

        # Clear the tree view
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch data from the database
        conn = self.connect_db()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]

            # Set up the Treeview columns and headings
            self.tree['columns'] = columns
            self.tree["show"] = "headings"  # Hide the first empty column
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, minwidth=50, stretch=True)

            # Insert rows
            rows = cursor.fetchall()
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

# Create the Tkinter window and run the application
if __name__ == "__main__":
    root = tk.Tk()
    viewer = DatabaseViewer(root)
    root.geometry("800x600")  # Set initial window size
    root.mainloop()
