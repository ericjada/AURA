# Instructions for Adding Future Cogs to the Bot

Adding new cogs to your Discord bot is simple if you follow these steps:

## 1. Create a New Cog File
Each cog is a Python class stored in its own file within the `cogs` folder.

- Navigate to the `cogs` folder in your project directory.
- Create a new `.py` file for the cog, naming it according to its purpose.
- Use lowercase names and underscores for file names (e.g., `role_manager.py`, `message_handler.py`)

**Examples:**
- `cogs/ai_chat.py` (for AI chat functionality)
- `cogs/moderation.py` (for moderation commands)
- `cogs/settings.py` (for bot configuration commands)

## 2. Structure the Cog
Each new cog should follow this structure:

```python
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from utils.config_loader import Config  # Import project-specific utilities

class NewCog(commands.Cog):
    """Brief description of what this cog does."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()  # Initialize config for settings

    @commands.Cog.listener()
    async def on_ready(self):
        """Optional: Set up any necessary initialization."""
        print(f"{self.__class__.__name__} cog has been loaded")

    @app_commands.command()
    @app_commands.describe(parameter="Description of the parameter")
    async def slash_command(self, interaction: discord.Interaction, parameter: Optional[str] = None):
        """Description of the command that appears in Discord."""
        # Check if the feature is enabled for this guild
        if not self.config.is_feature_enabled(interaction.guild_id, "feature_name"):
            await interaction.response.send_message("This feature is not enabled in this server.", ephemeral=True)
            return
            
        await interaction.response.send_message("This is a slash command!")

async def setup(bot):
    await bot.add_cog(NewCog(bot))
```

## Steps for Adding Future Cogs

1. **Define the Cog Class:**  
   - Use clear, descriptive class names
   - Include docstrings for the class and all commands
   - Group related commands together
   - Consider using command groups for related commands

2. **Choose Command Types:**
   - Use `@app_commands.command()` for slash commands (preferred for new commands)
   - Use `@commands.command()` for traditional prefix commands
   - Consider hybrid commands with `@commands.hybrid_command()` when needed

3. **Error Handling:**
   ```python
   @commands.Cog.listener()
   async def on_command_error(self, ctx, error):
       if isinstance(error, commands.CommandOnCooldown):
           await ctx.send(f"Please wait {error.retry_after:.2f}s before using this command again.")
       elif isinstance(error, commands.MissingPermissions):
           await ctx.send("You don't have permission to use this command.")
   ```

## Using `@commands.cooldown`

The `@commands.cooldown` decorator in Discord.py limits how often a command can be invoked by users, helping to prevent spam and ensuring a smoother experience for everyone in the server.

### Syntax

```python
@commands.cooldown(rate, per, bucket)
```

- **rate:** The number of times a command can be used within the specified time frame.
- **per:** The time frame (in seconds) during which the rate limit applies.
- **bucket:** The type of bucket that defines how the cooldown is applied. Common options include:
  - `commands.BucketType.default`: Applies to all users globally.
  - `commands.BucketType.user`: Applies separately to each user.
  - `commands.BucketType.guild`: Applies separately to each server.
  - `commands.BucketType.channel`: Applies separately to each channel.

### Example

Here’s how to implement a cooldown on a command:

```python
@commands.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def ping(ctx):
    """Responds with 'Pong!' when the user sends !ping."""
    await ctx.send('Pong!')
```

In this example, the `ping` command can be used once every 10 seconds by each user. If a user attempts to use the command again within that timeframe, they will receive an error message indicating that the command is on cooldown.

## Error Handling

If a user tries to use a command while it is on cooldown, a `commands.CommandOnCooldown` exception will be raised. You can handle this error to provide a custom response:

```python
@ping.error
async def ping_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"You are on cooldown! Try again in {round(error.retry_after)} seconds.")
```

## Conclusion

Using `@commands.cooldown` is an effective way to manage command usage and prevent spam, enhancing the overall user experience in your Discord bot.
