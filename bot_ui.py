import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
import asyncio
import threading
import queue
import subprocess
import os

class StdoutRedirector:
    def __init__(self, queue):
        self._queue = queue
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

    def write(self, text):
        self._queue.put(text)
        self._original_stdout.write(text)  # Also write to terminal

    def flush(self):
        self._original_stdout.flush()

    def restore(self):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

class BotControlUI:
    def __init__(self):
        # Initialize queue before anything else
        self.log_queue = queue.Queue()
        
        # Setup stdout redirect immediately
        self.stdout_redirector = StdoutRedirector(self.log_queue)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stdout_redirector
        
        # Create UI elements
        self.root = tk.Tk()
        self.root.title("Discord Bot Control Panel")
        self.root.geometry("800x600")
        
        # Initialize bot variables
        self.bot = None
        self.bot_thread = None
        self.loop = None
        self.TOKEN = 'YOUR_BOT_TOKEN_HERE'
        
        self.DB_VIEWER_PATH = r"C:\Users\ericj\Documents\GitHub\DiscordBot\AURADiscordBot\AURA\tools\db_viewer.py"
        self.README_PATH = r"C:\Users\ericj\Documents\GitHub\DiscordBot\AURADiscordBot\AURA\README.md"
        
        # Setup UI
        self.setup_ui()
        self.setup_queue_handler()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("Bot Control UI started. Click 'Start Bot' to begin.")

    def setup_ui(self):
        # Control Frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10, padx=10, fill='x')

        self.start_button = ttk.Button(control_frame, text="Start Bot", command=self.start_bot)
        self.start_button.pack(side='left', padx=5)

        self.db_viewer_button = ttk.Button(control_frame, text="Open DB Viewer", command=self.open_db_viewer)
        self.db_viewer_button.pack(side='left', padx=5)

        self.readme_button = ttk.Button(control_frame, text="Open README", command=self.open_readme)
        self.readme_button.pack(side='left', padx=5)

        # Log Frame
        log_frame = ttk.LabelFrame(self.root, text="Bot Logs")
        log_frame.pack(pady=10, padx=10, fill='both', expand=True)

        # Configure the ScrolledText widget with a higher update frequency
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=30)
        self.log_text.pack(padx=5, pady=5, fill='both', expand=True)
        # Enable real-time updates
        self.log_text.configure(state='normal')

    def setup_queue_handler(self):
        def check_queue():
            while True:
                try:
                    message = self.log_queue.get_nowait()
                    # Delete the last line if it's a carriage return update
                    if message.startswith('\r'):
                        self.log_text.delete("end-2c linestart", "end-1c")
                    self.log_text.insert(tk.END, message)
                    self.log_text.see(tk.END)
                    # Force update the widget
                    self.log_text.update_idletasks()
                except queue.Empty:
                    break
            # Increase the check frequency to 10ms for smoother updates
            self.root.after(10, check_queue)
        
        self.root.after(10, check_queue)

    def start_bot(self):
        if self.bot is not None:
            return
            
        self.start_button.config(state='disabled')
        
        def run_bot():
            try:
                from bot import DiscordBot
                
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                self.bot = DiscordBot()
                self.loop.create_task(self.bot.start(self.TOKEN))
                print("Bot starting...")
                self.loop.run_forever()
            except Exception as e:
                print(f"Error starting bot: {str(e)}")
                self.start_button.config(state='normal')

        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()

    def on_closing(self):
        print("Shutting down...")
        if self.bot:
            print("Stopping bot...")
        self.stdout_redirector.restore()
        self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.stdout_redirector.restore()

    def open_db_viewer(self):
        try:
            subprocess.Popen([sys.executable, self.DB_VIEWER_PATH])
            print("Database viewer opened.")
        except Exception as e:
            print(f"Error opening database viewer: {str(e)}")

    def open_readme(self):
        try:
            os.startfile(self.README_PATH)
            print("README opened.")
        except Exception as e:
            print(f"Error opening README: {str(e)}")

if __name__ == "__main__":
    ui = BotControlUI()
    ui.run()