# fishing.py

import random 
import discord
from discord.ext import commands
from datetime import datetime
import sqlite3
from discord.app_commands import checks
from discord import ui

class Fishing(commands.Cog):
    """
    A Discord cog that allows users to fish for virtual items using AURAcoin.
    Users can spend AURAcoin to buy bait, go fishing, catch fish of varying value, and sell them for AURAcoin.
    """

    def __init__(self, bot):
        """
        Initialize the Fishing cog.

        Args:
            bot: An instance of the Discord bot.
        """
        self.bot = bot
        self.conn = sqlite3.connect('./group_memories/aura_memory.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dictionary-like cursor
        self.cursor = self.conn.cursor()

        # Ensure the fishing_inventory table exists
        self.create_tables()

    def create_tables(self):
        """Creates necessary tables if they do not exist."""
        with self.conn:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_inventory (
                    user_id INTEGER NOT NULL,
                    bait INTEGER DEFAULT 0,
                    fish_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, fish_name)
                )
            ''')

    @discord.app_commands.command(name="buy_bait", description="Buy bait to go fishing.")
    @discord.app_commands.describe(quantity="The number of bait to purchase.")
    async def buy_bait(self, interaction: discord.Interaction, quantity: int):
        """Allows a user to buy bait using AURAcoin."""
        if not isinstance(quantity, int) or quantity <= 0:
            await interaction.response.send_message("Please enter a valid positive number of bait to purchase.", ephemeral=True)
            return
        user = interaction.user
        user_id = user.id
        bait_price = 5  # Set bait price to 5 AC per unit
        total_cost = bait_price * quantity

        await interaction.response.defer(thinking=True)

        try:
            # Check if the user has enough balance
            balance = self.get_auracoin_balance(user_id)
            if quantity <= 0:
                await interaction.followup.send("You need to buy at least one bait.")
                return
            if total_cost > balance:
                await interaction.followup.send(f"You have insufficient AURAcoin balance. Your balance is {balance} AC.")
                return

            # Deduct the cost from the user's balance
            new_balance = balance - total_cost
            timestamp = datetime.now().isoformat()
            with self.conn:
                self.conn.execute('''
                    INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, -total_cost, new_balance, 'bait_purchase', timestamp))

                # Update the user's bait count in the fishing_inventory table
                self.cursor.execute('''
                    SELECT bait FROM fishing_inventory WHERE user_id = ? AND fish_name = 'Bait'
                ''', (user_id,))
                result = self.cursor.fetchone()
                if result:
                    # User already has bait entry, update it
                    self.cursor.execute('''
                        UPDATE fishing_inventory SET bait = bait + ? WHERE user_id = ? AND fish_name = 'Bait'
                    ''', (quantity, user_id))
                else:
                    # User does not have bait entry, insert new
                    self.cursor.execute('''
                        INSERT INTO fishing_inventory (user_id, bait, fish_name, quantity) VALUES (?, ?, ?, ?)
                    ''', (user_id, quantity, 'Bait', 0))

            await interaction.followup.send(f"You have purchased {quantity} bait(s). Happy fishing!")

            # Log the command usage
            self.log_command_usage(interaction, "buy_bait", f"Quantity: {quantity}", f"Bait purchased: {quantity}")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /buy_bait command: {str(e)}")

    @discord.app_commands.command(name="fish", description="Go fishing to catch fish.")
    @discord.app_commands.checks.cooldown(1, 30)  # One use every 30 seconds
    async def fish(self, interaction: discord.Interaction):
        """Allows a user to go fishing using their bait."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        try:
            # Check if the user has bait
            self.cursor.execute('''
                SELECT bait FROM fishing_inventory WHERE user_id = ? AND fish_name = 'Bait'
            ''', (user_id,))
            result = self.cursor.fetchone()
            bait_count = result['bait'] if result else 0

            if bait_count <= 0:
                await interaction.followup.send("You have no bait. Buy some using `/buy_bait`.")
                return

            # Deduct one bait
            with self.conn:
                self.conn.execute('''
                    UPDATE fishing_inventory SET bait = bait - 1 WHERE user_id = ? AND fish_name = 'Bait'
                ''', (user_id,))

            # Simulate fishing
            catch = self.simulate_fishing()

            # Add the catch to the user's inventory
            with self.conn:
                # Check if the user already has this fish
                self.cursor.execute('''
                    SELECT quantity FROM fishing_inventory WHERE user_id = ? AND fish_name = ?
                ''', (user_id, catch['name']))
                fish_result = self.cursor.fetchone()
                if fish_result:
                    # Update the quantity
                    self.cursor.execute('''
                        UPDATE fishing_inventory SET quantity = quantity + 1 WHERE user_id = ? AND fish_name = ?
                    ''', (user_id, catch['name']))
                else:
                    # Insert a new fish entry
                    self.cursor.execute('''
                        INSERT INTO fishing_inventory (user_id, fish_name, quantity) VALUES (?, ?, ?)
                    ''', (user_id, catch['name'], 1))

            await interaction.followup.send(f"You cast your line and caught a **{catch['name']}** worth {catch['value']} AC!")

            # Log the command usage
            self.log_command_usage(interaction, "fish", "", f"Caught: {catch['name']}")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /fish command: {str(e)}")

    @fish.error
    async def fish_error(self, interaction: discord.Interaction, error):
        """Handle errors for the fish command."""
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            seconds = int(error.retry_after)
            await interaction.response.send_message(
                f"You need to wait {seconds} seconds before fishing again!", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}", 
                ephemeral=True
            )

    def simulate_fishing(self):
        """Simulates fishing and returns a caught fish."""
        # Define fish types with their rarity and value
        fish_types = [
            {'name': 'Common Carp', 'rarity': 'Common', 'value': 10},
            {'name': 'Bass', 'rarity': 'Common', 'value': 15},
            {'name': 'Salmon', 'rarity': 'Uncommon', 'value': 25},
            {'name': 'Tuna', 'rarity': 'Uncommon', 'value': 30},
            {'name': 'Rainbow Trout', 'rarity': 'Rare', 'value': 50},
            {'name': 'Swordfish', 'rarity': 'Rare', 'value': 75},
            {'name': 'Golden Koi', 'rarity': 'Epic', 'value': 150},
            {'name': 'Mythic Leviathan', 'rarity': 'Legendary', 'value': 500}
        ]

        # Assign probabilities based on rarity
        catch_probabilities = {
            'Common': 0.5,
            'Uncommon': 0.3,
            'Rare': 0.15,
            'Epic': 0.049,
            'Legendary': 0.001
        }

        # Create a weighted list of fish types
        weighted_fish = []
        for fish in fish_types:
            weight = catch_probabilities[fish['rarity']] * 1000  # Scale up for better weighting
            weighted_fish.extend([fish] * int(weight))

        # Randomly select a fish
        caught_fish = random.choice(weighted_fish)
        return caught_fish

    @discord.app_commands.command(name="inventory", description="Check your fishing inventory.")
    async def inventory(self, interaction: discord.Interaction):
        """Displays the user's fishing inventory."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        try:
            # Retrieve the user's fish inventory
            self.cursor.execute('''
                SELECT fish_name, quantity FROM fishing_inventory WHERE user_id = ? AND fish_name != 'Bait'
            ''', (user_id,))
            fish_inventory = self.cursor.fetchall()

            # Display the inventory
            if fish_inventory:
                inventory_message = "**Your Fishing Inventory:**\n"
                total_value = 0
                for row in fish_inventory:
                    fish_name = row['fish_name']
                    quantity = row['quantity']
                    value = self.get_fish_value(fish_name)
                    total_value += value * quantity
                    inventory_message += f"- {fish_name}: {quantity} (Worth: {value} AC each)\n"
                inventory_message += f"\nTotal Value: {total_value} AC"
                await interaction.followup.send(inventory_message)
            else:
                await interaction.followup.send("Your fishing inventory is empty.")

            # Log the command usage
            self.log_command_usage(interaction, "inventory", "", "Displayed fishing inventory.")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /inventory command: {str(e)}")

    @discord.app_commands.command(name="sell_fish", description="Sell your caught fish for AURAcoin.")
    async def sell_fish(self, interaction: discord.Interaction):
        """Allows a user to sell all their fish for AURAcoin."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        try:
            # Retrieve the user's fish inventory
            self.cursor.execute('''
                SELECT fish_name, quantity FROM fishing_inventory WHERE user_id = ? AND fish_name != 'Bait'
            ''', (user_id,))
            fish_inventory = self.cursor.fetchall()

            if not fish_inventory:
                await interaction.followup.send("You have no fish to sell.")
                return

            # Calculate total value first
            total_earnings = sum(self.get_fish_value(row['fish_name']) * row['quantity'] for row in fish_inventory)
            
            # Create confirmation view
            class ConfirmSale(ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.value = None

                @ui.button(label="Confirm Sale", style=discord.ButtonStyle.green)
                async def confirm(self, interaction: discord.Interaction, button: ui.Button):
                    self.value = True
                    self.stop()

                @ui.button(label="Cancel", style=discord.ButtonStyle.grey)
                async def cancel(self, interaction: discord.Interaction, button: ui.Button):
                    self.value = False
                    self.stop()

            view = ConfirmSale()
            await interaction.followup.send(
                f"Are you sure you want to sell all your fish for {total_earnings} AC?",
                view=view
            )

            await view.wait()
            if view.value:
                # Update the user's balance
                balance = self.get_auracoin_balance(user_id)
                new_balance = balance + total_earnings
                timestamp = datetime.now().isoformat()
                with self.conn:
                    self.conn.execute('''
                        INSERT INTO auracoin_ledger (player_id, change_amount, balance, transaction_type, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, total_earnings, new_balance, 'fish_sale', timestamp))

                    # Remove the fish from the inventory
                    self.conn.execute('''
                        DELETE FROM fishing_inventory WHERE user_id = ? AND fish_name != 'Bait'
                    ''', (user_id,))

                await interaction.followup.send(f"You sold all your fish for {total_earnings} AC! Your new balance is {new_balance} AC.")
            else:
                await interaction.followup.send("Fish sale cancelled.")

            # Log the command usage
            self.log_command_usage(interaction, "sell_fish", "", f"Sold fish for {total_earnings} AC")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /sell_fish command: {str(e)}")

    def get_fish_value(self, fish_name):
        """Returns the value of a fish based on its name."""
        fish_values = {
            'Common Carp': 10,
            'Bass': 15,
            'Salmon': 25,
            'Tuna': 30,
            'Rainbow Trout': 50,
            'Swordfish': 75,
            'Golden Koi': 150,
            'Mythic Leviathan': 500
        }
        return fish_values.get(fish_name, 0)

    @discord.app_commands.command(name="bait", description="Check how much bait you have.")
    async def bait(self, interaction: discord.Interaction):
        """Displays the amount of bait the user has."""
        user = interaction.user
        user_id = user.id

        await interaction.response.defer(thinking=True)

        try:
            # Retrieve the user's bait count
            self.cursor.execute('''
                SELECT bait FROM fishing_inventory WHERE user_id = ? AND fish_name = 'Bait'
            ''', (user_id,))
            result = self.cursor.fetchone()
            bait_count = result['bait'] if result else 0

            await interaction.followup.send(f"You have {bait_count} bait(s).")

            # Log the command usage
            self.log_command_usage(interaction, "bait", "", f"Bait count: {bait_count}")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /bait command: {str(e)}")

    @discord.app_commands.command(name="fishing_leaderboard", description="Shows the top fishers based on total earnings.")
    async def fishing_leaderboard(self, interaction: discord.Interaction):
        """Displays the leaderboard for fishing based on total earnings from selling fish."""
        await interaction.response.defer(thinking=True)

        try:
            cursor = self.conn.cursor()

            # Query top 5 players by total fish sale earnings
            cursor.execute('''
                SELECT player_id, SUM(change_amount) as total_earnings
                FROM auracoin_ledger
                WHERE transaction_type = 'fish_sale'
                GROUP BY player_id
                ORDER BY total_earnings DESC
                LIMIT 5
            ''')
            top_fishers = cursor.fetchall()

            # Format the output
            if top_fishers:
                leaderboard_message = "**Top 5 Fishers:**\n"
                for i, row in enumerate(top_fishers, start=1):
                    player_id = row['player_id']
                    total_earnings = row['total_earnings']
                    try:
                        user = await self.bot.fetch_user(player_id)
                        username = user.name
                    except discord.NotFound:
                        username = f"User ID {player_id}"
                    leaderboard_message += f"{i}. {username} - {total_earnings} AC earned from fishing\n"
            else:
                leaderboard_message = "No fishing data available yet."

            await interaction.followup.send(leaderboard_message)

            # Log the command usage
            self.log_command_usage(interaction, "fishing_leaderboard", "", "Displayed fishing leaderboard.")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            print(f"Error in /fishing_leaderboard command: {str(e)}")

    def get_auracoin_balance(self, player_id):
        """Get the AURAcoin balance for a player."""
        self.cursor.execute("SELECT balance FROM auracoin_ledger WHERE player_id = ? ORDER BY transaction_id DESC LIMIT 1", (player_id,))
        result = self.cursor.fetchone()
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
                ''', ('COMMAND_USAGE', f"({username}) executed {command_name}.", timestamp, user_id, username))
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error in log_command_usage: {e}")
            # Not critical, so we don't raise an exception

# Set up the cog
async def setup(bot):
    """Load the Fishing cog into the bot.

    Args:
        bot: An instance of the Discord bot.
    """
    await bot.add_cog(Fishing(bot))
