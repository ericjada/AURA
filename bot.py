import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction

# Set the working directory to the script's location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Function to check if the token.env file exists, if not, create it and prompt for the token
def check_token_file():
    """
    Check if the 'token.env' file exists.
    If not, create it and prompt the user to enter their Discord token.
    """
    if not os.path.exists('./token.env'):
        print("token.env not found. Creating a new one.")
        token = input("Please enter your Discord token: ")
        with open('./token.env', 'w') as f:
            f.write(f'DISCORD_TOKEN={token}\n')  # Save the token in the .env file
        print("token.env created successfully.")

# Check for token.env and prompt for token if missing
check_token_file()

# Load environment variables from the token.env file
load_dotenv('./token.env')

# Get the Discord token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Create bot instance with intents to listen for messages and message content
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Initialize SQLite database connection
conn = sqlite3.connect('./group_memories/aura_memory.db')  # Update with the correct path

async def load_cogs():
    """
    Asynchronously loads all cogs (extensions) from the 'cogs' folder.
    Each file in the folder must have a .py extension.
    
    Raises:
        Exception: If a cog fails to load, an error message will be printed.
    """
    for filename in os.listdir('./cogs'):  # Iterate through each file in the 'cogs' directory
        if filename.endswith('.py'):  # Check for Python files
            try:
                # Load the cog extension
                await bot.load_extension(f'cogs.{filename[:-3]}')  # Load the cog without the .py extension
                print(f'Loaded cog: {filename[:-3]}')  # Confirm successful loading
            except Exception as e:
                # Handle failure to load the cog
                print(f'Failed to load cog {filename[:-3]}: {e}')  # Print the error message

@bot.event
async def on_ready():
    """
    Event handler triggered when the bot is ready.
    Logs the bot's username and ID and attempts to sync slash commands.
    """
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

    # Sync slash commands with Discord
    try:
        await bot.tree.sync()  # Ensures slash commands are synced across servers
        print("Slash commands synced successfully!")
    except Exception as e:
        # Handle failure to sync commands
        print(f"Failed to sync commands: {e}")  # Print the error message

async def main():
    """
    Main function to start the bot asynchronously.
    Loads all cogs and starts the bot using the provided Discord token.

    Raises:
        Exception: If there is an error starting the bot, it will be printed.
    """
    try:
        async with bot:
            await load_cogs()  # Load all cogs before starting the bot
            await bot.start(TOKEN)  # Start the bot using the token
    except Exception as e:
        # Handle any exception that occurs during bot startup
        print(f'Failed to start the bot: {e}')  # Print the error message

# Asynchronously run the main function to start the bot
import asyncio
asyncio.run(main())