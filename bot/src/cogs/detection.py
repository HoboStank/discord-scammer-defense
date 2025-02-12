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
import unicodedata

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

    async def compare_images(self, img1: Image.Image, img2: Image.Image) -> tuple[float, list[str]]:
        """Compare two images using multiple methods."""
        if not img1 or not img2:
            return 0.0, []

        reasons = []
        max_similarity = 0.0
        
        # Convert images to same size and mode for comparison
        size = (128, 128)
        img1_resized = img1.resize(size).convert('RGB')
        img2_resized = img2.resize(size).convert('RGB')
        
        # 1. Average Hash (overall similarity)
        hash1 = imagehash.average_hash(img1_resized)
        hash2 = imagehash.average_hash(img2_resized)
        avg_similarity = 1 - (hash1 - hash2) / (len(hash1.hash) * len(hash1.hash))
        
        # 2. Perceptual Hash (resistant to minor modifications)
        phash1 = imagehash.phash(img1_resized)
        phash2 = imagehash.phash(img2_resized)
        phash_similarity = 1 - (phash1 - phash2) / (len(phash1.hash) * len(phash1.hash))
        
        # 3. Difference Hash (edge detection based)
        dhash1 = imagehash.dhash(img1_resized)
        dhash2 = imagehash.dhash(img2_resized)
        dhash_similarity = 1 - (dhash1 - dhash2) / (len(dhash1.hash) * len(dhash1.hash))
        
        # 4. Color analysis
        def get_dominant_colors(img):
            img = img.resize((50, 50))  # Reduce size for faster processing
            colors = img.getcolors(2500)  # Get all colors
            if colors:
                return sorted(colors, reverse=True)[:3]  # Top 3 colors
            return []
            
        colors1 = get_dominant_colors(img1_resized)
        colors2 = get_dominant_colors(img2_resized)
        
        # Compare color patterns
        color_similarity = 0
        if colors1 and colors2:
            matches = sum(1 for c1 in colors1 for c2 in colors2 
                        if abs(c1[1][0] - c2[1][0]) < 30 and  # R
                           abs(c1[1][1] - c2[1][1]) < 30 and  # G
                           abs(c1[1][2] - c2[1][2]) < 30)     # B
            color_similarity = matches / max(len(colors1), len(colors2))

        # Analyze results
        if avg_similarity > 0.8:
            reasons.append("very similar overall appearance")
            max_similarity = max(max_similarity, avg_similarity)
            
        if phash_similarity > 0.8:
            reasons.append("similar after minor modifications")
            max_similarity = max(max_similarity, phash_similarity)
            
        if dhash_similarity > 0.8:
            reasons.append("similar edge patterns")
            max_similarity = max(max_similarity, dhash_similarity)
            
        if color_similarity > 0.7:
            reasons.append("similar color scheme")
            max_similarity = max(max_similarity, color_similarity)

        return max_similarity, reasons

    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters to their closest ASCII representation."""
        # Common Unicode tricks used by scammers
        unicode_map = {
            'а': 'a',  # Cyrillic
            'е': 'e',  # Cyrillic
            'і': 'i',  # Cyrillic
            'о': 'o',  # Cyrillic
            'р': 'p',  # Cyrillic
            'с': 'c',  # Cyrillic
            'у': 'y',  # Cyrillic
            'ѕ': 's',  # Cyrillic
            '𝐚': 'a',  # Mathematical
            '𝐛': 'b',  # Mathematical
            '𝐨': 'o',  # Mathematical
            '𝓪': 'a',  # Script
            '𝓫': 'b',  # Script
            '𝓸': 'o',  # Script
            '𝔞': 'a',  # Fraktur
            '𝔟': 'b',  # Fraktur
            '𝔬': 'o',  # Fraktur
            # Add more as needed
        }
        
        # Replace Unicode characters
        normalized = text.lower()
        for unicode_char, ascii_char in unicode_map.items():
            normalized = normalized.replace(unicode_char, ascii_char)
            
        # Remove zero-width characters and other invisible Unicode
        normalized = re.sub(r'[\u200B-\u200D\uFEFF]', '', normalized)
        
        # Remove combining diacritical marks
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        return normalized

    async def compare_usernames(self, name1: str, name2: str) -> tuple[float, list[str]]:
        """Compare two usernames for similarity and return score and reasons."""
        reasons = []
        
        # Normalize Unicode characters first
        norm1 = self.normalize_unicode(name1)
        norm2 = self.normalize_unicode(name2)
        
        # Check for Unicode tricks
        if norm1 != name1.lower() or norm2 != name2.lower():
            reasons.append("using special Unicode characters")
            if norm1 == norm2:
                return 1.0, reasons
        
        # Clean and normalize usernames
        clean1 = re.sub(r'[^a-zA-Z0-9]', '', norm1)
        clean2 = re.sub(r'[^a-zA-Z0-9]', '', norm2)
        
        # Return 0 if one of the names is empty after cleaning
        if not clean1 or not clean2:
            return 0.0, reasons
            
        # Check for exact match after cleaning
        if clean1 == clean2:
            reasons.append("identical after removing special characters")
            return 1.0, reasons
            
        # Check for character replacement (0/O, l/I, etc.)
        char_replacements = {
            'o': '0',
            'l': '1',
            'i': '1',
            'e': '3',
            'a': '4',
            's': '5',
            't': '7',
            'b': '8',
            'g': '9'
        }
        
        test1 = clean1
        test2 = clean2
        for char, num in char_replacements.items():
            test1 = test1.replace(char, num)
            test2 = test2.replace(char, num)
        
        if test1 == test2:
            reasons.append("identical after checking number/letter substitutions")
            return 0.95, reasons
            
        # Check for repeated characters (e.g., Hobo vs Hoboo)
        stripped1 = re.sub(r'(.)\1+', r'\1', clean1)
        stripped2 = re.sub(r'(.)\1+', r'\1', clean2)
        
        if stripped1 == stripped2:
            reasons.append("identical after removing repeated characters")
            return 0.9, reasons
            
        # Calculate basic similarity
        basic_ratio = ratio(clean1, clean2)
        
        # Check for substring relationship
        if clean1 in clean2 or clean2 in clean1:
            reasons.append("one name contains the other")
            return max(basic_ratio, 0.8), reasons
            
        if basic_ratio > 0.7:
            reasons.append("general text similarity")
            
        return basic_ratio, reasons

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
        name_similarity, name_reasons = await self.compare_usernames(member.name, owner.name)
        if name_similarity > 0.7:
            suspicious_factors.append(f"Username similar to server owner ({name_similarity:.1%} match): {', '.join(name_reasons)}")
            risk_level += 3
            
        # Also check nickname if present
        if member.nick:
            nick_similarity, nick_reasons = await self.compare_usernames(member.nick, owner.name)
            if nick_similarity > 0.7:
                suspicious_factors.append(f"Nickname similar to server owner ({nick_similarity:.1%} match): {', '.join(nick_reasons)}")
                risk_level += 2

        # Avatar comparison
        member_avatar = await self.download_avatar(member.display_avatar.url)
        owner_avatar = await self.download_avatar(owner.display_avatar.url)
        if member_avatar and owner_avatar:
            similarity, reasons = await self.compare_images(member_avatar, owner_avatar)
            if similarity > 0.7:
                suspicious_factors.append(
                    f"Avatar similar to server owner ({similarity:.1%} match):\n" +
                    "\n".join(f"• {r}" for r in reasons)
                )
                risk_level += len(reasons)  # More matching aspects = higher risk

        # Bio/Status comparison
        def get_user_text(user):
            texts = []
            # Get custom status
            activities = [str(activity) for activity in user.activities if activity.type == discord.ActivityType.custom]
            texts.extend(activities)
            # Get roles as text
            roles_text = ' '.join(role.name for role in user.roles)
            texts.append(roles_text)
            return texts

        member_texts = get_user_text(member)
        owner_texts = get_user_text(owner)
        
        for member_text in member_texts:
            for owner_text in owner_texts:
                if member_text and owner_text:  # Skip empty texts
                    status_similarity = await self.compare_text(member_text, owner_text)
                    if status_similarity > 0.6:
                        suspicious_factors.append(
                            f"Profile text similar to server owner ({status_similarity:.1%} match)\n" +
                            f"Owner text: '{owner_text}'\n" +
                            f"Member text: '{member_text}'"
                        )
                        risk_level += 2

        # Check for suspicious patterns in all text fields
        all_text = [member.name]
        if member.nick:
            all_text.append(member.nick)
        all_text.extend(member_texts)
        
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
    async def scan_user(self, ctx, *, member_name: str):
        """Manually scan a user for potential scammer indicators."""
        # Try to find the member by name, ID, or mention
        member = None
        
        # Remove mention formatting if present
        member_name = member_name.strip('<@!>')
        
        # Try to find by ID first
        if member_name.isdigit():
            member = ctx.guild.get_member(int(member_name))
            
        # If not found, try by name
        if not member:
            member = discord.utils.find(
                lambda m: m.name.lower() == member_name.lower() or 
                         (m.nick and m.nick.lower() == member_name.lower()),
                ctx.guild.members
            )
            
        if not member:
            await ctx.send(f"❌ Could not find member: {member_name}")
            return
            
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