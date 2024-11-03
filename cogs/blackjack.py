# blackjack.py

import sqlite3
import random
import uuid
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio

class BlackjackGame:
    def __init__(self, cog, channel_id):
        self.cog = cog
        self.channel_id = channel_id
        self.players = set()
        self.players_in_turn = set()
        self.player_hands = {}
        self.dealer_hand = []
        self.bets = {}
        self.deck = self.initialize_deck()
        self.game_id = str(uuid.uuid4())
        self.auracoin_cog = cog.bot.get_cog('AURAcoin')

    def initialize_deck(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [{'suit': suit, 'rank': rank} for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def add_player(self, player_id: int):
        """Add a player to the game."""
        self.players.add(player_id)
        self.players_in_turn.add(player_id)
        self.player_hands[player_id] = []

    def calculate_hand_value(self, hand):
        """Calculate the total value of a hand, handling Aces optimally."""
        value = 0
        aces = 0
        
        for card in hand:
            if card['rank'] == 'A':
                aces += 1
            else:
                if card['rank'] in ['K', 'Q', 'J']:
                    value += 10
                else:
                    value += int(card['rank'])
        
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        
        return value

    def format_hand(self, hand):
        """Formats the hand for display."""
        return ', '.join(f"{card['rank']} of {card['suit']}" for card in hand)

    def deal_initial_cards(self):
        """Deal initial cards to all players and dealer."""
        # Deal two cards to each player
        for player_id in self.players:
            self.player_hands[player_id] = [self.deck.pop() for _ in range(2)]
        
        # Deal dealer's cards
        self.dealer_hand = [self.deck.pop() for _ in range(2)]

    def hit(self, player_id):
        """Give the player another card."""
        if len(self.deck) == 0:
            self.deck = self.initialize_deck()
        self.player_hands[player_id].append(self.deck.pop())

    def stand(self, player_id):
        """Player chooses to stand."""
        self.players_in_turn.remove(player_id)

    def play_dealer_hand(self):
        """Play out the dealer's hand according to house rules."""
        while self.calculate_hand_value(self.dealer_hand) < 17:
            if len(self.deck) == 0:
                self.deck = self.initialize_deck()
            self.dealer_hand.append(self.deck.pop())

    async def place_bet(self, interaction, player_id, amount):
        """Place a bet for a player."""
        if amount < 10:
            raise ValueError("Minimum bet is 10 AC.")
        
        balance = self.auracoin_cog.get_auracoin_balance(player_id)
        if amount > balance:
            raise ValueError("Insufficient funds.")

        # Deduct bet from player's balance
        self.auracoin_cog.update_balance(player_id, -amount, 'bet')
        self.bets[player_id] = amount

    def all_bets_placed(self):
        """Check if all players have placed their bets."""
        return all(player_id in self.bets for player_id in self.players)

    def get_winnings_or_loss(self, result, player_id):
        """Calculate winnings or losses based on game result."""
        if result == "win":
            return self.bets[player_id]
        elif result == "lose":
            return -self.bets[player_id]
        else:
            return 0

    def determine_results(self, player_id=None):
        """
        Determine the results for all players or a specific player in the game.
        
        Args:
            player_id: Optional; if provided, only determine result for this player
                      if None, determine results for all players
        
        Returns:
            Dictionary with player IDs as keys and results as values,
            or a single result string if player_id is provided
        """
        # Convert interaction.user.id to int if it's an Interaction object
        if hasattr(player_id, 'user'):
            player_id = player_id.user.id
        
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        dealer_bust = dealer_value > 21

        def get_player_result(pid):
            player_hand = self.player_hands[pid]
            player_value = self.calculate_hand_value(player_hand)
            
            # Check for player bust first
            if player_value > 21:
                return "lose"
            
            # Check for player blackjack (21 with 2 cards)
            if len(player_hand) == 2 and player_value == 21:
                return "blackjack"
            
            # If dealer busts and player hasn't, player wins
            if dealer_bust:
                return "win"
            
            # Compare values for normal cases
            if player_value > dealer_value:
                return "win"
            elif player_value < dealer_value:
                return "lose"
            else:
                return "push"

        # If specific player_id provided, return only their result
        if player_id is not None:
            return get_player_result(player_id)
            
        # Otherwise return results for all players
        results = {}
        for pid in self.players:
            results[pid] = get_player_result(pid)
        return results

    def get_payout_multiplier(self, result):
        """
        Get the payout multiplier for a given result.
        """
        multipliers = {
            "blackjack": 2.5,  # Pays 3:2
            "win": 2.0,        # Pays 1:1
            "push": 1.0,       # Return original bet
            "lose": 0.0        # Lose bet
        }
        return multipliers.get(result, 0.0)

    def log_blackjack_game(self, player_id, result, bet, winnings_or_loss):
        """
        Logs the result of a Blackjack game into the blackjack_game table.
        
        Args:
            player_id: The ID of the player
            result: The game result (win/lose/push/blackjack)
            bet: The amount bet
            winnings_or_loss: The amount won or lost
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Use the cog's database connection
            with self.cog.conn:
                self.cog.conn.execute('''
                    INSERT INTO blackjack_game 
                    (game_id, channel_id, player_id, result, amount_won_lost, bet, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (self.game_id, self.channel_id, player_id, result, winnings_or_loss, bet, timestamp))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_blackjack_game: {e}")
            print(f"game_id: {self.game_id}, player_id: {player_id}")
        except Exception as e:
            print(f"Unexpected error while logging Blackjack game: {e}")

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
        self.active_games = {}  # {channel_id: BlackjackGame}
        self.game_locks = {}    # {channel_id: asyncio.Lock}
        self._setup_database()

    def _setup_database(self):
        """Initialize database with proper configuration."""
        self.conn = sqlite3.connect(
            './group_memories/aura_memory.db',
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.execute('PRAGMA journal_mode = WAL')
        
        # Create blackjack_game table if it doesn't exist
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS blackjack_game (
                game_id TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                result TEXT NOT NULL,
                amount_won_lost INTEGER NOT NULL,
                bet INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (game_id, player_id)
            )
        ''')
        self.conn.commit()

    async def get_game_lock(self, channel_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific game channel."""
        if channel_id not in self.game_locks:
            self.game_locks[channel_id] = asyncio.Lock()
        return self.game_locks[channel_id]

    @app_commands.command(name="blackjack", description="Start a game of Blackjack with AURAcoin betting.")
    async def blackjack(self, interaction: discord.Interaction):
        """Start a blackjack game with improved validation and setup."""
        channel_id = interaction.channel.id
        lock = await self.get_game_lock(channel_id)

        async with lock:
            try:
                if channel_id in self.active_games:
                    await interaction.response.send_message(
                        "A game is already in progress in this channel.",
                        ephemeral=True
                    )
                    return

                game = BlackjackGame(self, channel_id)
                self.active_games[channel_id] = game

                embed = self._create_game_start_embed(interaction.user)
                await interaction.response.send_message(embed=embed)
                self.log_command_usage(interaction, "blackjack", "", "Game started")

            except Exception as e:
                await interaction.response.send_message(
                    "Failed to start the game. Please try again.",
                    ephemeral=True
                )
                print(f"Error starting blackjack game: {e}")

    def _create_game_start_embed(self, user):
        """Create a rich embed for game start."""
        return discord.Embed(
            title="🎰 Welcome to Blackjack! 🎲",
            description=(
                f"**Game Host:** {user.mention}\n\n"
                f"**How to Play:**\n"
                f"1️⃣ `/join` - Join the game\n"
                f"2️⃣ `/bet` - Place your bet (minimum: 10 AC)\n\n"
                f"**During Your Turn:**\n"
                f"🎯 `/hit` - Draw another card\n"
                f"✋ `/stand` - Keep your current hand\n\n"
                f"*Get as close to 21 as possible without going over!*"
            ),
            color=discord.Color.brand_green()
        )

    @app_commands.command(name="join", description="Join an active Blackjack game in this channel.")
    async def join(self, interaction: discord.Interaction):
        """Allows a user to join an active Blackjack game."""
        channel_id = interaction.channel.id
        user = interaction.user

        # Check if there's an active game
        if channel_id not in self.active_games:
            await interaction.response.send_message(
                "There is no active Blackjack game in this channel. Start one with `/blackjack`.",
                ephemeral=True
            )
            return

        game = self.active_games[channel_id]
        if user.id in game.players:
            await interaction.response.send_message(
                "You have already joined the game.",
                ephemeral=True
            )
            return

        game.add_player(user.id)
        await interaction.response.send_message(f"{user.mention} has joined the Blackjack game!")

        # Log the command usage
        self.log_command_usage(interaction, "join", "", f"{user.name} joined the Blackjack game.")

    @app_commands.command(name="bet", description="Place a bet for the Blackjack game.")
    @app_commands.describe(amount="The amount of AURAcoin to bet.")
    async def bet(self, interaction: discord.Interaction, amount: int):
        """Place a bet with improved validation and feedback."""
        channel_id = interaction.channel.id
        lock = await self.get_game_lock(channel_id)

        async with lock:
            try:
                await interaction.response.defer(thinking=True)
                
                if not self._validate_bet_conditions(channel_id, interaction.user.id, amount):
                    await interaction.followup.send(
                        "Invalid bet conditions. Check your balance and game state.",
                        ephemeral=True
                    )
                    return

                game = self.active_games[channel_id]
                await game.place_bet(interaction, interaction.user.id, amount)
                
                embed = self._create_bet_embed(interaction.user, amount)
                await interaction.followup.send(embed=embed)

                if game.all_bets_placed():
                    await self._start_game_round(interaction, game)

            except ValueError as e:
                await interaction.followup.send(str(e), ephemeral=True)
            except Exception as e:
                await interaction.followup.send(
                    "An error occurred while placing your bet.",
                    ephemeral=True
                )
                print(f"Error in bet command: {e}")

    def _validate_bet_conditions(self, channel_id: int, user_id: int, amount: int) -> bool:
        """Validate betting conditions."""
        if channel_id not in self.active_games:
            return False
        
        game = self.active_games[channel_id]
        if user_id not in game.players:
            return False
            
        if amount < 10:  # Minimum bet
            return False
            
        balance = self.bot.get_cog('AURAcoin').get_auracoin_balance(user_id)
        if amount > balance:
            return False
            
        return True

    @app_commands.command(name="hit", description="Take another card in Blackjack.")
    async def hit(self, interaction: discord.Interaction):
        """Allows a player to take another card."""
        user = interaction.user
        channel_id = interaction.channel.id
        key = channel_id

        await interaction.response.defer(thinking=True)

        # Check if there's an active game
        if key not in self.active_games:
            await interaction.followup.send("There is no active Blackjack game to play. Start one with `/blackjack`.", ephemeral=True)
            return

        game = self.active_games[key]
        if user.id not in game.players_in_turn:
            await interaction.followup.send("It's not your turn or you've already stood.", ephemeral=True)
            return

        # Player takes a card
        try:
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
                await interaction.followup.send(f"{user.mention} has taken a hit.")
            else:
                try:
                    await user.send(f"You drew a card. Your hand: {game.format_hand(player_hand)} (Total: {hand_value}).")
                except discord.Forbidden:
                    await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")
                await interaction.followup.send(f"{user.mention} has taken a hit.")

            # Log the command usage
            self.log_command_usage(interaction, "hit", "", f"{user.name} hit and now has hand value {hand_value}.")

            # Check if game is over
            await self.check_game_over(interaction, game)
        except Exception as e:
            await interaction.followup.send(f"An error occurred while processing your hit: {e}", ephemeral=True)
            return

    @app_commands.command(name="stand", description="Hold your hand in Blackjack.")
    async def stand(self, interaction: discord.Interaction):
        """Allows a player to hold their hand."""
        user = interaction.user
        channel_id = interaction.channel.id
        key = channel_id

        await interaction.response.defer(thinking=True)

        # Check if there's an active game
        if key not in self.active_games:
            await interaction.followup.send("There is no active Blackjack game to play. Start one with `/blackjack`.", ephemeral=True)
            return

        game = self.active_games[key]
        if user.id not in game.players_in_turn:
            await interaction.followup.send("It's not your turn or you've already stood.", ephemeral=True)
            return

        try:
            game.stand(user.id)
            hand_value = game.calculate_hand_value(game.player_hands[user.id])
            try:
                await user.send(f"You have chosen to stand with a hand value of {hand_value}.")
            except discord.Forbidden:
                await interaction.channel.send(f"{user.mention}, I couldn't send you a DM. Please check your privacy settings.")

            await interaction.followup.send(f"{user.mention} has chosen to stand.")

            # Log the command usage
            self.log_command_usage(interaction, "stand", "", f"{user.name} stood with hand value {hand_value}.")

            # Check if game is over
            await self.check_game_over(interaction, game)
        except Exception as e:
            await interaction.followup.send(f"An error occurred while processing your stand: {e}", ephemeral=True)
            return

    async def _start_game_round(self, interaction: discord.Interaction, game: 'BlackjackGame'):
        """Start a new round with improved dealing and notification."""
        try:
            game.deal_initial_cards()
            await self._send_initial_hands(interaction, game)
            
            # Start player turns
            await self._process_player_turns(interaction, game)

        except Exception as e:
            await interaction.channel.send("An error occurred while starting the round.")
            print(f"Error starting game round: {e}")
            self._cleanup_game(game.channel_id)

    async def _send_initial_hands(self, interaction: discord.Interaction, game: 'BlackjackGame'):
        """Send initial hand information to players."""
        dealer_card = game.dealer_hand[0]
        embed = discord.Embed(
            title="🎲 The Game Begins! 🎴",
            description=(
                f"**Dealer's Visible Card:**\n"
                f"└ {self._format_card(dealer_card)}\n\n"
                f"*Check your DMs for your cards!*"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.channel.send(embed=embed)

        # Send private hands to players
        for player_id in game.players:
            try:
                user = await self.bot.fetch_user(player_id)
                hand = game.player_hands[player_id]
                await self._send_player_hand(user, hand, game)
            except discord.Forbidden:
                await interaction.channel.send(
                    f"❌ {user.mention}, I couldn't send your cards! Please enable DMs from server members."
                )

    def _format_card(self, card: dict) -> str:
        """Format a card with proper suit symbols."""
        suits = {'Hearts': '♥️', 'Diamonds': '♦️', 'Clubs': '♣️', 'Spades': '♠️'}
        return f"{card['rank']} {suits[card['suit']]}"

    async def _process_player_turns(self, interaction: discord.Interaction, game: 'BlackjackGame'):
        """Process player turns with improved turn management."""
        for player_id in game.players_in_turn.copy():
            user = await self.bot.fetch_user(player_id)
            embed = discord.Embed(
                title="Your Turn!",
                description=(
                    f"{user.mention}'s turn\n"
                    f"Use `/hit` to take another card\n"
                    f"Use `/stand` to hold"
                ),
                color=discord.Color.gold()
            )
            await interaction.channel.send(embed=embed)

    def _cleanup_game(self, channel_id: int):
        """Clean up game resources."""
        if channel_id in self.active_games:
            del self.active_games[channel_id]
        if channel_id in self.game_locks:
            del self.game_locks[channel_id]

    async def check_game_over(self, interaction, game):
        """Checks if the game is over and resolves it."""
        if not game.players_in_turn:
            # Dealer's turn
            game.play_dealer_hand()
            dealer_value = game.calculate_hand_value(game.dealer_hand)
            dealer_hand_formatted = game.format_hand(game.dealer_hand)
            
            embed = discord.Embed(
                title="🎰 Dealer's Final Hand",
                description=(
                    f"**Cards:** {dealer_hand_formatted}\n"
                    f"**Total Value:** {dealer_value}"
                ),
                color=discord.Color.blue()
            )
            await interaction.channel.send(embed=embed)

            # Results
            results = game.determine_results()
            results_embed = discord.Embed(
                title="🎲 Game Results 🎲",
                color=discord.Color.gold()
            )
            
            for player_id, result in results.items():
                user = await self.bot.fetch_user(player_id)
                result_emoji = {
                    'win': '🏆',
                    'lose': '💔',
                    'push': '🤝',
                    'blackjack': '🎉'
                }.get(result, '❓')
                
                winnings = game.get_winnings_or_loss(result, player_id)
                result_text = {
                    'win': f"Won {winnings} AC",
                    'lose': f"Lost {abs(winnings)} AC",
                    'push': "Tied - Bet Returned",
                    'blackjack': f"Blackjack! Won {winnings} AC"
                }.get(result, "Unknown result")
                
                results_embed.add_field(
                    name=f"{result_emoji} {user.name}",
                    value=result_text,
                    inline=False
                )

            await interaction.channel.send(embed=results_embed)
            
            # Cleanup
            key = game.channel_id
            if key in self.active_games:
                del self.active_games[key]

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

        # Attempt to access the AURAcoin cog
        aura_cog = self.bot.get_cog('AURAcoin')
        if not aura_cog:
            print("AURAcoin cog is not loaded. Cannot log command usage.")
            return

        # Log only by user_id, remove guild_id to prevent FOREIGN KEY constraint failures
        try:
            with aura_cog.conn:
                aura_cog.conn.execute('''
                    INSERT INTO logs (log_type, log_message, timestamp, user_id, username)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('COMMAND_USAGE', f"({username}) executed {command_name}. Input: {input_data}. Output: {output_data}", 
                      timestamp, user_id, username))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

    def _create_bet_embed(self, user, amount):
        """Create a rich embed for bet placement."""
        return discord.Embed(
            title="💰 Bet Placed!",
            description=(
                f"{user.mention} has placed a bet of {amount} AC\n"
                f"Waiting for other players..."
            ),
            color=discord.Color.blue()
        )

    async def _send_player_hand(self, user, hand, game):
        """Send an embed showing the player's current hand."""
        hand_value = game.calculate_hand_value(hand)
        
        embed = discord.Embed(
            title=f"🎴 Your Cards",
            description=(
                f"**Your Hand:**\n"
                f"└ {game.format_hand(hand)}\n\n"
                f"**Total Value:** {hand_value}\n\n"
                f"*What would you like to do?*\n"
                f"🎯 `/hit` - Draw another card\n"
                f"✋ `/stand` - Keep these cards"
            ),
            color=discord.Color.blue()
        )
        
        if len(hand) == 2 and hand_value == 21:
            embed.add_field(
                name="🎉 BLACKJACK! 🎉",
                value="Congratulations on the perfect hand!",
                inline=False
            )
        
        await user.send(embed=embed)

    def format_hand(self, hand):
        """Formats the hand for display."""
        return ', '.join(f"{card['rank']} of {card['suit']}" for card in hand)

    def play_dealer_hand(self, hand):
        """Plays the dealer's hand according to Blackjack rules."""
        while self.calculate_hand_value(hand) < 17:
            if len(self.deck) == 0:
                self.deck = self.initialize_deck()
                print("Deck reshuffled.")
            hand.append(self.deck.pop())

    async def start_round(self):
        """Starts a new round of blackjack."""
        # ... existing code ...
        
        # Initialize hands for all players
        for player_id in self.players:
            self.player_hands[player_id] = []  # Initialize empty hand for each player
            # Deal initial two cards
            self.player_hands[player_id].append(self.deck.pop())
            self.player_hands[player_id].append(self.deck.pop())
        
        # Deal dealer's cards
        self.dealer_hand = []  # Reset dealer's hand
        self.dealer_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        
        # ... rest of the method ...

    def calculate_hand_value(self, hand):
        """Calculate the total value of a hand, handling Aces optimally."""
        value = 0
        aces = 0
        
        for card in hand:
            if card['rank'] == 'A':
                aces += 1
            else:
                if card['rank'] in ['K', 'Q', 'J']:
                    value += 10
                else:
                    value += int(card['rank'])
        
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        
        return value

class Player:
    """
    Represents a player in the blackjack game.
    
    Attributes:
        user (discord.User): The Discord user
        hand (list): List of cards in player's hand
        bet (int): Current bet amount
        is_standing (bool): Whether player has chosen to stand
    """
    def __init__(self, user):
        self.user = user
        self.hand = []
        self.bet = 0
        self.is_standing = False
    
    def reset(self):
        """Reset the player's state for a new game."""
        self.hand = []
        self.bet = 0
        self.is_standing = False

# Set up the cog
async def setup(bot):
    """Load the Blackjack cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Blackjack(bot))
