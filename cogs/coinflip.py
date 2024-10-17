import discord
import random
from discord.ext import commands
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction

class CoinFlip(commands.Cog):
    """
    A Discord cog that allows users to flip a coin and logs the result.
    """

    def __init__(self, bot):
        """
        Initialize the CoinFlip cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot

        # Initialize SQLite database connection for logging
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')  # Ensure the correct path to your database

    @discord.app_commands.command(name="coinflip", description="Flip a coin (Heads or Tails).")
    async def coinflip(self, interaction: discord.Interaction):
        """Flips a coin and returns either 'Heads' or 'Tails'."""
        result = random.choice(["Heads", "Tails"])  # Randomly choose between Heads or Tails

        # Log the coin flip result
        self.log_command_usage(interaction, result)

        # Send the result to the user
        await interaction.response.send_message(f"🪙 You flipped: **{result}**")

    def log_command_usage(self, interaction: discord.Interaction, result: str):
        """
        Logs the usage of the /coinflip command and its result into the SQLite database.

        Args:
            interaction: The interaction that triggered the command.
            result: The result of the coin flip ('Heads' or 'Tails').
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else 'DM'  # Handle DMs by assigning 'DM'
        channel_id = interaction.channel.id if interaction.channel else 'DM'
        username = interaction.user.name

        # Insert log into the SQLite database
        with self.conn:
            self.conn.execute('''
                INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('COINFLIP_COMMAND', f"({username}) flipped a coin: {result}", timestamp, guild_id, user_id, username))

        print(f"Logged: {username} flipped a coin resulting in {result}.")

# Set up the cog
async def setup(bot):
    """Load the CoinFlip cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(CoinFlip(bot))
