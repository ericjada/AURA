import sqlite3
from discord.ext import commands

class DatabaseManager(commands.Cog):
    """
    A cog responsible for managing the database and creating necessary tables.
    """

    def __init__(self, bot):
        self.bot = bot
        # Define your database path
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')
        self.create_tables()

    def create_tables(self):
        """Creates necessary tables for guilds, users, memory, and logs in the database."""
        with self.conn:
            # Create a table for storing guild information
            self.conn.execute(''' 
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_name TEXT UNIQUE
                )
            ''')
            # Create a table for storing conversation memory
            self.conn.execute(''' 
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    username TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    session_id INTEGER,
                    context TEXT,
                    priority INTEGER DEFAULT 0,
                    sentiment TEXT,
                    memory_type TEXT,
                    FOREIGN KEY (guild_id) REFERENCES guilds (guild_id)
                )
            ''')
            # Create a table for storing user profiles
            self.conn.execute(''' 
                CREATE TABLE IF NOT EXISTS user_profiles (
                    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,  -- Unique identifier for each user
                    username TEXT,
                    profile_picture_url TEXT,
                    join_date TEXT,
                    last_active_date TEXT,
                    roles TEXT,
                    preferences TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (guild_id) REFERENCES guilds (guild_id)
                )
            ''')
            # Create auracoin_ledger table
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
            # Create blackjack_game table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS blackjack_game (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    result TEXT NOT NULL,  -- win, lose, push
                    amount_won_lost INTEGER NOT NULL,
                    bet INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            # Create logs table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_type TEXT NOT NULL,
                    log_message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    guild_id INTEGER,
                    user_id INTEGER,
                    username TEXT
                )
            ''')

    def close_connection(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

async def setup(bot):
    """Setup the cog"""
    await bot.add_cog(DatabaseManager(bot))
