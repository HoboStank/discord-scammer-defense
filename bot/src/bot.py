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
            command_prefix='!dsd ',  # Commands will start with !dsd
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

    async def setup_hook(self):
        """Initialize bot settings and load extensions."""
        self.color = discord.Color.blue()
        await super().setup_hook()

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required argument. Use `!dsd help` for command usage.")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send("❌ An error occurred while executing the command.")

    async def on_member_join(self, member):
        """Event that fires when a new member joins."""
        logger.info(f'New member joined: {member.name}#{member.discriminator}')
        # TODO: Implement scammer detection logic

    async def on_member_update(self, before, after):
        """Event that fires when a member updates their profile."""
        if before.avatar != after.avatar or before.name != after.name:
            logger.info(f'Member updated: {after.name}#{after.discriminator}')
            # TODO: Implement profile change detection

async def main():
    """Main function to start the bot."""
    async with DSDBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())