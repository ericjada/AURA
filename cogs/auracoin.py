# auracoin.py

import discord
from discord.ext import commands
from datetime import datetime
import sqlite3

class AURAcoin(commands.Cog):
    """
    A Discord cog that handles global AURAcoin balances and transactions.
    """

    def __init__(self, bot):
        """
        Initialize the AURAcoin cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Enable foreign key support
        self.conn.execute('PRAGMA foreign_keys = ON')

        # Since you handle DB creation elsewhere, we won't create tables here

    @discord.app_commands.command(name="balance", description="Check your AURAcoin balance.")
    async def balance(self, interaction: discord.Interaction):
        """Checks the user's global AURAcoin balance and grants a daily bonus if eligible."""
        try:
            user_id = interaction.user.id

            await interaction.response.defer(thinking=True)

            # Check and grant daily bonus if eligible
            daily_bonus_granted = self.check_and_grant_daily_bonus(user_id)
            balance = self.get_auracoin_balance(user_id)
            if daily_bonus_granted:
                await interaction.followup.send(f"You have received your daily bonus of 100 AC!\nYour global AURAcoin balance is: {balance} AC")
            else:
                await interaction.followup.send(f"Your global AURAcoin balance is: {balance} AC")

            # Log the command usage
            self.log_command_usage(interaction, "balance", "", f"Balance: {balance} AC")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /balance command: {str(e)}")

    def check_and_grant_daily_bonus(self, player_id):
        """Checks if the player is eligible for the daily bonus and grants it if they are.

        Returns True if the bonus was granted, False otherwise.
        """
        cursor = self.conn.cursor()
        # Get the last time the user received a daily bonus
        cursor.execute("""
            SELECT timestamp FROM auracoin_ledger
            WHERE player_id = ? AND transaction_type = 'daily_bonus'
            ORDER BY transaction_id DESC LIMIT 1
        """, (player_id,))
        result = cursor.fetchone()
        now = datetime.now()
        if result:
            last_bonus_time = datetime.fromisoformat(result['timestamp'])
            time_since_last_bonus = now - last_bonus_time
            if time_since_last_bonus.total_seconds() < 24 * 3600:
                # Not eligible yet
                return False
        # Grant the bonus
        balance = self.get_auracoin_balance(player_id)
        new_balance = balance + 100
        timestamp = now.isoformat()
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (player_id, 100, new_balance, 'daily_bonus', timestamp))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in check_and_grant_daily_bonus: {e}")
            raise
        return True

    def get_auracoin_balance(self, player_id):
        """Get the global AURAcoin balance for a player."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT balance FROM auracoin_ledger
            WHERE player_id = ?
            ORDER BY transaction_id DESC LIMIT 1
        """, (player_id,))
        result = cursor.fetchone()
        return result['balance'] if result else 0

    def update_balance(self, player_id, amount, transaction_type):
        """Updates the player's global AURAcoin balance.

        Args:
            player_id: The ID of the player.
            amount: The amount to change (can be negative).
            transaction_type: The type of transaction.
        """
        balance = self.get_auracoin_balance(player_id)
        new_balance = balance + amount
        timestamp = datetime.now().isoformat()
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (player_id, amount, new_balance, transaction_type, timestamp))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in update_balance: {e}")
            raise

    def log_command_usage(self, interaction, command_name, input_data, output_data):
        """Logs the command usage to the database.

        Args:
            interaction: The interaction that triggered this command.
            command_name: The name of the command that was executed.
            input_data: The input provided by the user.
            output_data: The output generated by the command.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        username = interaction.user.name

        try:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, guild_id, user_id, username))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

    # You can add more AURAcoin-related commands here

async def setup(bot):
    """Load the AURAcoin cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(AURAcoin(bot))
