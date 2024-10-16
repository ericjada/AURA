# Instructions for Adding Future Cogs to the Bot

Adding new cogs to your Discord bot is simple if you follow these steps:

## 1. Create a New Cog File
Each cog is a Python class stored in its own file within the `cogs` folder.

- Navigate to the `cogs` folder in your project directory.
- Create a new `.py` file for the cog, naming it according to its purpose, such as `game.py`, `info.py`, or `admin.py`.

**Examples:**
- `cogs/admin.py` (for admin-related commands)
- `cogs/music.py` (for music-related commands)

## 2. Structure the Cog
Each new cog should follow a similar structure. Here’s a basic template:

```python
import discord
from discord.ext import commands

class NewCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def newcommand(self, ctx):
        """Description of the command."""
        await ctx.send("This is a new command!")

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(NewCog(bot))
```

## Steps for Adding Future Cogs

1. **Define the Cog Class:**  
   Each cog should inherit from `commands.Cog`, and all commands related to that cog should be placed inside this class.

2. **Add the Setup Function:**  
   Each cog must include a `setup(bot)` function that registers the cog with the bot.

3. **No Manual Registration Needed (Auto-load):**  
   Your bot is configured to automatically load all `.py` files from the `cogs` directory (thanks to the loop in `bot.py`). This means you don’t need to manually register each new cog. Once the file is created and saved in the `cogs` folder, the bot will load it automatically the next time it runs.

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
