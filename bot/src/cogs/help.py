from discord.ext import commands
import discord
import logging

logger = logging.getLogger('dsd_bot.help')

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            command = self.bot.get_command(command_name)
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

        embed.set_footer(text="Use '!dsd help <command>' for more details about a command")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
    logger.info('Help cog loaded')