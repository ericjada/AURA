import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
import random
import asyncio

class DuelArena(commands.Cog):
    """
    A Discord cog that allows users to duel each other by betting AURAcoin.
    Users can challenge others, accept challenges, and engage in a turn-based duel.
    """

    def __init__(self, bot):
        """
        Initialize the DuelArena cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')
        self.pending_duels = {}  # Key: challenged_user_id, Value: (challenger_user_id, bet_amount)
        self.active_duels = {}   # Key: (user1_id, user2_id), Value: duel data

    @discord.app_commands.command(name="duel_challenge", description="Challenge another user to a duel.")
    @discord.app_commands.describe(opponent="The user you want to challenge.", amount="The amount of AURAcoin to bet.")
    async def duel_challenge(self, interaction: discord.Interaction, opponent: discord.User, amount: int):
        """Allows a user to challenge another user to a duel."""
        challenger = interaction.user
        challenger_id = challenger.id
        opponent_id = opponent.id

        await interaction.response.defer(thinking=True)

        # Check if the opponent is not the same as the challenger
        if challenger_id == opponent_id:
            await interaction.followup.send("You cannot challenge yourself.")
            return

        # Check if the amount is valid
        if amount <= 0:
            await interaction.followup.send("You need to bet a positive amount of AURAcoin.")
            return

        # Check if the challenger has enough balance
        challenger_balance = self.get_auracoin_balance(challenger_id)
        if amount > challenger_balance:
            await interaction.followup.send(f"You have insufficient AURAcoin balance. Your balance is {challenger_balance} AC.")
            return

        # Check if the opponent has enough balance
        opponent_balance = self.get_auracoin_balance(opponent_id)
        if amount > opponent_balance:
            await interaction.followup.send(f"The opponent has insufficient AURAcoin balance.")
            return

        # Check if there is already a pending challenge
        if opponent_id in self.pending_duels:
            await interaction.followup.send(f"{opponent.mention} already has a pending challenge.")
            return

        # Create a pending duel
        self.pending_duels[opponent_id] = (challenger_id, amount)
        await interaction.followup.send(f"{challenger.mention} has challenged {opponent.mention} to a duel for {amount} AC! {opponent.mention}, type `/duel_accept` to accept the challenge.")

        # Log the command usage
        self.log_command_usage(interaction, "duel_challenge", f"Challenged {opponent.name}, Amount: {amount}", "Challenge sent.")

    @discord.app_commands.command(name="duel_accept", description="Accept a duel challenge.")
    async def duel_accept(self, interaction: discord.Interaction):
        """Allows a user to accept a pending duel challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if there is a pending duel
        if user_id not in self.pending_duels:
            await interaction.followup.send("You do not have any pending duel challenges.")
            return

        challenger_id, bet_amount = self.pending_duels.pop(user_id)
        challenger = await self.bot.fetch_user(challenger_id)

        # Deduct the bet amount from both users
        timestamp = datetime.now().isoformat()
        self.update_balance(challenger_id, -bet_amount, 'duel_bet')
        self.update_balance(user_id, -bet_amount, 'duel_bet')

        # Initialize the duel
        duel_key = tuple(sorted([challenger_id, user_id]))
        self.active_duels[duel_key] = {
            'bet_amount': bet_amount,
            'players': {
                challenger_id: {'hp': 100, 'turn': False},
                user_id: {'hp': 100, 'turn': False}
            },
            'turn_order': [challenger_id, user_id],
            'current_turn': 0,
            'timestamp': timestamp
        }

        # Randomly decide who starts
        random.shuffle(self.active_duels[duel_key]['turn_order'])
        first_player_id = self.active_duels[duel_key]['turn_order'][0]
        self.active_duels[duel_key]['players'][first_player_id]['turn'] = True

        # Notify both players
        await challenger.send(f"Your duel challenge to {user.name} has been accepted! The duel has begun. Check the channel to play.")
        await user.send(f"You have accepted the duel challenge from {challenger.name}! The duel has begun. Check the channel to play.")

        channel = interaction.channel
        await channel.send(f"The duel between {challenger.mention} and {user.mention} has started! It's {self.bot.get_user(first_player_id).mention}'s turn. Use `/duel_attack` to attack.")

        # Log the command usage
        self.log_command_usage(interaction, "duel_accept", "", f"Accepted duel from {challenger.name}.")

    @discord.app_commands.command(name="duel_attack", description="Attack your opponent in the duel.")
    async def duel_attack(self, interaction: discord.Interaction):
        """Allows a player to attack their opponent in an active duel."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Find the duel the user is in
        duel_key = None
        for key in self.active_duels.keys():
            if user_id in key:
                duel_key = key
                break

        if not duel_key:
            await interaction.followup.send("You are not in an active duel.")
            return

        duel = self.active_duels[duel_key]
        players = duel['players']
        if not players[user_id]['turn']:
            await interaction.followup.send("It's not your turn.")
            return

        # Perform the attack
        opponent_id = [pid for pid in duel_key if pid != user_id][0]
        damage = random.randint(15, 30)
        players[opponent_id]['hp'] -= damage

        # Check if the opponent is defeated
        if players[opponent_id]['hp'] <= 0:
            # Duel is over
            winner_id = user_id
            loser_id = opponent_id
            winnings = duel['bet_amount'] * 2

            # Update winner's balance
            self.update_balance(winner_id, winnings, 'duel_win')

            # Notify players
            winner = await self.bot.fetch_user(winner_id)
            loser = await self.bot.fetch_user(loser_id)

            await interaction.channel.send(f"{winner.mention} attacked and dealt {damage} damage, defeating {loser.mention}!\n{winner.mention} wins {winnings} AC!")

            # Log the duel result
            self.log_duel_result(winner_id, loser_id, duel['bet_amount'], winnings)

            # Remove the duel from active duels
            del self.active_duels[duel_key]

        else:
            # Switch turns
            players[user_id]['turn'] = False
            players[opponent_id]['turn'] = True
            duel['current_turn'] += 1

            opponent = await self.bot.fetch_user(opponent_id)

            # Notify players
            await interaction.channel.send(f"{user.mention} attacked and dealt {damage} damage to {opponent.mention}. {opponent.mention} has {players[opponent_id]['hp']} HP left.\nIt's now {opponent.mention}'s turn.")
            await opponent.send(f"It's your turn in the duel against {user.name}. Use `/duel_attack` to attack.")

        # Log the command usage
        self.log_command_usage(interaction, "duel_attack", "", f"Attacked opponent, dealt {damage} damage.")

    def update_balance(self, user_id, amount, transaction_type):
        """Updates the AURAcoin balance for a user.

        Args:
            user_id: The ID of the user.
            amount: The amount to change (can be negative).
            transaction_type: The type of transaction.
        """
        balance = self.get_auracoin_balance(user_id)
        new_balance = balance + amount
        timestamp = datetime.now().isoformat()

        with self.conn:
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, new_balance, transaction_type, timestamp))

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

    def log_duel_result(self, winner_id, loser_id, bet_amount, winnings):
        """Logs the result of a duel into the duel_arena table.

        Args:
            winner_id: The ID of the winning player.
            loser_id: The ID of the losing player.
            bet_amount: The amount of AURAcoin bet by each player.
            winnings: The total amount won by the winner.
        """
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO duel_arena (winner_id, loser_id, bet_amount, winnings, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (winner_id, loser_id, bet_amount, winnings, timestamp))

    @discord.app_commands.command(name="duel_leaderboard", description="Shows the top duelists.")
    async def duel_leaderboard(self, interaction: discord.Interaction):
        """Displays the leaderboard for duels based on total winnings."""
        cursor = self.conn.cursor()

        # Query top 5 players by total winnings
        cursor.execute('''
            SELECT winner_id, SUM(winnings) as total_winnings
            FROM duel_arena
            GROUP BY winner_id
            ORDER BY total_winnings DESC
            LIMIT 5
        ''')
        winners = cursor.fetchall()

        # Format the output
        leaderboard_message = "**Top 5 Duelists:**\n"
        for i, (player_id, total_winnings) in enumerate(winners, start=1):
            user = await self.bot.fetch_user(player_id)
            leaderboard_message += f"{i}. {user.name} - {total_winnings} AC won\n"

        await interaction.response.send_message(leaderboard_message)

        # Log the command usage
        self.log_command_usage(interaction, "duel_leaderboard", "", "Displayed duel leaderboard.")

    @discord.app_commands.command(name="duel_decline", description="Decline a duel challenge.")
    async def duel_decline(self, interaction: discord.Interaction):
        """Allows a user to decline a pending duel challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if there is a pending duel
        if user_id in self.pending_duels:
            challenger_id, _ = self.pending_duels.pop(user_id)
            challenger = await self.bot.fetch_user(challenger_id)
            await interaction.followup.send("You have declined the duel challenge.")
            await challenger.send(f"{user.name} has declined your duel challenge.")

            # Log the command usage
            self.log_command_usage(interaction, "duel_decline", "", f"Declined duel from {challenger.name}.")
        else:
            await interaction.followup.send("You do not have any pending duel challenges to decline.")

    @discord.app_commands.command(name="duel_rules", description="Display the rules of the duel.")
    async def duel_rules(self, interaction: discord.Interaction):
        """Displays the rules of the duel game."""
        rules_message = (
            "**Duel Rules:**\n"
            "- Each player starts with 100 HP.\n"
            "- On your turn, use `/duel_attack` to attack your opponent.\n"
            "- Damage dealt is between 15 and 30 HP, chosen at random.\n"
            "- The first player to reduce their opponent's HP to 0 wins the duel and takes the pot.\n"
            "\n"
            "To play, challenge another user using `/duel_challenge`, specify the bet amount, and wait for them to accept. "
            "Both players take turns attacking until one is defeated."
        )
        await interaction.response.send_message(rules_message)

        # Log the command usage
        self.log_command_usage(interaction, "duel_rules", "", "Displayed duel rules.")

    @discord.app_commands.command(name="duel_cancel", description="Cancel your pending duel challenge.")
    async def duel_cancel(self, interaction: discord.Interaction):
        """Allows a user to cancel their pending duel challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if the user has issued a challenge
        for challenged_user_id, (challenger_id, _) in list(self.pending_duels.items()):
            if challenger_id == user_id:
                del self.pending_duels[challenged_user_id]
                await interaction.followup.send("Your pending duel challenge has been canceled.")
                # Log the command usage
                self.log_command_usage(interaction, "duel_cancel", "", "Canceled pending duel challenge.")
                return

        await interaction.followup.send("You do not have any pending duel challenges to cancel.")

    # Additional methods and event listeners can be added as needed

# Set up the cog
async def setup(bot):
    """Load the DuelArena cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(DuelArena(bot))
