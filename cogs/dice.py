# dice.py

import discord
import random
import re  # Import regex to parse the dice roll string
from discord.ext import commands
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction

class Dice(commands.Cog):
    """
    A Discord cog that allows users to roll dice in the format XdY+Z.
    Users can perform standalone dice rolls or participate in duels.
    """

    def __init__(self, bot):
        """
        Initialize the Dice cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot

        # Initialize SQLite database connection for logging
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dictionary-like cursor
        self.cursor = self.conn.cursor()

    @discord.app_commands.command(name="roll", description="Roll dice in the format XdY+Z (e.g. 2d6+4 or d20).")
    @discord.app_commands.describe(dice="The dice roll command (e.g., 2d6+4 or d20).")
    async def roll(self, interaction: discord.Interaction, dice: str):
        """Parses and rolls the dice based on the format provided by the user (XdY+Z)."""

        user = interaction.user
        user_id = user.id

        try:
            result, rolls, modifier = self.parse_dice_roll(dice)
            rolls_str = ', '.join(str(roll) for roll in rolls)
            response = f"🎲 You rolled: {rolls_str} (Total: **{result}**)"
            if modifier:
                response += f" with modifier {modifier:+}"

            # Log the command usage and result
            self.log_command_usage(interaction, dice, rolls, result)

            # Check if the user is in an active duel that requires this roll
            dice_duel_cog = self.bot.get_cog('DiceDuel')
            if dice_duel_cog:
                await dice_duel_cog.handle_roll(user_id, result, rolls, dice)

            await interaction.response.send_message(response)
        except ValueError as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    def parse_dice_roll(self, dice_str: str):
        """
        Parses a dice roll string in the form of XdY+Z and calculates the result.

        Args:
            dice_str: The dice roll string to parse (e.g., 2d6+4, d20).

        Returns:
            Tuple containing:
            - result: The total sum of the dice roll with the modifier.
            - rolls: A list of individual dice rolls.
            - modifier: The numeric modifier applied to the result.
        """
        # Regex to match patterns like '2d6+4', 'd20', '4d8', or 'd12-2'
        dice_pattern = r"(?:(\d+)d)?(\d+)([+-]\d+)?"
        match = re.fullmatch(dice_pattern, dice_str.replace(" ", ""))  # Remove spaces before matching

        if not match:
            raise ValueError("Invalid dice format. Please use a format like 2d6+4 or d20.")

        num_dice = int(match.group(1)) if match.group(1) else 1  # Number of dice to roll, defaults to 1
        dice_size = int(match.group(2))  # Size of dice (e.g., 6 for d6, 20 for d20)
        modifier = int(match.group(3)) if match.group(3) else 0  # Modifier, defaults to 0 if not present

        if num_dice < 1 or dice_size < 1:
            raise ValueError("Number of dice and size must be greater than 0.")

        # Roll the dice
        rolls = [random.randint(1, dice_size) for _ in range(num_dice)]
        result = sum(rolls) + modifier

        return result, rolls, modifier

    def log_command_usage(self, interaction: discord.Interaction, dice_str: str, rolls, result: int):
        """
        Logs the usage of the /roll command and its results into the SQLite database.

        Args:
            interaction: The interaction that triggered the command.
            dice_str: The dice string provided by the user (e.g., '2d6+4').
            rolls: A list of individual dice rolls.
            result: The total result of the roll.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        username = interaction.user.name

        rolls_str = ', '.join(str(roll) for roll in rolls)

        # Insert log into the SQLite database
        with self.conn:
            self.conn.execute('''
                INSERT INTO logs (log_type, log_message, timestamp, user_id, username)
                VALUES (?, ?, ?, ?, ?)
            ''', ('ROLL_COMMAND', f"({username}) rolled {dice_str}: {rolls_str} (Total: {result})", 
                  timestamp, user_id, username))

        print(f"Logged: {username} rolled {dice_str} resulting in {result}.")

# Set up the cog
async def setup(bot):
    """Load the Dice cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Dice(bot))
