import random
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import sqlite3

class Lottery(commands.Cog):
    """
    A Discord cog that provides a lottery game using AURAcoin.
    Users can buy lottery tickets with AURAcoin, and a winner is drawn at a scheduled time.
    """

    def __init__(self, bot):
        """
        Initialize the Lottery cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')
        self.lottery_entries = {}  # Key: guild_id, Value: dict of user_id and number of tickets
        self.lottery_end_time = {}  # Key: guild_id, Value: datetime when lottery ends
        self.lottery_running = {}   # Key: guild_id, Value: bool indicating if lottery is running

    @discord.app_commands.command(name="start_lottery", description="Start a new lottery.")
    @commands.has_permissions(administrator=True)
    async def start_lottery(self, interaction: discord.Interaction, duration: int):
        """
        Starts a new lottery that will run for a specified duration in minutes.

        Args:
            duration: Duration in minutes for which the lottery will run.
        """
        guild_id = interaction.guild.id

        # Check if a lottery is already running
        if self.lottery_running.get(guild_id, False):
            await interaction.response.send_message("A lottery is already running in this server.")
            return

        # Initialize lottery details
        self.lottery_entries[guild_id] = {}
        self.lottery_end_time[guild_id] = datetime.now() + timedelta(minutes=duration)
        self.lottery_running[guild_id] = True

        await interaction.response.send_message(f"A new lottery has started! Use `/buy_ticket` to participate. The lottery will end in {duration} minutes.")

        # Log the command usage
        self.log_command_usage(interaction, "start_lottery", f"Duration: {duration} minutes", "Lottery started.")

    @discord.app_commands.command(name="buy_ticket", description="Buy a lottery ticket with AURAcoin.")
    @discord.app_commands.describe(quantity="The number of tickets to buy.")
    async def buy_ticket(self, interaction: discord.Interaction, quantity: int):
        """
        Allows a user to buy lottery tickets.

        Args:
            quantity: The number of tickets the user wants to buy.
        """
        user = interaction.user
        user_id = user.id
        guild_id = interaction.guild.id

        # Check if a lottery is running
        if not self.lottery_running.get(guild_id, False):
            await interaction.response.send_message("There is no active lottery right now.")
            return

        # Check if the lottery has ended
        if datetime.now() >= self.lottery_end_time[guild_id]:
            await interaction.response.send_message("The lottery has ended. Wait for the next one!")
            return

        # Check if the user has enough balance
        ticket_price = 10  # Set ticket price to 10 AC
        total_cost = ticket_price * quantity
        balance = self.get_auracoin_balance(user_id)
        if total_cost <= 0:
            await interaction.response.send_message("You need to buy at least one ticket.")
            return
        if total_cost > balance:
            await interaction.response.send_message(f"You have insufficient AURAcoin balance. Your balance is {balance} AC.")
            return

        # Deduct the cost from the user's balance
        new_balance = balance - total_cost
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, -total_cost, new_balance, 'lottery_ticket_purchase', timestamp))

        # Add entries to the lottery
        entries = self.lottery_entries[guild_id]
        if user_id in entries:
            entries[user_id] += quantity
        else:
            entries[user_id] = quantity

        await interaction.response.send_message(f"You have bought {quantity} lottery ticket(s). Good luck!")

        # Log the command usage
        self.log_command_usage(interaction, "buy_ticket", f"Quantity: {quantity}", f"Tickets purchased: {quantity}")

    @discord.app_commands.command(name="lottery_status", description="Check the status of the current lottery.")
    async def lottery_status(self, interaction: discord.Interaction):
        """
        Displays the status of the current lottery, including time left and total tickets sold.
        """
        guild_id = interaction.guild.id

        # Check if a lottery is running
        if not self.lottery_running.get(guild_id, False):
            await interaction.response.send_message("There is no active lottery right now.")
            return

        time_left = self.lottery_end_time[guild_id] - datetime.now()
        minutes_left = int(time_left.total_seconds() // 60)
        seconds_left = int(time_left.total_seconds() % 60)
        total_tickets = sum(self.lottery_entries[guild_id].values())

        await interaction.response.send_message(
            f"Time left: {minutes_left} minutes and {seconds_left} seconds.\n"
            f"Total tickets sold: {total_tickets}"
        )

        # Log the command usage
        self.log_command_usage(interaction, "lottery_status", "", "Displayed lottery status.")

    @discord.app_commands.command(name="end_lottery", description="End the current lottery and draw a winner.")
    @commands.has_permissions(administrator=True)
    async def end_lottery(self, interaction: discord.Interaction):
        """
        Ends the current lottery and draws a winner immediately.
        """
        guild_id = interaction.guild.id

        # Check if a lottery is running
        if not self.lottery_running.get(guild_id, False):
            await interaction.response.send_message("There is no active lottery to end.")
            return

        await self.draw_winner(interaction)

        # Log the command usage
        self.log_command_usage(interaction, "end_lottery", "", "Lottery ended manually.")

    async def draw_winner(self, interaction):
        """
        Draws a winner for the lottery.

        Args:
            interaction: The interaction that triggered the draw.
        """
        guild_id = interaction.guild.id
        entries = self.lottery_entries[guild_id]

        # Create a list of user IDs weighted by the number of tickets
        tickets_pool = []
        for user_id, tickets in entries.items():
            tickets_pool.extend([user_id] * tickets)

        if not tickets_pool:
            await interaction.response.send_message("No one participated in the lottery. No winner can be drawn.")
            self.reset_lottery(guild_id)
            return

        # Randomly select a winner
        winner_id = random.choice(tickets_pool)
        winner = await self.bot.fetch_user(winner_id)
        total_pot = sum(entries.values()) * 10  # Each ticket costs 10 AC
        timestamp = datetime.now().isoformat()

        # Award the prize to the winner
        balance = self.get_auracoin_balance(winner_id)
        new_balance = balance + total_pot
        with self.conn:
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (winner_id, total_pot, new_balance, 'lottery_win', timestamp))

        await interaction.response.send_message(f"🎉 Congratulations {winner.mention}! You have won the lottery and received {total_pot} AC!")

        # Log the lottery result
        self.log_lottery_result(guild_id, winner_id, total_pot)

        # Reset the lottery
        self.reset_lottery(guild_id)

    def reset_lottery(self, guild_id):
        """
        Resets the lottery data for a guild.

        Args:
            guild_id: The ID of the guild to reset the lottery for.
        """
        self.lottery_entries[guild_id] = {}
        self.lottery_end_time[guild_id] = None
        self.lottery_running[guild_id] = False

    def get_auracoin_balance(self, player_id):
        """Get the AURAcoin balance for a player."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT balance FROM auracoin_ledger WHERE player_id = ? ORDER BY transaction_id DESC LIMIT 1", (player_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

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

        with self.conn:
            self.conn.execute('''
                INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, guild_id, user_id, username))

    def log_lottery_result(self, guild_id, winner_id, prize_amount):
        """Logs the result of the lottery into the lottery_results table.

        Args:
            guild_id: The ID of the guild where the lottery took place.
            winner_id: The ID of the user who won the lottery.
            prize_amount: The amount of AURAcoin won.
        """
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO lottery_results (guild_id, winner_id, prize_amount, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, winner_id, prize_amount, timestamp))

    @commands.Cog.listener()
    async def on_ready(self):
        """Checks periodically if any lotteries have ended and draws winners."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            for guild_id in list(self.lottery_running.keys()):
                if self.lottery_running[guild_id] and datetime.now() >= self.lottery_end_time[guild_id]:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        channel = guild.system_channel or guild.text_channels[0]
                        interaction = discord.Interaction(channel=channel, user=guild.me)
                        await self.draw_winner(interaction)

    @discord.app_commands.command(name="lottery_history", description="Shows the history of lottery winners.")
    async def lottery_history(self, interaction: discord.Interaction):
        """
        Displays the history of lottery winners in the guild.
        """
        guild_id = interaction.guild.id
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT winner_id, prize_amount, timestamp
            FROM lottery_results
            WHERE guild_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (guild_id,))
        results = cursor.fetchall()

        if not results:
            await interaction.response.send_message("There is no lottery history for this server.")
            return

        history_message = "**Recent Lottery Winners:**\n"
        for winner_id, prize_amount, timestamp in results:
            winner = await self.bot.fetch_user(winner_id)
            time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            history_message += f"{winner.name} won {prize_amount} AC on {time_str}\n"

        await interaction.response.send_message(history_message)

        # Log the command usage
        self.log_command_usage(interaction, "lottery_history", "", "Displayed lottery history.")

import asyncio

# Set up the cog
async def setup(bot):
    """Load the Lottery cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Lottery(bot))
