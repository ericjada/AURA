import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
import asyncio

class RockPaperScissors(commands.Cog):
    """
    A Discord cog that allows users to play Rock-Paper-Scissors against each other using AURAcoin.
    Users can challenge others, accept challenges, and bet AURAcoin on the game.
    """

    def __init__(self, bot):
        """
        Initialize the RockPaperScissors cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')
        self.pending_challenges = {}  # Key: challenged_user_id, Value: (challenger_user_id, bet_amount)
        self.active_games = {}        # Key: (user1_id, user2_id), Value: game data

    @discord.app_commands.command(name="rps_challenge", description="Challenge another user to Rock-Paper-Scissors.")
    @discord.app_commands.describe(opponent="The user you want to challenge.", amount="The amount of AURAcoin to bet.")
    async def rps_challenge(self, interaction: discord.Interaction, opponent: discord.User, amount: int):
        """Allows a user to challenge another user to a game of Rock-Paper-Scissors."""
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
        if opponent_id in self.pending_challenges:
            await interaction.followup.send(f"{opponent.mention} already has a pending challenge.")
            return

        # Create a pending challenge
        self.pending_challenges[opponent_id] = (challenger_id, amount)
        await interaction.followup.send(f"{challenger.mention} has challenged {opponent.mention} to Rock-Paper-Scissors for {amount} AC! {opponent.mention}, type `/rps_accept` to accept the challenge.")

        # Log the command usage
        self.log_command_usage(interaction, "rps_challenge", f"Challenged {opponent.name}, Amount: {amount}", "Challenge sent.")

    @discord.app_commands.command(name="rps_accept", description="Accept a Rock-Paper-Scissors challenge.")
    async def rps_accept(self, interaction: discord.Interaction):
        """Allows a user to accept a pending Rock-Paper-Scissors challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if there is a pending challenge
        if user_id not in self.pending_challenges:
            await interaction.followup.send("You do not have any pending challenges.")
            return

        challenger_id, bet_amount = self.pending_challenges.pop(user_id)
        challenger = await self.bot.fetch_user(challenger_id)

        # Deduct the bet amount from both users
        timestamp = datetime.now().isoformat()
        self.update_balance(challenger_id, -bet_amount, 'rps_bet')
        self.update_balance(user_id, -bet_amount, 'rps_bet')

        # Initialize the game
        game_key = tuple(sorted([challenger_id, user_id]))
        self.active_games[game_key] = {
            'bet_amount': bet_amount,
            'players': {
                challenger_id: {'choice': None},
                user_id: {'choice': None}
            },
            'timestamp': timestamp
        }

        # Notify both players
        await challenger.send(f"Your challenge to {user.name} has been accepted! Please make your choice using `/rps_choice`.")
        await user.send(f"You have accepted the challenge from {challenger.name}! Please make your choice using `/rps_choice`.")

        await interaction.followup.send(f"The Rock-Paper-Scissors game between {challenger.mention} and {user.mention} has started! Both players, please check your DMs to make your choices.")

        # Log the command usage
        self.log_command_usage(interaction, "rps_accept", "", f"Accepted challenge from {challenger.name}.")

    @discord.app_commands.command(name="rps_choice", description="Make your choice in Rock-Paper-Scissors.")
    @discord.app_commands.describe(choice="Your choice: rock, paper, or scissors.")
    async def rps_choice(self, interaction: discord.Interaction, choice: str):
        """Allows a player to make their choice in an active Rock-Paper-Scissors game."""
        user = interaction.user
        user_id = user.id
        choice = choice.lower()

        await interaction.response.defer(thinking=True)

        # Validate choice
        if choice not in ['rock', 'paper', 'scissors']:
            await interaction.followup.send("Invalid choice. Please choose 'rock', 'paper', or 'scissors'.")
            return

        # Find the game the user is in
        game_key = None
        for key in self.active_games.keys():
            if user_id in key:
                game_key = key
                break

        if not game_key:
            await interaction.followup.send("You are not in an active game.")
            return

        game = self.active_games[game_key]
        player_data = game['players'][user_id]

        # Check if the user has already made a choice
        if player_data['choice'] is not None:
            await interaction.followup.send("You have already made your choice.")
            return

        # Record the player's choice
        player_data['choice'] = choice
        await interaction.followup.send(f"You have chosen {choice.capitalize()}.")

        # Log the command usage
        self.log_command_usage(interaction, "rps_choice", choice, "Choice recorded.")

        # Check if both players have made their choices
        if all(player['choice'] is not None for player in game['players'].values()):
            await self.resolve_game(game_key)

    async def resolve_game(self, game_key):
        """Resolves the Rock-Paper-Scissors game and updates balances."""
        game = self.active_games.pop(game_key)
        players = game['players']
        bet_amount = game['bet_amount']

        user_ids = list(players.keys())
        user1_id = user_ids[0]
        user2_id = user_ids[1]

        user1_choice = players[user1_id]['choice']
        user2_choice = players[user2_id]['choice']

        user1 = await self.bot.fetch_user(user1_id)
        user2 = await self.bot.fetch_user(user2_id)

        # Determine the winner
        result = self.determine_winner(user1_choice, user2_choice)

        if result == 0:
            # It's a tie, refund the bets
            self.update_balance(user1_id, bet_amount, 'rps_tie_refund')
            self.update_balance(user2_id, bet_amount, 'rps_tie_refund')

            # Notify players
            await user1.send(f"The game is a tie! Both players chose {user1_choice.capitalize()}. Your bet has been refunded.")
            await user2.send(f"The game is a tie! Both players chose {user2_choice.capitalize()}. Your bet has been refunded.")

            # Log the result
            self.log_game_result(user1_id, user2_id, 'tie', bet_amount, 0)
        else:
            # One player wins
            winner_id = user1_id if result == 1 else user2_id
            loser_id = user2_id if result == 1 else user1_id
            winner_choice = players[winner_id]['choice']
            loser_choice = players[loser_id]['choice']
            winnings = bet_amount * 2

            # Update winner's balance
            self.update_balance(winner_id, winnings, 'rps_win')

            # Notify players
            winner = await self.bot.fetch_user(winner_id)
            loser = await self.bot.fetch_user(loser_id)

            await winner.send(f"Congratulations! You won the Rock-Paper-Scissors game against {loser.name}. You chose {winner_choice.capitalize()}, and they chose {loser_choice.capitalize()}. You won {winnings} AC!")
            await loser.send(f"You lost the Rock-Paper-Scissors game against {winner.name}. You chose {loser_choice.capitalize()}, and they chose {winner_choice.capitalize()}. Better luck next time!")

            # Log the result
            self.log_game_result(winner_id, loser_id, 'win', bet_amount, winnings)

    def determine_winner(self, choice1, choice2):
        """Determines the winner of a Rock-Paper-Scissors game.

        Returns:
            int: 0 for tie, 1 if first player wins, 2 if second player wins.
        """
        if choice1 == choice2:
            return 0  # Tie
        elif (choice1 == 'rock' and choice2 == 'scissors') or \
             (choice1 == 'paper' and choice2 == 'rock') or \
             (choice1 == 'scissors' and choice2 == 'paper'):
            return 1  # First player wins
        else:
            return 2  # Second player wins

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

    def log_game_result(self, winner_id, loser_id, result, bet_amount, winnings):
        """Logs the result of a Rock-Paper-Scissors game into the rps_game table.

        Args:
            winner_id: The ID of the winning player.
            loser_id: The ID of the losing player.
            result: 'win' or 'tie'
            bet_amount: The amount of AURAcoin bet by each player.
            winnings: The total amount won by the winner.
        """
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO rps_game (winner_id, loser_id, result, bet_amount, winnings, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (winner_id if result != 'tie' else None, loser_id if result != 'tie' else None, result, bet_amount, winnings, timestamp))

    @discord.app_commands.command(name="rps_leaderboard", description="Shows the top Rock-Paper-Scissors players.")
    async def rps_leaderboard(self, interaction: discord.Interaction):
        """Displays the leaderboard for Rock-Paper-Scissors based on total winnings."""
        cursor = self.conn.cursor()

        # Query top 5 players by total winnings
        cursor.execute('''
            SELECT winner_id, SUM(winnings) as total_winnings
            FROM rps_game
            WHERE result = 'win'
            GROUP BY winner_id
            ORDER BY total_winnings DESC
            LIMIT 5
        ''')
        winners = cursor.fetchall()

        # Format the output
        leaderboard_message = "**Top 5 Rock-Paper-Scissors Players:**\n"
        for i, (player_id, total_winnings) in enumerate(winners, start=1):
            user = await self.bot.fetch_user(player_id)
            leaderboard_message += f"{i}. {user.name} - {total_winnings} AC won\n"

        await interaction.response.send_message(leaderboard_message)

        # Log the command usage
        self.log_command_usage(interaction, "rps_leaderboard", "", "Displayed RPS leaderboard.")

    @discord.app_commands.command(name="rps_cancel", description="Cancel your pending Rock-Paper-Scissors challenge.")
    async def rps_cancel(self, interaction: discord.Interaction):
        """Allows a user to cancel their pending challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if the user has issued a challenge
        for challenged_user_id, (challenger_id, _) in list(self.pending_challenges.items()):
            if challenger_id == user_id:
                del self.pending_challenges[challenged_user_id]
                await interaction.followup.send("Your pending challenge has been canceled.")
                # Log the command usage
                self.log_command_usage(interaction, "rps_cancel", "", "Canceled pending challenge.")
                return

        await interaction.followup.send("You do not have any pending challenges to cancel.")

    @discord.app_commands.command(name="rps_decline", description="Decline a Rock-Paper-Scissors challenge.")
    async def rps_decline(self, interaction: discord.Interaction):
        """Allows a user to decline a pending Rock-Paper-Scissors challenge."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        # Check if there is a pending challenge
        if user_id in self.pending_challenges:
            challenger_id, _ = self.pending_challenges.pop(user_id)
            challenger = await self.bot.fetch_user(challenger_id)
            await interaction.followup.send("You have declined the challenge.")
            await challenger.send(f"{user.name} has declined your Rock-Paper-Scissors challenge.")

            # Log the command usage
            self.log_command_usage(interaction, "rps_decline", "", f"Declined challenge from {challenger.name}.")
        else:
            await interaction.followup.send("You do not have any pending challenges to decline.")

    @discord.app_commands.command(name="rps_rules", description="Display the rules of Rock-Paper-Scissors.")
    async def rps_rules(self, interaction: discord.Interaction):
        """Displays the rules of the game."""
        rules_message = (
            "**Rock-Paper-Scissors Rules:**\n"
            "- Rock beats Scissors\n"
            "- Scissors beats Paper\n"
            "- Paper beats Rock\n"
            "\n"
            "To play, challenge another user using `/rps_challenge`, specify the bet amount, and wait for them to accept. "
            "Both players then make their choices using `/rps_choice`."
        )
        await interaction.response.send_message(rules_message)

        # Log the command usage
        self.log_command_usage(interaction, "rps_rules", "", "Displayed RPS rules.")

# Set up the cog
async def setup(bot):
    """Load the RockPaperScissors cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(RockPaperScissors(bot))
