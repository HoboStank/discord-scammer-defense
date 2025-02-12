from discord.ext import commands
import discord
import logging
from Levenshtein import ratio
import datetime

logger = logging.getLogger('dsd_bot.detection')

class Detection(commands.Cog):
    """Commands and features for detecting potential scammers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.suspicious_patterns = [
            "free nitro",
            "steam gift",
            "giveaway",
            "claim your",
            "discord staff",
            "moderator application"
        ]

    async def compare_usernames(self, name1: str, name2: str) -> float:
        """Compare two usernames for similarity using Levenshtein distance."""
        return ratio(name1.lower(), name2.lower())

    async def check_suspicious_patterns(self, text: str) -> list:
        """Check text for suspicious patterns."""
        found_patterns = []
        text_lower = text.lower()
        for pattern in self.suspicious_patterns:
            if pattern in text_lower:
                found_patterns.append(pattern)
        return found_patterns

    async def check_user(self, member: discord.Member) -> tuple:
        """Check a user against known patterns and staff profiles."""
        suspicious_factors = []
        risk_level = 0

        # Check account age
        account_age = datetime.datetime.utcnow() - member.created_at
        if account_age.days < 7:
            suspicious_factors.append(f"New account ({account_age.days} days old)")
            risk_level += 2
        elif account_age.days < 30:
            suspicious_factors.append(f"Recent account ({account_age.days} days old)")
            risk_level += 1

        # Check for suspicious patterns in username and display name
        patterns = await self.check_suspicious_patterns(member.name)
        if member.nick:
            patterns.extend(await self.check_suspicious_patterns(member.nick))
        
        if patterns:
            suspicious_factors.append(f"Suspicious patterns found: {', '.join(patterns)}")
            risk_level += len(patterns)

        # Compare with server owner's name
        owner_name_similarity = await self.compare_usernames(member.name, member.guild.owner.name)
        if owner_name_similarity > 0.8:
            suspicious_factors.append(f"Username similar to server owner ({owner_name_similarity:.1%} match)")
            risk_level += 3

        return suspicious_factors, risk_level

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle new member joins."""
        factors, risk = await self.check_user(member)
        
        if risk > 0:
            channel = member.guild.system_channel or next((ch for ch in member.guild.text_channels if ch.permissions_for(member.guild.me).send_messages), None)
            if channel:
                embed = discord.Embed(
                    title="⚠️ Potential Scammer Detected",
                    description=f"Member: {member.mention}\nRisk Level: {'🔴' * min(risk, 5)}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Suspicious Factors", value='\n'.join(f"• {f}" for f in factors) or "None")
                embed.set_footer(text=f"User ID: {member.id}")
                await channel.send(embed=embed)

    @commands.command(name='scan')
    @commands.has_permissions(manage_messages=True)
    async def scan_user(self, ctx, member: discord.Member):
        """Manually scan a user for potential scammer indicators."""
        async with ctx.typing():
            factors, risk = await self.check_user(member)
            
            embed = discord.Embed(
                title="🔍 Scan Results",
                description=f"Member: {member.mention}\nRisk Level: {'🔴' * min(risk, 5)}",
                color=discord.Color.blue() if risk == 0 else discord.Color.orange()
            )
            embed.add_field(
                name="Suspicious Factors", 
                value='\n'.join(f"• {f}" for f in factors) or "No suspicious factors found",
                inline=False
            )
            embed.add_field(
                name="Account Info",
                value=f"Created: {discord.utils.format_dt(member.created_at, 'R')}\n"
                      f"Joined: {discord.utils.format_dt(member.joined_at, 'R')}",
                inline=False
            )
            embed.set_footer(text=f"User ID: {member.id}")
            
            await ctx.send(embed=embed)

    @commands.command(name='scampatterns')
    @commands.has_permissions(manage_messages=True)
    async def show_patterns(self, ctx):
        """Show the current list of suspicious patterns."""
        patterns = '\n'.join(f"• {p}" for p in self.suspicious_patterns)
        embed = discord.Embed(
            title="📋 Suspicious Patterns",
            description=f"Current patterns being monitored:\n{patterns}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Detection(bot))
    logger.info('Detection cog loaded')