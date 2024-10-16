import discord
import sqlite3
from datetime import datetime
from discord.ext import commands

class Info(commands.Cog):
    """
    A Discord cog that provides information commands for the server and users.
    This includes commands to display server information and user profiles.
    """

    def __init__(self, bot):
        """
        Initialize the Info cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        # Initialize SQLite database connection (adjust the path as necessary)
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')  # Ensure the path to your database is correct

    @discord.app_commands.command(name="serverinfo", description="Displays information about the server.")
    async def guildinfo(self, interaction: discord.Interaction):
        """Displays information about the server.

        Args:
            interaction: The interaction that triggered this command.
        """
        user_id = interaction.user.id  # Get the user's ID
        username = interaction.user.name  # Get the username
        guild_id = interaction.guild.id  # Get the guild's ID
        channel_id = interaction.channel.id  # Get the channel's ID

        print(f"{username} used /serverinfo")  # Log the user who invoked the command
        guild = interaction.guild  # Get the guild (server) from the interaction
        embed = discord.Embed(title=guild.name, color=discord.Color.green())  # Create an embed for the server info
        embed.add_field(name="Server ID", value=guild.id)  # Add server ID to the embed
        embed.add_field(name="Member Count", value=guild.member_count)  # Add member count to the embed
        embed.add_field(name="Created On", value=guild.created_at)  # Add creation date to the embed
        
        # Log the command usage
        self.log_command_usage(interaction, "serverinfo")

        await interaction.response.send_message(embed=embed)  # Send the embed as a response

    @discord.app_commands.command(name="whois", description="Displays detailed information about a specified user.")
    @discord.app_commands.describe(member="The member to retrieve information about (defaults to you).")
    async def whois(self, interaction: discord.Interaction, member: discord.Member = None):
        """Displays detailed information about a specified user.

        Args:
            interaction: The interaction that triggered this command.
            member: The member to retrieve information about (defaults to the user who invoked the command).
        """
        user_id = interaction.user.id  # Get the user's ID
        username = interaction.user.name  # Get the username
        guild_id = interaction.guild.id  # Get the guild's ID
        channel_id = interaction.channel.id  # Get the channel's ID

        print(f"{username} used /whois")  # Log the user who invoked the command
        if member is None:
            member = interaction.user  # Default to the user who invoked the command if no member is specified
        
        embed = discord.Embed(title=f"{member.name}'s Profile", color=member.color)  # Create an embed for the user's profile
        embed.add_field(name="ID", value=member.id)  # Add user ID to the embed
        embed.add_field(name="Status", value=member.status)  # Add user status to the embed
        embed.add_field(name="Joined at", value=member.joined_at)  # Add join date to the embed
        
        # Log the command usage
        self.log_command_usage(interaction, "whois")

        await interaction.response.send_message(embed=embed)  # Send the embed as a response

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
    """Load the Info cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Info(bot))
