from discord.ext import commands
import discord
import logging

logger = logging.getLogger('dsd_bot.moderation')

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a user."""
        await ctx.send(f'Warning {member.mention}' + (f' for: {reason}' if reason else ''))

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban_user(self, ctx, member: discord.Member, *, reason: str = None):
        """Ban a user."""
        await ctx.send(f'Banning {member.mention}' + (f' for: {reason}' if reason else ''))
        # TODO: Implement actual ban logic

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    logger.info('Moderation cog loaded')