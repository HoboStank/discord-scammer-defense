import discord
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from .db import get_db
from sqlalchemy import text

logger = logging.getLogger('dsd_bot.logging')

class ActionLogger:
    def __init__(self, bot):
        self.bot = bot

    async def log_to_channel(self, guild: discord.Guild, log_channel_id: str, embed: discord.Embed):
        """Send a log message to the specified channel."""
        try:
            if log_channel_id:
                channel = guild.get_channel(int(log_channel_id))
                if channel and channel.permissions_for(guild.me).send_messages:
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending log to channel: {e}")

    async def create_action_embed(self, action_type: str, target: discord.Member,
                                moderator: discord.Member, reason: str,
                                metadata: Optional[Dict[str, Any]] = None) -> discord.Embed:
        """Create a standardized embed for action logging."""
        color_map = {
            'warn': discord.Color.yellow(),
            'kick': discord.Color.orange(),
            'ban': discord.Color.red(),
            'mute': discord.Color.purple(),
            'unmute': discord.Color.green(),
            'unban': discord.Color.green(),
            'detection': discord.Color.blue(),
            'appeal': discord.Color.gold()
        }

        embed = discord.Embed(
            title=f"🔔 {action_type.title()} Action",
            description=f"Action taken against {target.mention}",
            color=color_map.get(action_type.lower(), discord.Color.greyple()),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="User", value=f"{target} ({target.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator} ({moderator.id})", inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)

        if metadata:
            for key, value in metadata.items():
                if value:  # Only add non-empty metadata
                    embed.add_field(name=key.replace('_', ' ').title(), 
                                  value=str(value), inline=True)

        embed.set_footer(text=f"User ID: {target.id}")
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        return embed

    async def log_mod_action(self, guild: discord.Guild, action_type: str,
                           target: discord.Member, moderator: discord.Member,
                           reason: str, log_channel_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """Log a moderation action to both database and Discord channel."""
        try:
            # Create embed for Discord logging
            embed = await self.create_action_embed(
                action_type, target, moderator, reason, metadata
            )

            # Log to channel if configured
            await self.log_to_channel(guild, log_channel_id, embed)

            # Log to database
            with get_db() as db:
                query = text("""
                    INSERT INTO mod_logs 
                        (guild_id, target_id, moderator_id, action, reason, metadata)
                    VALUES 
                        (:guild_id, :target_id, :mod_id, :action, :reason, :metadata)
                    RETURNING id;
                """)
                
                result = db.execute(
                    query,
                    {
                        'guild_id': str(guild.id),
                        'target_id': str(target.id),
                        'mod_id': str(moderator.id),
                        'action': action_type,
                        'reason': reason,
                        'metadata': metadata
                    }
                )
                return result.fetchone()[0]
        except Exception as e:
            logger.error(f"Error logging moderation action: {e}")
            return None

    async def log_detection(self, guild: discord.Guild, target: discord.Member,
                          risk_level: float, factors: list,
                          log_channel_id: Optional[str] = None):
        """Log a scammer detection event."""
        metadata = {
            'risk_level': f"{risk_level:.1%}",
            'detection_factors': '\n'.join(f"• {f}" for f in factors)
        }

        return await self.log_mod_action(
            guild=guild,
            action_type='detection',
            target=target,
            moderator=guild.me,  # Bot is the moderator for detections
            reason="Automatic scammer detection",
            log_channel_id=log_channel_id,
            metadata=metadata
        )

    async def log_appeal(self, guild: discord.Guild, target: discord.Member,
                        moderator: discord.Member, approved: bool,
                        reason: str, log_channel_id: Optional[str] = None):
        """Log an appeal decision."""
        metadata = {
            'decision': 'Approved' if approved else 'Rejected',
            'appeal_reason': reason
        }

        return await self.log_mod_action(
            guild=guild,
            action_type='appeal',
            target=target,
            moderator=moderator,
            reason=f"Appeal {'approved' if approved else 'rejected'}: {reason}",
            log_channel_id=log_channel_id,
            metadata=metadata
        )

    async def get_user_history(self, guild_id: str, user_id: str, 
                             limit: int = 10) -> list:
        """Get a user's moderation history in a guild."""
        try:
            with get_db() as db:
                query = text("""
                    SELECT * FROM mod_logs 
                    WHERE guild_id = :guild_id AND target_id = :user_id 
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                """)
                
                result = db.execute(
                    query,
                    {
                        'guild_id': guild_id,
                        'user_id': user_id,
                        'limit': limit
                    }
                )
                return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return []