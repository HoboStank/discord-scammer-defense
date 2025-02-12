import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dsd_bot')

# Load environment variables
load_dotenv('config/.env')

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # For reading message content
intents.members = True         # For tracking member joins/updates
intents.presences = True       # For tracking user status changes

class DSDBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!dsd ',  # Command prefix with space
            case_insensitive=True,  # Make commands case-insensitive
            intents=intents,
            description='Discord Scammer Defense Bot'
        )
        self.initial_extensions = [
            'cogs.detection',    # Scammer detection logic
            'cogs.moderation',   # Moderation commands
            'cogs.appeals',      # Appeal system
            'cogs.admin'         # Admin commands
        ]

    async def setup_hook(self):
        """Setup hook that runs when the bot starts."""
        self.color = discord.Color.blue()
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f'Loaded extension: {ext}')
            except Exception as e:
                logger.error(f'Failed to load extension {ext}: {e}')

    async def on_ready(self):
        """Event that fires when the bot is ready."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name='for scammers | !dsd help'
            )
        )

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required argument. Use `!dsd help` for command usage.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Command not found. Use `!dsd help` to see available commands.")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send("❌ An error occurred while executing the command.")

    async def get_prefix(self, message):
        """Get the prefix for the bot."""
        return '!dsd '

async def main():
    """Main function to start the bot."""
    async with DSDBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())