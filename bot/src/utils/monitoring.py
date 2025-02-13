import logging
import psutil
import discord
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger('dsd_bot.monitoring')

class SystemMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)
        self.process = psutil.Process()

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource usage stats."""
        memory = self.process.memory_info()
        cpu_percent = self.process.cpu_percent(interval=0.1)
        
        return {
            'memory_used_mb': memory.rss / (1024 * 1024),  # Convert to MB
            'cpu_percent': cpu_percent,
            'threads': self.process.num_threads(),
            'open_files': len(self.process.open_files()),
            'connections': len(self.process.connections())
        }

    def get_bot_stats(self) -> Dict[str, Any]:
        """Get Discord bot statistics."""
        return {
            'guilds': len(self.bot.guilds),
            'users': sum(g.member_count for g in self.bot.guilds),
            'latency_ms': round(self.bot.latency * 1000, 2),
            'commands_used': getattr(self.bot, 'commands_used', 0),
            'events_processed': getattr(self.bot, 'events_processed', 0)
        }

    def get_uptime(self) -> Dict[str, Any]:
        """Get bot uptime information."""
        uptime = datetime.now(timezone.utc) - self.start_time
        return {
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0]  # Format as HH:MM:SS
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the bot."""
        try:
            system_stats = self.get_system_stats()
            bot_stats = self.get_bot_stats()
            uptime = self.get_uptime()
            
            # Define health thresholds
            is_healthy = (
                system_stats['cpu_percent'] < 80 and  # CPU below 80%
                system_stats['memory_used_mb'] < 1024 and  # Memory below 1GB
                bot_stats['latency_ms'] < 500  # Latency below 500ms
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system': system_stats,
                'bot': bot_stats,
                'uptime': uptime
            }
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

    async def log_metrics(self, log_channel_id: str = None):
        """Log metrics to Discord channel if configured."""
        try:
            if not log_channel_id:
                return

            stats = self.get_health_status()
            embed = discord.Embed(
                title="📊 System Metrics",
                color=discord.Color.blue() if stats['status'] == 'healthy' else discord.Color.orange()
            )

            # System metrics
            embed.add_field(
                name="System",
                value=f"CPU: {stats['system']['cpu_percent']}%\n"
                      f"Memory: {stats['system']['memory_used_mb']:.1f}MB\n"
                      f"Threads: {stats['system']['threads']}",
                inline=True
            )

            # Bot metrics
            embed.add_field(
                name="Bot",
                value=f"Guilds: {stats['bot']['guilds']}\n"
                      f"Users: {stats['bot']['users']}\n"
                      f"Latency: {stats['bot']['latency_ms']}ms",
                inline=True
            )

            # Uptime
            embed.add_field(
                name="Uptime",
                value=stats['uptime']['uptime_formatted'],
                inline=False
            )

            embed.set_footer(text=f"Status: {stats['status'].title()}")

            channel = self.bot.get_channel(int(log_channel_id))
            if channel:
                await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error logging metrics: {e}")