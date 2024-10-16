import discord
from discord.ext import commands
from datetime import datetime
import sqlite3  # Make sure to import sqlite3 for database interaction

class General(commands.Cog):
    """
    A Discord cog that provides general commands for users.
    This includes a ping command that responds with a simple message.
    """

    def __init__(self, bot):
        """
        Initialize the General cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        # Initialize the database connection
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')  # Update with the correct path

    @discord.app_commands.command(name="ping", description="Responds with 'Pong!'")
    async def ping(self, interaction: discord.Interaction):
        """Responds with 'Pong!' when the user sends /ping.

        Args:
            interaction: The interaction that triggered this command.
        """
        user_id = interaction.user.id  # Get the user's ID
        username = interaction.user.name  # Get the username
        guild_id = interaction.guild.id  # Get the guild's ID
        channel_id = interaction.channel.id  # Get the channel's ID

        print(f"{username} used /ping")  # Log the user who invoked the command

        # Log the command usage to the database
        self.log_command_usage(interaction, "ping")

        await interaction.response.send_message('Pong!')  # Send the response

    def log_command_usage(self, interaction, command_name):
        """Logs the command usage to the database.

        Args:
            interaction: The interaction that triggered the command.
            command_name: The name of the command that was executed.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        username = interaction.user.name

        with self.conn:
            self.conn.execute(''' 
                INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, guild_id, user_id, username))

# Set up the cog
async def setup(bot):
    """Load the General cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(General(bot))
