import random
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import sqlite3
import asyncio
import aiohttp
import json
import os
from typing import Dict, Optional, List

class Trivia(commands.Cog):
    """A Discord cog for an LLM-powered trivia game with betting."""
    
    def __init__(self, bot):
        self.bot = bot
        self._setup_database()
        self.active_games: Dict[int, 'TriviaGame'] = {}  # channel_id: game
        self.cooldowns: Dict[int, datetime] = {}  # user_id: last_play_time
        self.lock = asyncio.Lock()
        self.COOLDOWN_MINUTES = 5
        self.MIN_BET = 10
        self.MAX_BET = 1000
        
    def _setup_database(self):
        """Initialize database with proper configuration."""
        self.conn = sqlite3.connect(
            './group_memories/aura_memory.db',
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.execute('PRAGMA journal_mode = WAL')

    async def _check_cooldown(self, user_id: int) -> Optional[int]:
        """Check if user is on cooldown. Returns remaining seconds if on cooldown."""
        if user_id in self.cooldowns:
            elapsed = datetime.now() - self.cooldowns[user_id]
            if elapsed < timedelta(minutes=self.COOLDOWN_MINUTES):
                return int((timedelta(minutes=self.COOLDOWN_MINUTES) - elapsed).total_seconds())
        return None

    @discord.app_commands.command(name="trivia", description="Play a trivia game with AURAcoin betting")
    @discord.app_commands.describe(amount="Amount of AURAcoin to bet (10-1000 AC)")
    async def trivia(self, interaction: discord.Interaction, amount: int):
        """Start a new trivia game with betting."""
        try:
            await interaction.response.defer(thinking=True)
            
            if not await self._validate_trivia_start(interaction, amount):
                return
                
            async with self.lock:
                game = TriviaGame(self.bot, interaction.channel_id, interaction.user.id, amount)
                self.active_games[interaction.channel_id] = game
                
                # Generate and send question
                question_data = await self._generate_trivia_question()
                if not question_data:
                    await self._handle_generation_failure(interaction, amount)
                    return
                    
                await game.start_game(interaction, question_data)
                self.cooldowns[interaction.user.id] = datetime.now()

        except Exception as e:
            await self._handle_error(interaction, "starting trivia game", e)

    async def _validate_trivia_start(self, interaction: discord.Interaction, amount: int) -> bool:
        """Validate conditions for starting a trivia game."""
        # Check cooldown
        remaining_cooldown = await self._check_cooldown(interaction.user.id)
        if remaining_cooldown:
            await interaction.followup.send(
                f"You must wait {remaining_cooldown} seconds before playing again.",
                ephemeral=True
            )
            return False

        # Validate bet amount
        if not self.MIN_BET <= amount <= self.MAX_BET:
            await interaction.followup.send(
                f"Bet must be between {self.MIN_BET} and {self.MAX_BET} AC.",
                ephemeral=True
            )
            return False

        # Check active game
        if interaction.channel_id in self.active_games:
            await interaction.followup.send(
                "A game is already in progress in this channel.",
                ephemeral=True
            )
            return False

        # Check balance
        balance = self.bot.get_cog('AURAcoin').get_auracoin_balance(interaction.user.id)
        if amount > balance:
            await interaction.followup.send(
                f"Insufficient balance. You have {balance} AC.",
                ephemeral=True
            )
            return False

        return True

    async def _generate_trivia_question(self) -> Optional[dict]:
        """Generate a trivia question using Ollama API with improved error handling."""
        prompt = (
            "Generate a single trivia question with 4 options. Format exactly as follows:\n"
            "Question: [Your question here]\n"
            "A) [First option]\n"
            "B) [Second option]\n"
            "C) [Third option]\n"
            "D) [Fourth option]\n"
            "Answer: [A/B/C/D]\n"
            "Explanation: [Brief explanation]\n"
        )

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                # Debug log
                print("Sending request to Ollama API...")
                
                async with session.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        print(f"Ollama API error: Status {response.status}")
                        print(f"Response text: {await response.text()}")
                        return None

                    try:
                        result = await response.json()
                        content = result.get('response', '')
                        
                        # Debug log
                        print("Raw API response:", content)
                        
                        if not content:
                            print("Empty response from API")
                            return None
                            
                        # Parse the response
                        parsed = self._parse_question_response(content)
                        if parsed:
                            print("Successfully parsed question:", parsed)
                            return parsed
                        else:
                            print("Failed to parse question response")
                            return None

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        return None

        except aiohttp.ClientError as e:
            print(f"HTTP request error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in question generation: {e}")
            return None

    def _parse_question_response(self, content: str) -> Optional[dict]:
        """Parse LLM response into structured question data."""
        try:
            # Debug log
            print("Starting to parse content:", content)
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            data = {
                'question': None,
                'options': [],
                'answer': None,
                'explanation': None
            }

            # More flexible question parsing
            for line in lines:
                if line.lower().startswith('here is') or line.lower().startswith('this is'):
                    continue
                elif 'question' not in line.lower() and data['question'] is None and '?' in line:
                    data['question'] = line.strip()
                elif line.startswith('Question:'):
                    data['question'] = line[9:].strip()
                elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                    data['options'].append(line[3:].strip())
                elif line.startswith('Answer:'):
                    # Handle combined answer and explanation
                    answer_text = line[7:].strip()
                    if ')' in answer_text:
                        # Split on first occurrence of ')'
                        answer_part, explanation_part = answer_text.split(')', 1)
                        answer = answer_part.strip().upper()
                        if 'explanation:' in explanation_part.lower():
                            data['explanation'] = explanation_part.split(':', 1)[1].strip()
                        else:
                            data['explanation'] = explanation_part.strip()
                    else:
                        answer = answer_text.strip().upper()
                    
                    # Clean up the answer to just the letter
                    answer = answer.replace(')', '').strip()
                    if answer in ['A', 'B', 'C', 'D']:
                        data['answer'] = answer
                elif line.startswith('Explanation:'):
                    data['explanation'] = line[12:].strip()

            # If no explanation was provided, generate a simple one
            if not data['explanation'] and data['answer']:
                option_index = ord(data['answer']) - ord('A')
                if 0 <= option_index < len(data['options']):
                    data['explanation'] = f"The correct answer is {data['options'][option_index]}."

            # Validate parsed data
            if (data['question'] and 
                len(data['options']) == 4 and 
                data['answer'] and 
                data['explanation']):
                return data
            else:
                print("Invalid parsed data:", data)
                return None

        except Exception as e:
            print(f"Error parsing question response: {e}")
            return None

    async def _handle_generation_failure(self, interaction: discord.Interaction, amount: int):
        """Handle failure to generate question and refund bet."""
        try:
            auracoin_cog = self.bot.get_cog('AURAcoin')
            auracoin_cog.update_balance(
                interaction.user.id,
                amount,
                'trivia_refund'
            )
            await interaction.followup.send(
                "Failed to generate question. Your bet has been refunded.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error handling generation failure: {e}")

    async def _handle_error(self, interaction: discord.Interaction, action: str, error: Exception):
        """Handle errors uniformly."""
        error_msg = f"An error occurred while {action}."
        print(f"{error_msg} Error: {str(error)}")
        try:
            await interaction.followup.send(error_msg, ephemeral=True)
        except discord.NotFound:
            pass

class TriviaGame:
    """Manages a single trivia game instance."""
    
    def __init__(self, bot, channel_id: int, player_id: int, bet_amount: int):
        self.bot = bot
        self.channel_id = channel_id
        self.player_id = player_id
        self.bet_amount = bet_amount
        self.question_data = None
        self.answered = False
        self.timeout = 30.0

    async def start_game(self, interaction: discord.Interaction, question_data: dict):
        """Start the game with the generated question."""
        self.question_data = question_data
        
        embed = discord.Embed(
            title="🎯 Trivia Question",
            description=self.question_data['question'],
            color=discord.Color.blue()
        )
        
        for letter, option in zip(['A', 'B', 'C', 'D'], self.question_data['options']):
            embed.add_field(
                name=f"Option {letter}",
                value=option,
                inline=False
            )
        
        embed.set_footer(text=f"Bet: {self.bet_amount} AC | Time: {int(self.timeout)} seconds")
        await interaction.followup.send(embed=embed)
        
        # Start answer handling
        self.bot.loop.create_task(self._handle_answer(interaction))

    async def _handle_answer(self, interaction: discord.Interaction):
        """Handle user answer with timeout."""
        def check(m):
            return (
                m.author.id == self.player_id and
                m.channel.id == self.channel_id and
                m.content.upper() in ['A', 'B', 'C', 'D']
            )

        try:
            message = await self.bot.wait_for('message', check=check, timeout=self.timeout)
            await self._process_answer(interaction, message.content.upper())
        except asyncio.TimeoutError:
            await self._handle_timeout(interaction)
        finally:
            self._cleanup_game()

    async def _process_answer(self, interaction: discord.Interaction, answer: str):
        """Process the player's answer."""
        correct = answer == self.question_data['answer']
        
        embed = discord.Embed(
            title="🎯 Trivia Result",
            description=(
                f"Your answer: {answer}\n"
                f"Correct answer: {self.question_data['answer']}\n\n"
                f"Explanation: {self.question_data['explanation']}"
            ),
            color=discord.Color.green() if correct else discord.Color.red()
        )

        if correct:
            winnings = self.bet_amount * 2
            self.bot.get_cog('AURAcoin').update_balance(
                self.player_id,
                winnings,
                'trivia_win'
            )
            embed.add_field(
                name="Winnings",
                value=f"You won {winnings} AC!",
                inline=False
            )
        else:
            embed.add_field(
                name="Result",
                value=f"You lost {self.bet_amount} AC!",
                inline=False
            )

        await interaction.channel.send(embed=embed)

    async def _handle_timeout(self, interaction: discord.Interaction):
        """Handle timeout case."""
        embed = discord.Embed(
            title="⏰ Time's Up!",
            description=(
                f"The correct answer was: {self.question_data['answer']}\n"
                f"Explanation: {self.question_data['explanation']}"
            ),
            color=discord.Color.red()
        )
        embed.add_field(
            name="Result",
            value=f"You lost {self.bet_amount} AC!",
            inline=False
        )
        await interaction.channel.send(embed=embed)

    def _cleanup_game(self):
        """Clean up game resources."""
        if self.channel_id in self.bot.get_cog('Trivia').active_games:
            del self.bot.get_cog('Trivia').active_games[self.channel_id]

async def setup(bot):
    """Load the Trivia cog."""
    await bot.add_cog(Trivia(bot))
