import random
import discord
from discord.ext import commands
from datetime import datetime
import sqlite3

class Games(commands.Cog):
    """
    A Discord cog that provides various games and fun commands,
    including dice rolls, coin flips, Magic 8-Ball responses, and a Blackjack game with AURAcoin betting.
    """

    def __init__(self, bot):
        """
        Initialize the Games cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')
        self.active_blackjack_games = {}  # Key: (guild_id, channel_id), Value: BlackjackGame instance


    @discord.app_commands.command(name="balance", description="Check your AURAcoin balance.")
    async def balance(self, interaction: discord.Interaction):
        """Checks the user's AURAcoin balance and grants a daily bonus if eligible."""
        user_id = interaction.user.id
        # Check and grant daily bonus if eligible
        daily_bonus_granted = self.check_and_grant_daily_bonus(user_id)
        balance = self.get_auracoin_balance(user_id)
        if daily_bonus_granted:
            await interaction.response.send_message(f"You have received your daily bonus of 100 AC!\nYour AURAcoin balance is: {balance} AC")
        else:
            await interaction.response.send_message(f"Your AURAcoin balance is: {balance} AC")

        # Log the command usage
        self.log_command_usage(interaction, "balance", "", f"Balance: {balance} AC")

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
            last_bonus_time = datetime.fromisoformat(result[0])
            time_since_last_bonus = now - last_bonus_time
            if time_since_last_bonus.total_seconds() < 24 * 3600:
                # Not eligible yet
                return False
        # Grant the bonus
        balance = self.get_auracoin_balance(player_id)
        new_balance = balance + 100
        timestamp = now.isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (player_id, 100, new_balance, 'daily_bonus', timestamp))
        return True

    def get_auracoin_balance(self, player_id):
        """Get the AURAcoin balance for a player."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT balance FROM auracoin_ledger WHERE player_id = ? ORDER BY transaction_id DESC LIMIT 1", (player_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    @discord.app_commands.command(name="blackjack", description="Play a game of Blackjack with AURAcoin betting.")
    async def blackjack(self, interaction: discord.Interaction):
        """Starts a game of Blackjack."""
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        user = interaction.user

        key = (guild_id, channel_id)

        # Check if there's an active game in this channel
        if key in self.active_blackjack_games:
            await interaction.response.send_message("A Blackjack game is already in progress in this channel.")
            return

        # Initialize a new game
        game = BlackjackGame(self, guild_id, channel_id)
        self.active_blackjack_games[key] = game
        await interaction.response.send_message(f"{user.mention} has started a game of Blackjack! Type `/join` to join the game.")

        # Log the command usage
        self.log_command_usage(interaction, "blackjack", "", f"{user.name} started a Blackjack game.")

    @discord.app_commands.command(name="join", description="Join an active Blackjack game in this channel.")
    async def join(self, interaction: discord.Interaction):
        """Allows a user to join an active Blackjack game."""
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        user = interaction.user

        key = (guild_id, channel_id)

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.response.send_message("There is no active Blackjack game in this channel. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id in game.players:
            await interaction.response.send_message("You have already joined the game.")
            return

        game.add_player(user.id)
        await interaction.response.send_message(f"{user.mention} has joined the Blackjack game!")

        # Log the command usage
        self.log_command_usage(interaction, "join", "", f"{user.name} joined the Blackjack game.")

    @discord.app_commands.command(name="bet", description="Place a bet for the Blackjack game.")
    @discord.app_commands.describe(amount="The amount of AURAcoin to bet.")
    async def bet(self, interaction: discord.Interaction, amount: int):
        """Allows a player to place a bet."""
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        user = interaction.user

        key = (guild_id, channel_id)

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.response.send_message("There is no active Blackjack game to bet on. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players:
            await interaction.response.send_message("You need to join the game first using `/join`.")
            return

        # Place the bet
        try:
            game.place_bet(user.id, amount)
            await interaction.response.send_message(f"{user.mention} has placed a bet of {amount} AC.")
        except ValueError as e:
            await interaction.response.send_message(str(e))
            return

        # Log the command usage
        self.log_command_usage(interaction, "bet", str(amount), f"{user.name} placed a bet of {amount} AC.")

        # Check if all players have placed bets
        if game.all_bets_placed():
            await self.start_blackjack_game(interaction, game)

    async def start_blackjack_game(self, interaction, game):
        """Starts the Blackjack game after all bets are placed."""
        game.deal_initial_cards()
        for player_id in game.players:
            user = await self.bot.fetch_user(player_id)
            player_hand = game.player_hands[player_id]
            hand_value = game.calculate_hand_value(player_hand)
            await user.send(f"Your hand: {game.format_hand(player_hand)} (Total: {hand_value})")
            await user.send("Type `/hit` to take another card or `/stand` to hold your hand.")

        # Notify the channel
        channel = interaction.channel
        await channel.send("All bets are placed. Players have been dealt their initial cards. Check your DMs for your hand.")

    @discord.app_commands.command(name="hit", description="Take another card in Blackjack.")
    async def hit(self, interaction: discord.Interaction):
        """Allows a player to take another card."""
        user = interaction.user
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        key = (guild_id, channel_id)

        # Acknowledge the interaction to prevent timeout
        await interaction.response.defer()

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.response.send_message("There is no active Blackjack game to play. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players_in_turn:
            await interaction.response.send_message("It's not your turn or you've already stood.")
            return

        # Player takes a card
        game.hit(user.id)
        player_hand = game.player_hands[user.id]
        hand_value = game.calculate_hand_value(player_hand)

        # Check for bust
        if hand_value > 21:
            await user.send(f"You drew a card. Your hand: {game.format_hand(player_hand)} (Total: {hand_value}). You busted!")
            game.players_in_turn.remove(user.id)
        else:
            await user.send(f"You drew a card. Your hand: {game.format_hand(player_hand)} (Total: {hand_value}).")

        # Log the command usage
        self.log_command_usage(interaction, "hit", "", f"{user.name} hit and now has hand value {hand_value}.")

        # Check if game is over
        await self.check_game_over(interaction, game)

    @discord.app_commands.command(name="stand", description="Hold your hand in Blackjack.")
    async def stand(self, interaction: discord.Interaction):
        """Allows a player to hold their hand."""
        user = interaction.user
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        key = (guild_id, channel_id)

        # Acknowledge the interaction to prevent timeout
        await interaction.response.defer()

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.response.send_message("There is no active Blackjack game to play. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players_in_turn:
            await interaction.response.send_message("It's not your turn or you've already stood.")
            return

        game.players_in_turn.remove(user.id)
        hand_value = game.calculate_hand_value(game.player_hands[user.id])
        await user.send(f"You have chosen to stand with a hand value of {hand_value}.")

        # Log the command usage
        self.log_command_usage(interaction, "stand", "", f"{user.name} stood with hand value {hand_value}.")

        # Check if game is over
        await self.check_game_over(interaction, game)

    async def check_game_over(self, interaction, game):
        """Checks if the game is over and resolves it."""
        if not game.players_in_turn:
            # All players have stood or busted, dealer's turn
            game.play_dealer_hand()
            dealer_hand_value = game.calculate_hand_value(game.dealer_hand)
            dealer_hand_formatted = game.format_hand(game.dealer_hand)
            channel = interaction.channel
            await channel.send(f"Dealer's hand: {dealer_hand_formatted} (Total: {dealer_hand_value})")
            # Determine results and update balances
            results = game.determine_results()
            for player_id, result in results.items():
                user = await self.bot.fetch_user(player_id)
                if result == 'win':
                    await channel.send(f"{user.mention} wins!")
                elif result == 'lose':
                    await channel.send(f"{user.mention} loses.")
                elif result == 'push':
                    await channel.send(f"{user.mention} pushes (tie).")

                # Log the game result in the blackjack_game table
                self.log_blackjack_game(game.guild_id, game.channel_id, player_id, result, game.bets[player_id], game.get_winnings_or_loss(result, player_id))

            # Remove the game from active games
            key = (game.guild_id, game.channel_id)
            del self.active_blackjack_games[key]

    def log_blackjack_game(self, guild_id, channel_id, player_id, result, bet, winnings_or_loss):
        """Logs the result of a Blackjack game into the blackjack_game table."""
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO blackjack_game (guild_id, channel_id, player_id, result, amount_won_lost, bet, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, channel_id, player_id, result, winnings_or_loss, bet, timestamp))

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

    @discord.app_commands.command(name="leaderboard", description="Shows the top 5 Blackjack winners and losers.")
    async def leaderboard(self, interaction: discord.Interaction):
        """Displays the top 5 winners and losers in Blackjack based on their overall winnings/losses."""
        cursor = self.conn.cursor()

        # Query top 5 winners
        cursor.execute('''
            SELECT player_id, SUM(amount_won_lost) as total_won
            FROM blackjack_game
            WHERE result = 'win'
            GROUP BY player_id
            ORDER BY total_won DESC
            LIMIT 5
        ''')
        winners = cursor.fetchall()

        # Query top 5 losers
        cursor.execute('''
            SELECT player_id, SUM(amount_won_lost) as total_lost
            FROM blackjack_game
            WHERE result = 'lose'
            GROUP BY player_id
            ORDER BY total_lost ASC
            LIMIT 5
        ''')
        losers = cursor.fetchall()

        # Format the output
        leaderboard_message = "**Top 5 Winners:**\n"
        for i, (player_id, total_won) in enumerate(winners, start=1):
            user = await self.bot.fetch_user(player_id)
            leaderboard_message += f"{i}. {user.name} - {total_won} AC\n"

        leaderboard_message += "\n**Top 5 Losers:**\n"
        for i, (player_id, total_lost) in enumerate(losers, start=1):
            user = await self.bot.fetch_user(player_id)
            leaderboard_message += f"{i}. {user.name} - {total_lost} AC\n"

        await interaction.response.send_message(leaderboard_message)

class BlackjackGame:
    """Class to manage a Blackjack game."""

    def __init__(self, cog, guild_id, channel_id):
        self.cog = cog
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.players = []
        self.bets = {}
        self.player_hands = {}
        self.dealer_hand = []
        self.deck = self.initialize_deck()
        self.players_in_turn = []

    def initialize_deck(self):
        """Initializes and shuffles the deck."""
        deck = []
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
            '7': 7, '8': 8, '9': 9, '10': 10,
            'Jack': 10, 'Queen': 10, 'King': 10, 'Ace': 11
        }
        for suit in suits:
            for rank, value in ranks.items():
                deck.append({'rank': rank, 'suit': suit, 'value': value})
        random.shuffle(deck)
        return deck

    def add_player(self, player_id):
        """Adds a player to the game."""
        self.players.append(player_id)
        self.bets[player_id] = 0
        self.player_hands[player_id] = []

    def place_bet(self, player_id, amount):
        """Places a bet for a player."""
        balance = self.cog.get_auracoin_balance(player_id)
        if amount > balance:
            raise ValueError(f"You have insufficient AURAcoin balance. Your balance is {balance} AC.")
        self.bets[player_id] = amount
        new_balance = balance - amount
        timestamp = datetime.now().isoformat()
        with self.cog.conn:
            self.cog.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (player_id, -amount, new_balance, 'bet', timestamp))

    def all_bets_placed(self):
        """Checks if all players have placed their bets."""
        return all(bet > 0 for bet in self.bets.values())

    def deal_initial_cards(self):
        """Deals initial two cards to each player and the dealer."""
        for player_id in self.players:
            self.player_hands[player_id] = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.players_in_turn = self.players.copy()

    def hit(self, player_id):
        """Deals one card to the player."""
        self.player_hands[player_id].append(self.deck.pop())

    def calculate_hand_value(self, hand):
        """Calculates the value of a hand."""
        value = sum(card['value'] for card in hand)
        # Adjust for Aces
        num_aces = sum(1 for card in hand if card['rank'] == 'Ace')
        while value > 21 and num_aces:
            value -= 10
            num_aces -= 1
        return value

    def format_hand(self, hand):
        """Formats the hand for display."""
        return ', '.join(f"{card['rank']} of {card['suit']}" for card in hand)

    def play_dealer_hand(self):
        """Plays the dealer's hand according to Blackjack rules."""
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

    def determine_results(self):
        """Determines the result for each player."""
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        results = {}
        for player_id in self.players:
            player_value = self.calculate_hand_value(self.player_hands[player_id])
            bet = self.bets[player_id]
            timestamp = datetime.now().isoformat()
            if player_value > 21:
                # Player busts
                results[player_id] = 'lose'
                # No balance update needed (bet already deducted)
            elif dealer_value > 21 or player_value > dealer_value:
                # Player wins
                winnings = bet * 2
                balance = self.cog.get_auracoin_balance(player_id)
                new_balance = balance + winnings
                with self.cog.conn:
                    self.cog.conn.execute('''
                        INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (player_id, winnings, new_balance, 'win', timestamp))
                results[player_id] = 'win'
            elif player_value == dealer_value:
                # Push (tie), return bet
                balance = self.cog.get_auracoin_balance(player_id)
                new_balance = balance + bet
                with self.cog.conn:
                    self.cog.conn.execute('''
                        INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (player_id, bet, new_balance, 'push', timestamp))
                results[player_id] = 'push'
            else:
                # Player loses
                results[player_id] = 'lose'
                # No balance update needed (bet already deducted)
        return results

    def get_winnings_or_loss(self, result, player_id):
        """Returns the amount won or lost based on the game result."""
        if result == "win":
            return self.bets[player_id] * 2
        elif result == "lose":
            return -self.bets[player_id]
        else:
            return 0

# Set up the cog
async def setup(bot):
    """Load the Games cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Games(bot))
