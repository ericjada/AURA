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
        self.memory_directory = 'user_memories'  # Directory to save user memory files
        os.makedirs(self.memory_directory, exist_ok=True)  # Create the directory if it doesn't exist
        self.default_system_prompt = "You are a helpful assistant."  # Default system message

        # Initialize SQLite database connection
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # To access columns by name

        # Start ollama serve when the bot is initialized
        self.start_ollama_serve()

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
        memory_file = os.path.join(self.memory_directory, f'{user_id}.json')
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
        memory_file = os.path.join(self.memory_directory, f'{user_id}.json')
        with open(memory_file, 'w') as file:
            json.dump(memory_data, file)  # Save memory data to file

    @app_commands.command(name="chat", description="Chat with the LLaMA model.")
    @app_commands.describe(prompt="The message you want to send to the assistant.")
    async def chat(self, interaction: discord.Interaction, prompt: str):
        """Generates a response from the LLaMA model based on the given prompt.

        Args:
            interaction: The interaction that triggered this command.
            prompt: The user's message to send to the model.
        """
        user_id = str(interaction.user.id)  # Get the user ID
        username = str(interaction.user)  # Get the username

        print(f"{username} used /chat with prompt: {prompt}")

        # Log the command usage asynchronously
        self.log_command_usage(interaction, "chat", prompt)

        if not prompt:
            await interaction.response.send_message("Please provide a prompt for the model.", ephemeral=True)
            return

        # Defer the interaction immediately to avoid timeout
        await interaction.response.defer(thinking=True)

        try:
            # Load the user's conversation history and system prompt asynchronously
            memory_data = await asyncio.to_thread(self.load_memory, user_id)

            # Store the user's name if it hasn't been set
            if not memory_data['name']:
                memory_data['name'] = username

            # Ensure the system prompt is always included at the beginning of the conversation
            system_message = {'role': 'system', 'content': memory_data.get('system_prompt', self.default_system_prompt)}
            
            # Check if the system message is already in the history
            if len(memory_data['history']) == 0 or memory_data['history'][0]['role'] != 'system':
                memory_data['history'].insert(0, system_message)  # Always ensure system prompt is the first message

            # Add the user prompt to the conversation history
            memory_data['history'].append({'role': 'user', 'content': prompt})

            # Prepare the message for the Ollama API, including user's conversation history
            messages = memory_data['history'].copy()

            # Using ollama to generate a response asynchronously
            response = await asyncio.to_thread(ollama.chat, model=self.model, messages=messages)
            print("Ollama response:", response)  # Print the entire response for inspection

            # Extract the content from the response
            bot_response = response['message']['content']

            # Send the response in chunks if it's too long
            await send_message_in_chunks(interaction, bot_response)

            # Add the bot's response to the conversation history
            memory_data['history'].append({'role': 'assistant', 'content': bot_response})

            # Save the updated conversation history asynchronously
            await asyncio.to_thread(self.save_memory, user_id, memory_data)

            # Log the bot's response asynchronously
            self.log_command_usage(interaction, "chat_response", bot_response)

        except KeyError as e:
            await interaction.followup.send(f'Error: The response structure from the API is unexpected. {str(e)}', ephemeral=True)
        except json.JSONDecodeError:
            await interaction.followup.send('Error: Failed to decode the JSON response from the API.', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'An error occurred while generating a response: {str(e)}', ephemeral=True)

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
        memory_file = os.path.join(self.memory_directory, f'{user_id}.json')

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
