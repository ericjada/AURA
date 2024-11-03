import discord
import ollama
import json
import os
import asyncio
import subprocess
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction
import aiofiles  # Import aiofiles for asynchronous file operations

class Chat(commands.Cog):
    """
    A Discord cog that allows users to chat with the LLaMA model.
    Users can send messages to the model, set a system prompt, 
    and manage their conversation memory.
    """

    def __init__(self, bot):
        """
        Initialize the Chat cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.model = "llama3.2"  # Specify the LLaMA model to use
        self.memory_directory = {
            'individual': 'user_memories',
        }
        os.makedirs(self.memory_directory['individual'], exist_ok=True)
        self.default_system_prompt = "You are a helpful assistant."  # Default system message

        # Initialize SQLite database connection
        self.db_path = './group_memories/aura_memory.db'
        self.conn = self._create_db_connection()
        self._initialize_group_tables()

        # Start ollama serve when the bot is initialized
        self.start_ollama_serve()

    def _create_db_connection(self):
        """Creates a new database connection with proper row factory."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def start_ollama_serve(self):
        """Starts the ollama serve process in the background if it's not already running."""
        try:
            # Check if the 'ollama' process is already running
            result = subprocess.run(['tasklist'], capture_output=True, text=True)
            if 'ollama.exe' not in result.stdout and 'ollama' not in result.stdout:
                subprocess.Popen(['ollama', 'serve'])  # Start the ollama serve process
                print("Ollama serve has been started.")
            else:
                print("Ollama serve is already running.")
        except Exception as e:
            print(f"Failed to start ollama serve: {str(e)}")

    def load_memory(self, user_id):
        """Loads the conversation history and system prompt from a user's file.

        Args:
            user_id: The ID of the user whose memory is being loaded.

        Returns:
            dict: A dictionary containing user's name, history, and system prompt.
        """
        memory_file = os.path.join(self.memory_directory['individual'], f'{user_id}.json')
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as file:
                return json.load(file)  # Load existing memory data
        return {'name': '', 'history': [], 'system_prompt': self.default_system_prompt}  # Default memory structure

    def save_memory(self, user_id, memory_data):
        """Saves the conversation history and system prompt to a user's file.

        Args:
            user_id: The ID of the user whose memory is being saved.
            memory_data: The data to be saved, including history and system prompt.
        """
        memory_file = os.path.join(self.memory_directory['individual'], f'{user_id}.json')
        with open(memory_file, 'w') as file:
            json.dump(memory_data, file)  # Save memory data to file

    def _initialize_group_tables(self):
        """Creates the necessary tables for group chat memory if they don't exist."""
        try:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS group_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS group_settings (
                    channel_id TEXT PRIMARY KEY,
                    system_prompt TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Failed to initialize group tables: {str(e)}")

    async def load_group_memory(self, channel_id):
        """Loads the conversation history for a group channel from database."""
        try:
            # Get system prompt
            cursor = self.conn.execute(
                'SELECT system_prompt FROM group_settings WHERE channel_id = ?',
                (channel_id,)
            )
            result = cursor.fetchone()
            system_prompt = result[0] if result else self.default_system_prompt

            # Get recent messages (last 20 for example)
            cursor = self.conn.execute('''
                SELECT role, content, timestamp 
                FROM group_messages 
                WHERE channel_id = ? 
                ORDER BY timestamp DESC LIMIT 20
            ''', (channel_id,))
            
            history = [
                {
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                }
                for row in cursor.fetchall()
            ]
            history.reverse()  # Most recent last

            return {
                'history': history,
                'system_prompt': system_prompt
            }
        except Exception as e:
            print(f"Failed to load group memory: {str(e)}")
            return {
                'history': [],
                'system_prompt': self.default_system_prompt
            }

    async def save_group_memory(self, channel_id, user_id, username, role, content):
        """Saves a new message to the group chat history in database."""
        try:
            timestamp = datetime.now().isoformat()
            await asyncio.to_thread(
                self.conn.execute,
                '''
                INSERT INTO group_messages (channel_id, user_id, username, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (channel_id, user_id, username, role, content, timestamp)
            )
            await asyncio.to_thread(self.conn.commit)
        except Exception as e:
            print(f"Failed to save group memory: {str(e)}")

    @app_commands.command(name="chat")
    @app_commands.describe(
        prompt="Your message to the AI",
        mode="Override the default chat mode (private/group). Only available in servers."
    )
    async def chat(self, interaction: discord.Interaction, prompt: str, mode: str = None):
        """
        Handle chat interactions with the AI:
        - DMs are always private
        - Guild channels default to group but can be overridden
        """
        # In DMs, force private mode and ignore any mode parameter
        if isinstance(interaction.channel, discord.DMChannel):
            mode = "private"
        # In guilds, set default or validate override
        else:
            if mode is None:
                mode = "group"
            elif mode not in ["private", "group"]:
                await interaction.response.send_message(
                    "Invalid mode. Please use 'private' or 'group'.", 
                    ephemeral=True
                )
                return

        await interaction.response.defer(thinking=True)
        
        try:
            if mode == "private":
                memory_data = await asyncio.to_thread(self.load_memory, str(interaction.user.id))
            else:
                memory_data = await self.load_group_memory(str(interaction.channel_id))

            # Add username context for all chats
            user_context = f"{interaction.user.name}: "
            formatted_prompt = f"{user_context}{prompt}"

            # For group chat, save the user message immediately
            if mode != "private":
                await self.save_group_memory(
                    str(interaction.channel_id),
                    str(interaction.user.id),
                    interaction.user.name,
                    'user',
                    formatted_prompt
                )

            # Generate response using updated history
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                messages=memory_data['history']
            )

            bot_response = response['message']['content']
            
            # Save the responses
            if mode == "private":
                memory_data['history'].append({
                    'role': 'assistant',
                    'content': bot_response,
                    'timestamp': datetime.now().isoformat()
                })
                await asyncio.to_thread(self.save_memory, str(interaction.user.id), memory_data)
            else:
                await self.save_group_memory(
                    str(interaction.channel_id),
                    'assistant',
                    'Assistant',
                    'assistant',
                    bot_response
                )

            # Send response in chunks if needed
            await send_message_in_chunks(interaction, bot_response)
            
            # Log the interaction
            self.log_command_usage(interaction, f"{mode}_chat", prompt)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            self.log_command_usage(interaction, "chat_error", str(e))

    @app_commands.command(name="set_prompt", description="Sets the system prompt for the assistant.")
    @app_commands.describe(system_prompt="The new system prompt.")
    async def set_prompt(self, interaction: discord.Interaction, system_prompt: str):
        """Sets the initial system prompt for the user's chat sessions.

        Args:
            interaction: The interaction that triggered this command.
            system_prompt: The new system prompt to be set.
        """
        user_id = str(interaction.user.id)  # Get the user ID

        # Defer the interaction to allow time for processing
        await interaction.response.defer(thinking=True)

        try:
            # Load memory asynchronously
            memory_data = await asyncio.to_thread(self.load_memory, user_id)

            # Update the system prompt
            memory_data['system_prompt'] = system_prompt

            # Save memory asynchronously
            await asyncio.to_thread(self.save_memory, user_id, memory_data)

            # Log the command usage asynchronously
            self.log_command_usage(interaction, "set_prompt", system_prompt)

            await interaction.followup.send(f"Your system prompt has been updated to: '{system_prompt}'", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to set system prompt: {str(e)}", ephemeral=True)

    @app_commands.command(name="reset_memory", description="Resets your conversation memory.")
    async def reset_memory(self, interaction: discord.Interaction):
        """Resets the user's conversation memory.

        Args:
            interaction: The interaction that triggered this command.
        """
        user_id = str(interaction.user.id)  # Get the user ID
        memory_file = os.path.join(self.memory_directory['individual'], f'{user_id}.json')

        # Defer the interaction to allow time for processing
        await interaction.response.defer(thinking=True)

        try:
            if os.path.exists(memory_file):
                # Delete the user's memory file asynchronously
                await asyncio.to_thread(os.remove, memory_file)
                await interaction.followup.send("Your conversation memory has been reset.", ephemeral=True)

                # Log the command usage asynchronously
                self.log_command_usage(interaction, "reset_memory", "Memory reset.")
            else:
                await interaction.followup.send("No memory found to reset.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to reset memory: {str(e)}", ephemeral=True)

    def log_command_usage(self, interaction, command_name, details):
        """Logs the command usage to the database.

        Args:
            interaction: The interaction that triggered the command.
            command_name: The name of the command executed.
            details: Additional details about the command execution.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        username = interaction.user.name

        try:
            # Execute the insert operation in a separate thread to prevent blocking
            asyncio.create_task(self.execute_log_insert(
                'COMMAND_USAGE',
                f"({username}) executed {command_name}. Details: {details}",
                timestamp,
                user_id,
                username
            ))
        except Exception as e:
            print(f"Failed to log command usage: {str(e)}")

    async def execute_log_insert(self, log_type, log_message, timestamp, user_id, username):
        """Asynchronously inserts a log entry into the database.

        Args:
            log_type: The type/category of the log.
            log_message: The log message detailing the action.
            timestamp: The timestamp of the log entry.
            user_id: The ID of the user who executed the command.
            username: The username of the user who executed the command.
        """
        try:
            await asyncio.to_thread(self.conn.execute, '''
                INSERT INTO logs (log_type, log_message, timestamp, user_id, username)
                VALUES (?, ?, ?, ?, ?)
            ''', (log_type, log_message, timestamp, user_id, username))
            await asyncio.to_thread(self.conn.commit)
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception
        except Exception as e:
            print(f"Unexpected error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

    @app_commands.command(name="set_group_prompt", description="Sets the system prompt for the current channel.")
    @app_commands.describe(system_prompt="The new system prompt for this channel.")
    async def set_group_prompt(self, interaction: discord.Interaction, system_prompt: str):
        """Sets the system prompt for the current channel."""
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            timestamp = datetime.now().isoformat()
            await asyncio.to_thread(
                self.conn.execute,
                '''
                INSERT OR REPLACE INTO group_settings (channel_id, system_prompt, last_updated)
                VALUES (?, ?, ?)
                ''',
                (str(interaction.channel_id), system_prompt, timestamp)
            )
            await asyncio.to_thread(self.conn.commit)
            
            await interaction.followup.send(f"Channel system prompt has been updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to set system prompt: {str(e)}", ephemeral=True)

async def send_message_in_chunks(interaction, message, chunk_size=1900):
    """Sends a message in chunks if it exceeds the specified chunk size.

    Args:
        interaction: The interaction to send the message to.
        message: The message to send, possibly exceeding the chunk size.
        chunk_size: The maximum size for each chunk of the message.
    """
    for i in range(0, len(message), chunk_size):
        await interaction.followup.send(message[i:i + chunk_size])

# Set up the cog
async def setup(bot):
    """Load the Chat cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Chat(bot))
