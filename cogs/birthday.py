import discord
from discord.ext import commands, tasks
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction

class Birthday(commands.Cog):
    """
    A Discord cog that manages user birthdays, allowing users to set their birthday,
    check the countdown to their birthday, and send birthday wishes.
    """

    def __init__(self, bot):
        """
        Initialize the Birthday cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        # Initialize SQLite database connection
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')  # Update with the correct path
        self.create_table()
        # Start the daily birthday check
        self.birthday_wishes.start()

    def create_table(self):
        """Creates the birthdays table if it doesn't already exist."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    birthday DATE,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')

    def log_command_usage(self, interaction, command_name, details):
        """Logs the command usage to the database.

        Args:
            interaction: The interaction that triggered the command.
            command_name: The name of the command executed.
            details: Additional details about the command execution.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = interaction.channel.id if interaction.guild else None
        username = interaction.user.name

        with self.conn:
            self.conn.execute(''' 
                INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, guild_id, user_id, username))

    @discord.app_commands.command(name='set_birthday', description="Set your birthday (format: YYYY-MM-DD).")
    @discord.app_commands.describe(date="Your birthday in YYYY-MM-DD format")
    async def set_birthday(self, interaction: discord.Interaction, date: str):
        """
        Set your birthday in the format YYYY-MM-DD.

        Args:
            interaction: The interaction that triggered this command.
            date: The user's birthday in YYYY-MM-DD format.

        Example:
            /set_birthday 1990-05-15
        """
        user_id = interaction.user.id  # Get the user ID
        guild_id = interaction.guild.id if interaction.guild else None  # Get the guild ID

        try:
            # Parse the input date
            birthday = datetime.strptime(date, '%Y-%m-%d').date()
            # Store the birthday in the database
            with self.conn:
                self.conn.execute('''
                    INSERT INTO birthdays (user_id, guild_id, birthday)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET birthday = ?;
                ''', (user_id, guild_id, birthday, birthday))

            # Log the command usage
            self.log_command_usage(interaction, "set_birthday", f"Birthday set to {birthday.strftime('%Y-%m-%d')}")

            await interaction.response.send_message(f"🎉 {interaction.user.mention}, your birthday has been set to {birthday.strftime('%Y-%m-%d')}! I'll make sure to remind everyone on the big day!")
        except ValueError:
            await interaction.response.send_message("⚠️ Please enter your birthday in the correct format (YYYY-MM-DD). Example: `/set_birthday 1990-05-15`.")

    @discord.app_commands.command(name='birthday_countdown', description="See how many days are left until a user's birthday.")
    @discord.app_commands.describe(member="The member whose birthday countdown you want to check. Defaults to yourself.")
    async def birthday_countdown(self, interaction: discord.Interaction, member: discord.Member = None):
        """
        Show how many days are left until a user's birthday. Defaults to the command author's birthday.

        Args:
            interaction: The interaction that triggered this command.
            member: The Discord member whose birthday countdown to check (defaults to the command author).

        Example:
            /birthday_countdown @user
        """
        user_id = interaction.user.id  # Get the user ID
        if member is None:
            member = interaction.user

        # Retrieve the birthday from the database
        birthday_row = self.conn.execute('SELECT birthday FROM birthdays WHERE user_id = ?', (member.id,)).fetchone()
        
        if not birthday_row:
            await interaction.response.send_message(f"❌ {member.name} hasn't set their birthday yet. Ask them to use `/set_birthday`!")
            return

        # Convert birthday string back to a datetime object
        birthday = datetime.strptime(birthday_row[0], '%Y-%m-%d').date()

        # Get the current date and the user's birthday in this year or next year
        today = datetime.now().date()
        next_birthday = birthday.replace(year=today.year)

        # If the birthday for this year has already passed, set it for the next year
        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)

        days_until_birthday = (next_birthday - today).days

        # Log the command usage
        self.log_command_usage(interaction, "birthday_countdown", f"Checked countdown for {member.name}.")

        if days_until_birthday == 0:
            await interaction.response.send_message(f"🎉🎂 It's {member.name}'s birthday today! Everyone, wish them a Happy Birthday! 🎂🎉")
        else:
            await interaction.response.send_message(f"📅 {member.name}'s birthday is in {days_until_birthday} days!")

    @tasks.loop(hours=24)
    async def birthday_wishes(self):
        """
        This task runs every 24 hours and sends birthday wishes to users whose birthday is today.
        """
        today = datetime.now().date()
        birthday_rows = self.conn.execute('SELECT user_id FROM birthdays WHERE birthday = ?', (today.strftime('%Y-%m-%d'),)).fetchall()
        
        for row in birthday_rows:
            user_id = row[0]
            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(f"🎉🥳 Happy Birthday, {user.name}! I hope you have an amazing day! 🎂🎈")
                    print(f"Sent a birthday wish to {user.name} (ID: {user_id}).")
                except discord.Forbidden:
                    print(f"Couldn't send a birthday wish to {user.name} (ID: {user_id}). The bot doesn't have permission to DM this user.")
            else:
                print(f"User with ID {user_id} not found for birthday wishes.")

    @birthday_wishes.before_loop
    async def before_birthday_wishes(self):
        """
        Wait until the bot is ready before starting the loop.
        """
        await self.bot.wait_until_ready()

# Required to setup the cog
async def setup(bot):
    """
    Load the Birthday cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Birthday(bot))
