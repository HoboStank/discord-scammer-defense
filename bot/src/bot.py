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
            command_prefix=['!dsd ', '!dsd', 'dsd '],  # Multiple prefix options
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

    @commands.command(name='help')
    async def help_command(self, ctx, command_name: str = None):
        """Show help for bot commands."""
        embed = discord.Embed(
            title="DSD Bot Help",
            description="Available commands:",
            color=discord.Color.blue()
        )

        if command_name:
            # Show help for specific command
            command = self.get_command(command_name)
            if command:
                embed.add_field(
                    name=f"!dsd {command.name}",
                    value=command.help or "No description available",
                    inline=False
                )
            else:
                await ctx.send(f"Command '{command_name}' not found.")
                return
        else:
            # Show all commands
            commands_list = [
                ("scan @user", "Scan a user for suspicious activity"),
                ("scampatterns", "Show the list of suspicious patterns"),
                ("help [command]", "Show this help message or get help for a specific command")
            ]
            
            for cmd, desc in commands_list:
                embed.add_field(
                    name=f"!dsd {cmd}",
                    value=desc,
                    inline=False
                )

        embed.set_footer(text="Use !dsd help <command> for more details about a command")
        await ctx.send(embed=embed)

async def main():
    """Main function to start the bot."""
    async with DSDBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())