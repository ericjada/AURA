# database_manager.py

import sqlite3
from discord.ext import commands

class DatabaseManager(commands.Cog):
    """
    A cog responsible for managing the database and creating necessary tables.
    """

    def __init__(self, bot):
        self.bot = bot
        # Define your database path
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Enable foreign key support
        self.conn.execute('PRAGMA foreign_keys = ON')

        # Create necessary tables
        self.create_tables()

    def create_tables(self):
        """Creates necessary tables for guilds, users, memory, and logs in the database."""
        with self.conn:
            # Create a table for storing guild information
            self.conn.execute(''' 
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY,
                    guild_name TEXT
                )
            ''')

            # Create auracoin_ledger table without guild_id
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS auracoin_ledger (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    change_amount INTEGER NOT NULL,
                    balance INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')

            # Create blackjack_game table without guild_id
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS blackjack_game (
                    game_id TEXT PRIMARY KEY,  -- Changed to TEXT to accommodate UUIDs
                    channel_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    result TEXT NOT NULL,      -- win, lose, push
                    amount_won_lost INTEGER NOT NULL,
                    bet INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')

            # Logs table without guild_id
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_type TEXT NOT NULL,
                    log_message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT
                )
            ''')

            # Create roulette_game table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS roulette_game (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    bet_type TEXT NOT NULL,      -- red, black, even, odd, number
                    bet_amount INTEGER NOT NULL,
                    outcome_number INTEGER NOT NULL,
                    outcome_color TEXT NOT NULL, -- red, black, green (for 0)
                    result TEXT NOT NULL,        -- win or lose
                    winnings INTEGER NOT NULL,   -- Amount won (or lost, 0 for a loss)
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

            # Create lottery_results table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS lottery_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    prize_amount INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

            # Create dice_duel_results table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS dice_duel_results (
                    duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    challenger_id INTEGER NOT NULL,
                    challenged_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    loser_id INTEGER NOT NULL,
                    challenger_result INTEGER NOT NULL,
                    challenged_result INTEGER NOT NULL,
                    challenger_rolls TEXT NOT NULL,
                    challenged_rolls TEXT NOT NULL,
                    dice_str TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

            # Create rps_game table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS rps_game (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    winner_id INTEGER,
                    loser_id INTEGER,
                    result TEXT NOT NULL,         -- 'win' or 'tie'
                    bet_amount INTEGER NOT NULL,
                    winnings INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

            # Create duel_arena table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS duel_arena (
                    duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    loser_id INTEGER NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    winnings INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

            # Create fishing_inventory table with guild_id NOT NULL
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS fishing_inventory (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    bait INTEGER DEFAULT 0,
                    fish_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id, fish_name),
                    FOREIGN KEY(guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                )
            ''')

    def close_connection(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

async def setup(bot):
    """Setup the cog"""
    await bot.add_cog(DatabaseManager(bot))
