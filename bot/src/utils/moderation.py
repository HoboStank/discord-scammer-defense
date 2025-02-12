from typing import Optional, List, Dict
import discord
from datetime import datetime, timedelta
from .db import get_db
from sqlalchemy import text

class ModerationActions:
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild_id: str, target_id: str, moderator_id: str, 
                        action: str, reason: str, duration: Optional[int] = None,
                        metadata: Optional[Dict] = None) -> bool:
        """Log a moderation action to the database."""
        try:
            with get_db() as db:
                query = text("""
                    INSERT INTO mod_logs 
                        (guild_id, target_id, moderator_id, action, reason, duration, metadata)
                    VALUES 
                        (:guild_id, :target_id, :mod_id, :action, :reason, :duration, :metadata)
                    RETURNING id;
                """)
                result = db.execute(
                    query,
                    {
                        'guild_id': guild_id,
                        'target_id': target_id,
                        'mod_id': moderator_id,
                        'action': action,
                        'reason': reason,
                        'duration': duration,
                        'metadata': metadata
                    }
                )
                return bool(result.fetchone())
        except Exception as e:
            print(f"Error logging moderation action: {e}")
            return False

    async def warn_user(self, member: discord.Member, reason: str, 
                       moderator: Optional[discord.Member] = None) -> bool:
        """Warn a user and log the action."""
        try:
            # Send warning DM
            try:
                embed = discord.Embed(
                    title="⚠️ Warning",
                    description=f"You have been warned in {member.guild.name}",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=reason)
                await member.send(embed=embed)
            except:
                pass  # User might have DMs disabled

            # Log the warning
            return await self.log_action(
                str(member.guild.id),
                str(member.id),
                str(moderator.id if moderator else self.bot.user.id),
                'warn',
                reason
            )
        except Exception as e:
            print(f"Error warning user: {e}")
            return False

    async def kick_user(self, member: discord.Member, reason: str,
                       moderator: Optional[discord.Member] = None) -> bool:
        """Kick a user and log the action."""
        try:
            # Send kick notification
            try:
                embed = discord.Embed(
                    title="👢 Kicked",
                    description=f"You have been kicked from {member.guild.name}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Reason", value=reason)
                await member.send(embed=embed)
            except:
                pass

            # Kick the member
            await member.kick(reason=reason)

            # Log the kick
            return await self.log_action(
                str(member.guild.id),
                str(member.id),
                str(moderator.id if moderator else self.bot.user.id),
                'kick',
                reason
            )
        except Exception as e:
            print(f"Error kicking user: {e}")
            return False

    async def ban_user(self, member: discord.Member, reason: str,
                      moderator: Optional[discord.Member] = None,
                      delete_message_days: int = 1) -> bool:
        """Ban a user and log the action."""
        try:
            # Send ban notification
            try:
                embed = discord.Embed(
                    title="🔨 Banned",
                    description=f"You have been banned from {member.guild.name}",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=reason)
                await member.send(embed=embed)
            except:
                pass

            # Ban the member
            await member.ban(reason=reason, delete_message_days=delete_message_days)

            # Log the ban
            return await self.log_action(
                str(member.guild.id),
                str(member.id),
                str(moderator.id if moderator else self.bot.user.id),
                'ban',
                reason
            )
        except Exception as e:
            print(f"Error banning user: {e}")
            return False

    async def mute_user(self, member: discord.Member, duration: int, reason: str,
                       moderator: Optional[discord.Member] = None) -> bool:
        """Timeout (mute) a user and log the action."""
        try:
            # Calculate end time
            until = datetime.utcnow() + timedelta(seconds=duration)

            # Send mute notification
            try:
                embed = discord.Embed(
                    title="🔇 Muted",
                    description=f"You have been muted in {member.guild.name}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Reason", value=reason)
                embed.add_field(name="Duration", value=f"{duration} seconds")
                await member.send(embed=embed)
            except:
                pass

            # Timeout the member
            await member.timeout(until, reason=reason)

            # Log the mute
            return await self.log_action(
                str(member.guild.id),
                str(member.id),
                str(moderator.id if moderator else self.bot.user.id),
                'mute',
                reason,
                duration
            )
        except Exception as e:
            print(f"Error muting user: {e}")
            return False

    async def get_recent_actions(self, guild_id: str, limit: int = 10) -> List[Dict]:
        """Get recent moderation actions for a guild."""
        try:
            with get_db() as db:
                query = text("""
                    SELECT * FROM mod_logs 
                    WHERE guild_id = :guild_id 
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                """)
                result = db.execute(query, {'guild_id': guild_id, 'limit': limit})
                return [dict(row) for row in result.fetchall()]
        except Exception as e:
            print(f"Error getting recent actions: {e}")
            return []