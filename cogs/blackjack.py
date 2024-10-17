# blackjack.py

import sqlite3
import random
import uuid
import discord
from discord.ext import commands
from datetime import datetime

class Blackjack(commands.Cog):
    """
    A Discord cog that provides a Blackjack game with AURAcoin betting.
    """

    def __init__(self, bot):
        """
        Initialize the Blackjack cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.active_blackjack_games = {}  # Key: channel_id, Value: BlackjackGame instance

    @discord.app_commands.command(name="blackjack", description="Start a game of Blackjack with AURAcoin betting.")
    async def blackjack(self, interaction: discord.Interaction):
        """Starts a game of Blackjack."""
        channel_id = interaction.channel.id
        user = interaction.user

        key = channel_id

        # Check if there's an active game in this channel
        if key in self.active_blackjack_games:
            await interaction.response.send_message("A Blackjack game is already in progress in this channel.")
            return

        # Initialize a new game
        try:
            game = BlackjackGame(self, channel_id)
        except Exception as e:
            await interaction.response.send_message(f"Failed to start a Blackjack game: {e}")
            return

        self.active_blackjack_games[key] = game
        await interaction.response.send_message(f"{user.mention} has started a game of Blackjack! Type `/join` to join the game.")

        # Log the command usage
        self.log_command_usage(interaction, "blackjack", "", f"{user.name} started a Blackjack game.")

    @discord.app_commands.command(name="join", description="Join an active Blackjack game in this channel.")
    async def join(self, interaction: discord.Interaction):
        """Allows a user to join an active Blackjack game."""
        channel_id = interaction.channel.id
        user = interaction.user

        key = channel_id

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
        channel_id = interaction.channel.id
        user = interaction.user

        key = channel_id

        await interaction.response.defer(thinking=True)

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.followup.send("There is no active Blackjack game to bet on. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players:
            await interaction.followup.send("You need to join the game first using `/join`.")
            return

        # Place the bet
        try:
            await game.place_bet(interaction, user.id, amount)
            await interaction.followup.send(f"{user.mention} has placed a bet of {amount} AC.")
        except ValueError as e:
            await interaction.followup.send(str(e))
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
            try:
                await user.send(f"Your hand: {game.format_hand(player_hand)} (Total: {hand_value})")
                await user.send("Type `/hit` to take another card or `/stand` to hold your hand.")
            except discord.Forbidden:
                await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")

        # Notify the channel
        channel = interaction.channel
        await channel.send("All bets are placed. Players have been dealt their initial cards. Check your DMs for your hand.")

    @discord.app_commands.command(name="hit", description="Take another card in Blackjack.")
    async def hit(self, interaction: discord.Interaction):
        """Allows a player to take another card."""
        user = interaction.user
        channel_id = interaction.channel.id
        key = channel_id

        await interaction.response.defer(thinking=True)

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.followup.send("There is no active Blackjack game to play. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players_in_turn:
            await interaction.followup.send("It's not your turn or you've already stood.")
            return

        # Player takes a card
        game.hit(user.id)
        player_hand = game.player_hands[user.id]
        hand_value = game.calculate_hand_value(player_hand)

        # Check for bust
        if hand_value > 21:
            try:
                await user.send(f"You drew a card. Your hand: {game.format_hand(player_hand)} (Total: {hand_value}). You busted!")
            except discord.Forbidden:
                await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")
            game.players_in_turn.remove(user.id)
        else:
            try:
                await user.send(f"You drew a card. Your hand: {game.format_hand(player_hand)} (Total: {hand_value}).")
            except discord.Forbidden:
                await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")

        # Log the command usage
        self.log_command_usage(interaction, "hit", "", f"{user.name} hit and now has hand value {hand_value}.")

        # Check if game is over
        await self.check_game_over(interaction, game)

    @discord.app_commands.command(name="stand", description="Hold your hand in Blackjack.")
    async def stand(self, interaction: discord.Interaction):
        """Allows a player to hold their hand."""
        user = interaction.user
        channel_id = interaction.channel.id
        key = channel_id

        await interaction.response.defer(thinking=True)

        # Check if there's an active game
        if key not in self.active_blackjack_games:
            await interaction.followup.send("There is no active Blackjack game to play. Start one with `/blackjack`.")
            return

        game = self.active_blackjack_games[key]
        if user.id not in game.players_in_turn:
            await interaction.followup.send("It's not your turn or you've already stood.")
            return

        game.players_in_turn.remove(user.id)
        hand_value = game.calculate_hand_value(game.player_hands[user.id])
        try:
            await user.send(f"You have chosen to stand with a hand value of {hand_value}.")
        except discord.Forbidden:
            await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")

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
            results = await game.determine_results(interaction)
            for player_id, result in results.items():
                user = await self.bot.fetch_user(player_id)
                if result == 'win':
                    await channel.send(f"{user.mention} wins!")
                elif result == 'lose':
                    await channel.send(f"{user.mention} loses.")
                elif result == 'push':
                    await channel.send(f"{user.mention} pushes (tie).")

                # Log the game result in the blackjack_game table
                game.log_blackjack_game(player_id, result, game.bets[player_id], game.get_winnings_or_loss(result, player_id))

            # Remove the game from active games
            key = game.channel_id
            if key in self.active_blackjack_games:
                del self.active_blackjack_games[key]

            # Final follow-up to conclude the interaction
            await interaction.followup.send("The Blackjack game has concluded.", ephemeral=True)

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
        username = interaction.user.name

        # Log only by user_id, remove guild_id to prevent FOREIGN KEY constraint failures
        try:
            with self.bot.get_cog('AURAcoin').conn:
                self.bot.get_cog('AURAcoin').conn.execute('''
                    INSERT INTO logs (log_type, log_message, timestamp, user_id, username)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, user_id, username))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

class BlackjackGame:
    """Class to manage a Blackjack game."""

    def __init__(self, cog, channel_id):
        self.cog = cog
        self.channel_id = channel_id
        self.game_id = str(uuid.uuid4())  # Unique identifier for the game
        self.players = []
        self.bets = {}
        self.player_hands = {}
        self.dealer_hand = []
        self.deck = self.initialize_deck()
        self.players_in_turn = []

        # Access the AURAcoin cog
        self.auracoin_cog = cog.bot.get_cog('AURAcoin')
        if not self.auracoin_cog:
            raise Exception("AURAcoin cog is not loaded.")

        # Get database connection
        self.conn = self.auracoin_cog.conn

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

    async def place_bet(self, interaction, player_id, amount):
        """Places a bet for a player."""
        balance = self.auracoin_cog.get_auracoin_balance(player_id)
        if amount > balance:
            raise ValueError(f"You have insufficient AURAcoin balance. Your balance is {balance} AC.")
        self.bets[player_id] = amount
        # Update balance
        self.auracoin_cog.update_balance(player_id, -amount, 'bet')

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

    async def determine_results(self, interaction):
        """Determines the result for each player."""
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        results = {}
        for player_id in self.players:
            player_value = self.calculate_hand_value(self.player_hands[player_id])
            bet = self.bets[player_id]
            if player_value > 21:
                # Player busts
                results[player_id] = 'lose'
                # No balance update needed (bet already deducted)
            elif dealer_value > 21 or player_value > dealer_value:
                # Player wins
                winnings = bet * 2
                # Update balance
                self.auracoin_cog.update_balance(player_id, winnings, 'win')
                results[player_id] = 'win'
            elif player_value == dealer_value:
                # Push (tie), return bet
                # Update balance
                self.auracoin_cog.update_balance(player_id, bet, 'push')
                results[player_id] = 'push'
            else:
                # Player loses
                results[player_id] = 'lose'
                # No balance update needed (bet already deducted)
        return results

    def get_winnings_or_loss(self, result, player_id):
        """Returns the amount won or lost based on the game result."""
        if result == "win":
            return self.bets[player_id]
        elif result == "lose":
            return -self.bets[player_id]
        else:
            return 0  # Push (tie), no gain or loss

    def log_blackjack_game(self, player_id, result, bet, winnings_or_loss):
        """Logs the result of a Blackjack game into the blackjack_game table."""
        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO blackjack_game (game_id, channel_id, player_id, result, amount_won_lost, bet, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.game_id, self.channel_id, player_id, result, winnings_or_loss, bet, timestamp))

# Set up the cog
async def setup(bot):
    """Load the Blackjack cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Blackjack(bot))
