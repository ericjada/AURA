import random
import discord
from discord.ext import commands
from datetime import datetime
import sqlite3  # Import sqlite3 for database interaction

class Games(commands.Cog):
    """
    A Discord cog that provides various games and fun commands,
    including dice rolls, coin flips, and Magic 8-Ball responses.
    """

    def __init__(self, bot):
        """
        Initialize the Games cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        # Assuming the database connection is initialized here
        self.conn = sqlite3.connect('./group_memories/aura_memory.db')  # Update with the correct path

    @discord.app_commands.command(name="roll", description="Rolls dice in NdN format with an optional modifier (e.g., 2d6+2).")
    @discord.app_commands.describe(dice="The dice roll format (e.g., 2d6 or 2d6+2)")
    async def roll(self, interaction: discord.Interaction, dice: str):
        """Rolls dice in NdN format, adds a modifier, and shows the total.

        Args:
            interaction: The interaction that triggered this command.
            dice: The dice roll format string, e.g., "2d6" or "2d6+2".
        """
        print(f"{interaction.user} used /roll with argument: {dice}")
        try:
            # Parse the dice input to separate the dice part and modifier
            if '+' in dice:
                dice_part, modifier = dice.split('+')
                modifier = int(modifier)  # Convert modifier to an integer
            else:
                dice_part = dice
                modifier = 0  # No modifier if not present

            # Split the dice part into number of rolls and the limit of the dice
            rolls, limit = map(int, dice_part.split('d'))

            # Validation checks
            if rolls <= 0 or limit <= 0:
                await interaction.response.send_message("Number of rolls and limit must be greater than zero.")
                return
            if rolls > 100:
                await interaction.response.send_message("You can only roll a maximum of 100 dice at a time.")
                return

        except ValueError:
            # Handle incorrect format for dice input
            await interaction.response.send_message('Format has to be in NdN or NdN+M! Example: 2d6 or 2d6+2')
            return

        # Perform the dice rolls
        individual_rolls = [random.randint(1, limit) for _ in range(rolls)]  # Generate random rolls
        total = sum(individual_rolls) + modifier  # Calculate total with modifier

        # Respond with results
        if rolls > 20:
            result_message = f'Rolled {rolls}d{limit} | Total: {total} | Too many results to display!'
        else:
            result = ', '.join(str(roll) for roll in individual_rolls)  # Format individual rolls for output
            result_message = f'Rolls: {result} | Total: {total}'

        await interaction.response.send_message(result_message)

        # Save the command input and output to memory
        self.save_roll_memory(interaction, dice, result_message)

        # Log the command usage
        self.log_command_usage(interaction, "roll", dice, result_message)

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
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        username = interaction.user.name

        with self.conn:
            self.conn.execute(''' 
                INSERT INTO logs (log_type, log_message, timestamp, guild_id, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, guild_id, user_id, username))

    def save_roll_memory(self, interaction, dice_input, result_output):
        """Saves the roll command input and output to the memory database.

        Args:
            interaction: The interaction that triggered this command.
            dice_input: The input used in the roll command.
            result_output: The output generated from the roll command.
        """
        timestamp = datetime.now().isoformat()
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        username = interaction.user.name

        with self.conn:
            self.conn.execute(''' 
                INSERT INTO memories (guild_id, channel_id, user_id, username, content, timestamp, role, memory_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, channel_id, user_id, username, f"Input: {dice_input} | Output: {result_output}", timestamp, 'user', 'DICE_ROLL'))

    @discord.app_commands.command(name="coinflip", description="Flips a coin and returns heads or tails.")
    async def coinflip(self, interaction: discord.Interaction):
        """Flips a coin and returns heads or tails.

        Args:
            interaction: The interaction that triggered this command.
        """
        print(f"{interaction.user} used /coinflip")
        result = random.choice(["Heads", "Tails"])  # Randomly choose Heads or Tails
        await interaction.response.send_message(f"The coin landed on: {result}")

        # Log the command usage
        self.log_command_usage(interaction, "coinflip", "", result)

    @discord.app_commands.command(name="eightball", description="Ask the Magic 8-Ball a yes/no question.")
    @discord.app_commands.describe(question="Your yes/no question for the Magic 8-Ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        """Answers a yes/no question using a set of predefined responses.

        Args:
            interaction: The interaction that triggered this command.
            question: The yes/no question to ask the Magic 8-Ball.
        """
        print(f"{interaction.user} used /eightball with question: {question}")
        responses = [
            "Yes", "No", "Maybe", "Definitely", "Absolutely not", 
            "I wouldn't count on it", "Yes, in due time", "Ask again later"
        ]
        response = random.choice(responses)  # Send a random response
        await interaction.response.send_message(f"🎱 {response}")

        # Log the command usage
        self.log_command_usage(interaction, "eightball", question, response)

# Set up the cog
async def setup(bot):
    """Load the Games cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Games(bot))