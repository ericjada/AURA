# dice_duel.py

import random
import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
import asyncio
import re  # For parsing dice roll strings

class DiceDuel(commands.Cog):
    """
    A Discord cog that provides a dice duel game using AURAcoin.
    Users can challenge each other to a duel by betting AURAcoin, and the winner takes the pot.
    Users can specify custom dice rolls in the format XdY+Z.
    """

    def __init__(self, bot):
        """
        Initialize the DiceDuel cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.active_challenges = {}  # Key: (challenger_id, challenged_id), Value: dict with 'amount', 'dice_str', 'channel_id'
        self.pending_rolls = {}  # Key: (challenger_id, challenged_id), Value: dict with 'challenger_roll' and 'challenged_roll'

    def get_auracoin_balance(self, player_id):
        """Get the AURAcoin balance for a player."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT balance FROM auracoin_ledger WHERE player_id = ? ORDER BY transaction_id DESC LIMIT 1",
            (player_id,))
        result = cursor.fetchone()
        return result['balance'] if result else 0

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
            with self.conn:
                self.conn.execute('''
                    INSERT INTO logs (log_type, log_message, timestamp, user_id, username)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('COMMAND_USAGE', f"({username}) executed {command_name}. Input: {input_data}. Output: {output_data}", 
                      timestamp, user_id, username))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

    @discord.app_commands.command(name="challenge", description="Challenge another user to a dice duel with AURAcoin betting.")
    @discord.app_commands.describe(
        opponent="The user you want to challenge.",
        amount="The amount of AURAcoin to bet.",
        dice="The dice roll format (e.g., 2d6+3). Defaults to 'd6' if not specified."
    )
    async def challenge(self, interaction: discord.Interaction, opponent: discord.Member, amount: int, dice: str = "d6"):
        """Allows a user to challenge another user to a dice duel with custom dice."""
        challenger = interaction.user
        challenged = opponent
        challenger_id = challenger.id
        challenged_id = challenged.id
        channel_id = interaction.channel.id if interaction.channel else None

        if not channel_id:
            await interaction.response.send_message("❌ Could not determine the channel for the duel.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        # Check if the amount is valid
        if amount <= 0:
            await interaction.followup.send("❌ You need to bet a positive amount of AURAcoin.", ephemeral=True)
            return

        # Check if challenger has enough balance
        challenger_balance = self.get_auracoin_balance(challenger_id)
        if amount > challenger_balance:
            await interaction.followup.send(f"❌ You have insufficient AURAcoin balance. Your balance is {challenger_balance} AC.", ephemeral=True)
            return

        # Validate the dice string
        try:
            self.parse_dice_roll(dice)
        except ValueError as e:
            await interaction.followup.send(f"❌ Invalid dice format: {str(e)}", ephemeral=True)
            return

        # Check if challenged user is not a bot
        if challenged.bot:
            await interaction.followup.send("❌ You cannot challenge a bot.", ephemeral=True)
            return

        # Check if there is already an active challenge between these users
        if (challenger_id, challenged_id) in self.active_challenges or (challenged_id, challenger_id) in self.active_challenges:
            await interaction.followup.send("❌ There is already an active challenge between you two.", ephemeral=True)
            return

        # Store the challenge with channel_id
        self.active_challenges[(challenger_id, challenged_id)] = {'amount': amount, 'dice_str': dice, 'channel_id': channel_id}

        # Send a message to the challenged user
        try:
            await challenged.send(
                f"🎲 {challenger.mention} has challenged you to a dice duel for **{amount} AC** using dice `{dice}`! "
                f"Type `/accept` to accept or `/decline` to decline."
            )
            await interaction.followup.send(
                f"✅ You have challenged {challenged.mention} to a dice duel for **{amount} AC** using dice `{dice}`."
            )
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Could not send a DM to {challenged.mention}. They might have DMs disabled.", ephemeral=True)

        # Log the command usage
        self.log_command_usage(interaction, "challenge", f"Opponent: {challenged.name}, Amount: {amount}, Dice: {dice}", 
                               f"Challenge sent to {challenged.name}.")

    @discord.app_commands.command(name="accept", description="Accept a dice duel challenge.")
    async def accept(self, interaction: discord.Interaction):
        """Allows a user to accept a dice duel challenge."""
        challenged = interaction.user
        challenged_id = challenged.id

        await interaction.response.defer(thinking=True)

        # Find the challenge
        challenge = None
        for (challenger_id, challenged_id_key), data in self.active_challenges.items():
            if challenged_id_key == challenged_id:
                challenge = (challenger_id, challenged_id_key, data)
                break

        if not challenge:
            await interaction.followup.send("❌ You have no pending challenges.", ephemeral=True)
            return

        challenger_id, challenged_id_key, data = challenge
        amount = data['amount']
        dice_str = data['dice_str']
        channel_id = data['channel_id']
        challenger = await self.bot.fetch_user(challenger_id)

        # Check if challenged user has enough balance
        challenged_balance = self.get_auracoin_balance(challenged_id)
        if amount > challenged_balance:
            await interaction.followup.send(f"❌ You have insufficient AURAcoin balance. Your balance is {challenged_balance} AC.", ephemeral=True)
            # Remove the challenge
            del self.active_challenges[(challenger_id, challenged_id)]
            return

        # Deduct bet amounts from both users
        timestamp = datetime.now().isoformat()
        new_challenger_balance = self.get_auracoin_balance(challenger_id) - amount
        new_challenged_balance = challenged_balance - amount

        with self.conn:
            # Deduct from challenger
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (challenger_id, -amount, new_challenger_balance, 'dice_duel_bet', timestamp))
            # Deduct from challenged
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (challenged_id, -amount, new_challenged_balance, 'dice_duel_bet', timestamp))

        # Initialize pending rolls
        self.pending_rolls[(challenger_id, challenged_id)] = {'challenger_roll': None, 'challenged_roll': None, 'dice_str': dice_str}

        # Inform both users to roll
        try:
            await challenger.send(
                f"🎲 Your duel against {challenged.mention} has been accepted! Please use `/roll {dice_str}` to roll your dice."
            )
        except discord.Forbidden:
            await self.bot.get_channel(channel_id).send(f"{challenger.mention}, I couldn't send you a DM. Please check your privacy settings.")

        try:
            await challenged.send(
                f"🎲 Your duel against {challenger.mention} has been accepted! Please use `/roll {dice_str}` to roll your dice."
            )
        except discord.Forbidden:
            await self.bot.get_channel(channel_id).send(f"{challenged.mention}, I couldn't send you a DM. Please check your privacy settings.")

        await interaction.followup.send(
            f"✅ You have accepted the duel with {challenger.mention} for **{amount} AC** using dice `{dice_str}`. Both of you have been instructed to roll your dice."
        )

        # Log the command usage
        self.log_command_usage(interaction, "accept", "", f"Duel accepted by {challenged.name}. Challenger: {challenger.name}")

    @discord.app_commands.command(name="decline", description="Decline a dice duel challenge.")
    async def decline(self, interaction: discord.Interaction):
        """Allows a user to decline a dice duel challenge."""
        challenged = interaction.user
        challenged_id = challenged.id

        await interaction.response.defer(thinking=True)

        # Find the challenge
        challenge = None
        for (challenger_id, challenged_id_key), data in self.active_challenges.items():
            if challenged_id_key == challenged_id:
                challenge = (challenger_id, challenged_id_key, data)
                break

        if not challenge:
            await interaction.followup.send("❌ You have no pending challenges.", ephemeral=True)
            return

        challenger_id, challenged_id_key, data = challenge
        challenger = await self.bot.fetch_user(challenger_id)

        # Inform both users
        await interaction.followup.send(f"✅ You have declined the dice duel challenge from {challenger.mention}.")
        try:
            await challenger.send(f"❌ {challenged.mention} has declined your dice duel challenge.")
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Could not send a DM to {challenger.mention}. They might have DMs disabled.", ephemeral=True)

        # Remove the challenge
        del self.active_challenges[(challenger_id, challenged_id)]

        # Log the command usage
        self.log_command_usage(interaction, "decline", "", f"Challenge from {challenger.name} declined by {challenged.name}.")

    async def record_roll(self, user_id, result, rolls, dice_str):
        """
        Records a user's roll in an active duel.

        Args:
            user_id: The ID of the user who rolled.
            result: The total result of the roll.
            rolls: A list of individual dice rolls.
            dice_str: The dice string used for rolling.
        """
        # Find if the user is part of any active duel
        for (challenger_id, challenged_id), duel_data in self.pending_rolls.items():
            if user_id == challenger_id or user_id == challenged_id:
                # Check if the dice_str matches
                if duel_data['dice_str'] != dice_str:
                    # Ignore rolls with incorrect dice_str
                    continue

                if user_id == challenger_id:
                    self.pending_rolls[(challenger_id, challenged_id)]['challenger_roll'] = {'result': result, 'rolls': rolls}
                else:
                    self.pending_rolls[(challenger_id, challenged_id)]['challenged_roll'] = {'result': result, 'rolls': rolls}

                # Check if both have rolled
                if (self.pending_rolls[(challenger_id, challenged_id)]['challenger_roll'] and
                    self.pending_rolls[(challenger_id, challenged_id)]['challenged_roll']):
                    # Both have rolled, determine the winner
                    await self.resolve_duel(challenger_id, challenged_id)
                return  # Exit after handling the duel

    async def resolve_duel(self, challenger_id, challenged_id):
        """
        Resolves the duel between two users.

        Args:
            challenger_id: The ID of the challenger.
            challenged_id: The ID of the challenged user.
        """
        duel_data = self.pending_rolls.get((challenger_id, challenged_id))
        if not duel_data:
            return  # Duel data not found

        challenger_roll = duel_data['challenger_roll']['result']
        challenger_rolls = duel_data['challenger_roll']['rolls']
        challenged_roll = duel_data['challenged_roll']['result']
        challenged_rolls = duel_data['challenged_roll']['rolls']
        amount = self.active_challenges.get((challenger_id, challenged_id), {}).get('amount', 0)
        dice_str = self.active_challenges.get((challenger_id, challenged_id), {}).get('dice_str', 'd6')
        channel_id = self.active_challenges.get((challenger_id, challenged_id), {}).get('channel_id', None)

        if not channel_id:
            print(f"No channel_id found for duel between {challenger_id} and {challenged_id}.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            print(f"Channel with ID {channel_id} not found.")
            return

        challenger = await self.bot.fetch_user(challenger_id)
        challenged = await self.bot.fetch_user(challenged_id)

        # Determine the winner
        if challenger_roll > challenged_roll:
            winner = challenger
            loser = challenged
            winner_id = challenger_id
            loser_id = challenged_id
        elif challenged_roll > challenger_roll:
            winner = challenged
            loser = challenger
            winner_id = challenged_id
            loser_id = challenger_id
        else:
            # It's a tie; refund bets
            timestamp = datetime.now().isoformat()
            with self.conn:
                # Refund challenger
                self.conn.execute('''
                    INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (challenger_id, amount, self.get_auracoin_balance(challenger_id) + amount, 'dice_duel_refund', timestamp))
                # Refund challenged
                self.conn.execute('''
                    INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (challenged_id, amount, self.get_auracoin_balance(challenged_id) + amount, 'dice_duel_refund', timestamp))

            # Inform users of the tie
            try:
                await challenger.send(
                    f"🎲 Your dice duel with {challenged.mention} resulted in a tie. Bets have been refunded.\n"
                    f"📊 Your roll: {challenger_roll} ({', '.join(map(str, challenger_rolls))})\n"
                    f"📊 {challenged.mention}'s roll: {challenged_roll} ({', '.join(map(str, challenged_rolls))})"
                )
            except discord.Forbidden:
                pass
            try:
                await challenged.send(
                    f"🎲 Your dice duel with {challenger.mention} resulted in a tie. Bets have been refunded.\n"
                    f"📊 Your roll: {challenged_roll} ({', '.join(map(str, challenged_rolls))})\n"
                    f"📊 {challenger.mention}'s roll: {challenger_roll} ({', '.join(map(str, challenger_rolls))})"
                )
            except discord.Forbidden:
                pass

            # Log the duel result
            self.log_duel_result(
                challenger_id, challenged_id, amount, None, None, challenger_roll, challenged_roll,
                ', '.join(map(str, challenger_rolls)), ', '.join(map(str, challenged_rolls)), 
                dice_str
            )

            # Inform in the channel if possible
            if channel:
                await channel.send(
                    f"⚖️ The duel between {challenger.mention} and {challenged.mention} ended in a tie. Bets have been refunded."
                )

            # Clean up
            del self.pending_rolls[(challenger_id, challenged_id)]
            del self.active_challenges[(challenger_id, challenged_id)]
            return

        # Update winner's balance
        total_pot = amount * 2
        new_winner_balance = self.get_auracoin_balance(winner_id) + total_pot

        timestamp = datetime.now().isoformat()
        with self.conn:
            self.conn.execute('''
                INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (winner_id, total_pot, new_winner_balance, 'dice_duel_win', timestamp))

        # Inform users of the result
        try:
            await winner.send(
                f"🎉 Congratulations! You won the dice duel against {loser.mention} and received **{total_pot} AC**.\n"
                f"📊 Your roll: {challenger_roll if winner_id == challenger_id else challenged_roll} "
                f"({', '.join(map(str, challenger_rolls if winner_id == challenger_id else challenged_rolls))})\n"
                f"📊 {loser.mention}'s roll: {challenged_roll if winner_id == challenger_id else challenger_roll} "
                f"({', '.join(map(str, challenged_rolls if winner_id == challenger_id else challenger_rolls))})"
            )
        except discord.Forbidden:
            pass
        try:
            await loser.send(
                f"😞 Unfortunately, you lost the dice duel against {winner.mention} and lost **{amount} AC**.\n"
                f"📊 Your roll: {challenged_roll if loser.id == challenged_id else challenger_roll} "
                f"({', '.join(map(str, challenged_rolls if loser.id == challenged_id else challenger_rolls))})\n"
                f"📊 {winner.mention}'s roll: {challenger_roll if loser.id == challenged_id else challenged_roll} "
                f"({', '.join(map(str, challenger_rolls if loser.id == challenged_id else challenged_rolls))})"
            )
        except discord.Forbidden:
            pass

        # Log the duel result
        self.log_duel_result(
            challenger_id, challenged_id, amount, winner_id, loser_id, challenger_roll, challenged_roll,
            ', '.join(map(str, challenger_rolls)), ', '.join(map(str, challenged_rolls)), 
            dice_str
        )

        # Inform in the channel if possible
        if channel:
            await channel.send(
                f"🏆 {winner.mention} has won the duel against {loser.mention} and received **{total_pot} AC**!"
            )

        # Clean up
        del self.pending_rolls[(challenger_id, challenged_id)]
        del self.active_challenges[(challenger_id, challenged_id)]

    def parse_dice_roll(self, dice_str: str):
        """
        Parses a dice roll string in the form of XdY+Z and calculates the result.

        Args:
            dice_str: The dice roll string to parse (e.g., 2d6+4, d20).

        Returns:
            Tuple containing:
            - result: The total sum of the dice roll with the modifier.
            - rolls: A list of individual dice rolls.
            - modifier: The numeric modifier applied to the result.
        """
        # Regex to match patterns like '2d6+4', 'd20', '4d8', or 'd12-2'
        dice_pattern = r"(?:(\d+)d)?(\d+)([+-]\d+)?"
        match = re.fullmatch(dice_pattern, dice_str.replace(" ", ""))  # Remove spaces before matching

        if not match:
            raise ValueError("Invalid dice format. Please use a format like 2d6+4 or d20.")

        num_dice = int(match.group(1)) if match.group(1) else 1  # Number of dice to roll, defaults to 1
        dice_size = int(match.group(2))  # Size of dice (e.g., 6 for d6, 20 for d20)
        modifier = int(match.group(3)) if match.group(3) else 0  # Modifier, defaults to 0 if not present

        if num_dice < 1 or dice_size < 1:
            raise ValueError("Number of dice and size must be greater than 0.")

        # Roll the dice
        rolls = [random.randint(1, dice_size) for _ in range(num_dice)]
        result = sum(rolls) + modifier

        return result, rolls, modifier

    def log_duel_result(self, challenger_id, challenged_id, amount, winner_id, loser_id, 
                        challenger_result, challenged_result, challenger_rolls, challenged_rolls, dice_str):
        """Logs the result of a dice duel into the dice_duel_results table."""

        timestamp = datetime.now().isoformat()

        with self.conn:
            self.conn.execute('''
                INSERT INTO dice_duel_results (
                    challenger_id, challenged_id, amount, winner_id, loser_id, 
                    challenger_result, challenged_result,
                    challenger_rolls, challenged_rolls, dice_str, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                challenger_id, challenged_id, amount, winner_id, loser_id, 
                challenger_result, challenged_result,
                challenger_rolls, challenged_rolls, dice_str, timestamp
            ))


    async def handle_roll(self, user_id, result, rolls, dice_str):
        """
        Handles a roll made by a user in a duel.

        Args:
            user_id: The ID of the user who rolled.
            result: The total result of the roll.
            rolls: A list of individual dice rolls.
            dice_str: The dice string used for rolling.
        """
        await self.record_roll(user_id, result, rolls, dice_str)

    async def record_roll(self, user_id, result, rolls, dice_str):
        """
        Records a user's roll in an active duel.

        Args:
            user_id: The ID of the user who rolled.
            result: The total result of the roll.
            rolls: A list of individual dice rolls.
            dice_str: The dice string used for rolling.
        """
        # Find if the user is part of any active duel
        for (challenger_id, challenged_id), duel_data in self.pending_rolls.items():
            if user_id == challenger_id or user_id == challenged_id:
                # Check if the dice_str matches
                if duel_data['dice_str'] != dice_str:
                    # Ignore rolls with incorrect dice_str
                    continue

                if user_id == challenger_id:
                    self.pending_rolls[(challenger_id, challenged_id)]['challenger_roll'] = {'result': result, 'rolls': rolls}
                else:
                    self.pending_rolls[(challenger_id, challenged_id)]['challenged_roll'] = {'result': result, 'rolls': rolls}

                # Check if both have rolled
                if (self.pending_rolls[(challenger_id, challenged_id)]['challenger_roll'] and
                    self.pending_rolls[(challenger_id, challenged_id)]['challenged_roll']):
                    # Both have rolled, determine the winner
                    await self.resolve_duel(challenger_id, challenged_id)
                return  # Exit after handling the duel

# Set up the cog
async def setup(bot):
    """Load the DiceDuel cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(DiceDuel(bot))
