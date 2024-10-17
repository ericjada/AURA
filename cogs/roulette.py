import discord
import random
from discord.ext import commands
from datetime import datetime
import sqlite3

class Roulette(commands.Cog):
    """
    A Discord cog that allows users to play a game of Roulette using AURAcoin.
    """

    def __init__(self, bot):
        """
        Initialize the Roulette cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')

    @discord.app_commands.command(name="roulette", description="Place a bet on Roulette using AURAcoin.")
    @discord.app_commands.describe(bet_type="Bet on 'red', 'black', 'even', 'odd', or a specific number (0-36).", amount="Amount of AURAcoin to bet.")
    async def roulette(self, interaction: discord.Interaction, bet_type: str, amount: int):
        """Places a bet on a game of Roulette."""
        user_id = interaction.user.id
        user_name = interaction.user.name

        await interaction.response.defer(thinking=True)  # Show 'thinking' indicator

        # Validate bet type
        valid_bet_types = ['red', 'black', 'even', 'odd'] + [str(i) for i in range(37)]
        if bet_type not in valid_bet_types:
            await interaction.followup.send(f"Invalid bet type! You can bet on 'red', 'black', 'even', 'odd', or a number (0-36).")
            return

        # Check if the user has enough AURAcoin
        balance = self.get_auracoin_balance(user_id)
        if amount > balance:
            await interaction.followup.send(f"Insufficient AURAcoin balance. You only have {balance} AC.")
            return

        # Deduct bet amount
        self.update_balance(user_id, -amount, 'bet')

        # Spin the wheel
        outcome_number, outcome_color = self.spin_wheel()

        # Determine the result and payout
        result, winnings = self.calculate_payout(bet_type, amount, outcome_number, outcome_color)

        # Update balance based on the result
        if winnings > 0:
            self.update_balance(user_id, winnings, 'win')

        # Create the result message
        outcome_message = f"The roulette wheel landed on {outcome_number} ({outcome_color}).\n"
        if result == "win":
            outcome_message += f"🎉 You won {winnings} AC!"
        else:
            outcome_message += f"😢 You lost {amount} AC."

        # Send the result to the user
        await interaction.followup.send(outcome_message)

        # Log the command usage
        self.log_roulette_game(interaction, bet_type, amount, outcome_number, outcome_color, result, winnings)

    def spin_wheel(self):
        """Simulates a spin of the roulette wheel."""
        numbers = list(range(37))  # Numbers 0-36
        colors = ['red', 'black'] * 18 + ['green']  # 18 red, 18 black, 1 green (for 0)
        outcome_number = random.choice(numbers)
        outcome_color = 'green' if outcome_number == 0 else random.choice(colors)
        return outcome_number, outcome_color

    def calculate_payout(self, bet_type, amount, outcome_number, outcome_color):
        """Calculates the payout based on the bet and the outcome of the spin."""
        if bet_type.isdigit():  # Betting on a specific number
            if int(bet_type) == outcome_number:
                return "win", amount * 35  # 35:1 payout
            else:
                return "lose", 0
        elif bet_type == "red" and outcome_color == "red":
            return "win", amount * 2  # 2:1 payout
        elif bet_type == "black" and outcome_color == "black":
            return "win", amount * 2  # 2:1 payout
        elif bet_type == "even" and outcome_number % 2 == 0 and outcome_number != 0:
            return "win", amount * 2  # 2:1 payout
        elif bet_type == "odd" and outcome_number % 2 != 0:
            return "win", amount * 2  # 2:1 payout
        else:
            return "lose", 0  # Bet lost

    def update_balance(self, user_id, change_amount, transaction_type):
        """Updates the user's AURAcoin balance in the database."""
        balance = self.get_auracoin_balance(user_id) + change_amount
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, change_amount, balance, transaction_type, timestamp))

    def get_auracoin_balance(self, player_id):
        """Retrieves the AURAcoin balance for a player."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT balance FROM auracoin_ledger WHERE player_id = ? ORDER BY transaction_id DESC LIMIT 1", (player_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def log_roulette_game(self, interaction, bet_type, bet_amount, outcome_number, outcome_color, result, winnings):
        """Logs the result of a Roulette game."""
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else 'DM'
        user_name = interaction.user.name

        with self.conn:
            self.conn.execute('''
                INSERT INTO roulette_game (guild_id, player_id, bet_type, bet_amount, outcome_number, outcome_color, result, winnings, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, user_id, bet_type, bet_amount, outcome_number, outcome_color, result, winnings, timestamp))

        print(f"Logged: {user_name} bet {bet_amount} AC on {bet_type} and {result} with {winnings} AC winnings.")

# Set up the cog
async def setup(bot):
    """Load the Roulette cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Roulette(bot))
