from discord.ext import commands
import discord
import logging
from Levenshtein import ratio
import datetime
import aiohttp
from io import BytesIO
from PIL import Image
import imagehash
import re

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

    async def download_avatar(self, url: str) -> Image.Image:
        """Download and return a user's avatar."""
        if not url:
            return None
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as response:
                if response.status == 200:
                    data = await response.read()
                    return Image.open(BytesIO(data))
        return None

    async def compare_images(self, img1: Image.Image, img2: Image.Image) -> float:
        """Compare two images using perceptual hashing."""
        if not img1 or not img2:
            return 0.0
        
        # Convert images to same size and mode for comparison
        size = (128, 128)
        img1 = img1.resize(size).convert('RGB')
        img2 = img2.resize(size).convert('RGB')
        
        # Calculate perceptual hashes
        hash1 = imagehash.average_hash(img1)
        hash2 = imagehash.average_hash(img2)
        
        # Calculate similarity (0 to 1, where 1 is identical)
        max_diff = len(hash1.hash) * len(hash1.hash)  # Maximum possible difference
        actual_diff = hash1 - hash2
        return 1 - (actual_diff / max_diff)

    async def compare_usernames(self, name1: str, name2: str) -> float:
        """Compare two usernames for similarity."""
        # Clean and normalize usernames
        clean1 = re.sub(r'[^a-zA-Z0-9]', '', name1.lower())
        clean2 = re.sub(r'[^a-zA-Z0-9]', '', name2.lower())
        
        # Return 0 if one of the names is empty after cleaning
        if not clean1 or not clean2:
            return 0.0
            
        # Calculate basic similarity
        basic_ratio = ratio(clean1, clean2)
        
        # Check for substring relationship
        if clean1 in clean2 or clean2 in clean1:
            return max(basic_ratio, 0.8)  # At least 80% match if one is substring of other
            
        return basic_ratio

    async def compare_text(self, text1: str, text2: str) -> float:
        """Compare two text strings for similarity."""
        if not text1 or not text2:
            return 0.0
        return ratio(text1.lower(), text2.lower())

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

        # Skip checks if user is the server owner
        if member.id == member.guild.owner_id:
            return [], 0

        # Check account age
        account_age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
        if account_age.days < 7:
            suspicious_factors.append(f"New account ({account_age.days} days old)")
            risk_level += 2
        elif account_age.days < 30:
            suspicious_factors.append(f"Recent account ({account_age.days} days old)")
            risk_level += 1

        # Compare with server owner
        owner = member.guild.owner
        
        # Username comparison
        owner_name_similarity = await self.compare_usernames(member.name, owner.name)
        if owner_name_similarity > 0.7:
            suspicious_factors.append(f"Username similar to server owner ({owner_name_similarity:.1%} match)")
            risk_level += 3

        # Avatar comparison
        member_avatar = await self.download_avatar(member.display_avatar.url)
        owner_avatar = await self.download_avatar(owner.display_avatar.url)
        if member_avatar and owner_avatar:
            avatar_similarity = await self.compare_images(member_avatar, owner_avatar)
            if avatar_similarity > 0.8:
                suspicious_factors.append(f"Avatar similar to server owner ({avatar_similarity:.1%} match)")
                risk_level += 3

        # Bio/Status comparison
        member_activities = [str(activity) for activity in member.activities if activity.type == discord.ActivityType.custom]
        owner_activities = [str(activity) for activity in owner.activities if activity.type == discord.ActivityType.custom]
        
        if member_activities and owner_activities:
            status_similarity = await self.compare_text(member_activities[0], owner_activities[0])
            if status_similarity > 0.6:
                suspicious_factors.append(f"Status message similar to server owner ({status_similarity:.1%} match)")
                risk_level += 2

        # Check for suspicious patterns in all text fields
        all_text = [member.name]
        if member.nick:
            all_text.append(member.nick)
        all_text.extend(member_activities)
        
        for text in all_text:
            patterns = await self.check_suspicious_patterns(text)
            if patterns:
                suspicious_factors.append(f"Suspicious patterns in {text}: {', '.join(patterns)}")
                risk_level += len(patterns)

        # Additional risk for combination of factors
        if len(suspicious_factors) >= 3:
            risk_level += 2  # Extra risk for multiple suspicious factors

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