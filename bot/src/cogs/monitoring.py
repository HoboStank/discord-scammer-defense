import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime, timedelta
from ..utils.monitoring import SystemMonitor
from ..utils.server_config import ServerConfig

logger = logging.getLogger('dsd_bot.monitoring_cog')

class Monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor = SystemMonitor(bot)
        self.metrics_loop.start()
        self.metric_channels = {}  # guild_id: channel_id mapping
        
    def cog_unload(self):
        self.metrics_loop.cancel()

    @tasks.loop(minutes=5)  # Update metrics every 5 minutes
    async def metrics_loop(self):
        """Periodic task to update metrics in configured channels."""
        try:
            for guild_id, channel_id in self.metric_channels.items():
                await self.monitor.log_metrics(channel_id)
        except Exception as e:
            logger.error(f"Error in metrics loop: {e}")

    @metrics_loop.before_loop
    async def before_metrics(self):
        """Wait for bot to be ready before starting metrics loop."""
        await self.bot.wait_until_ready()
        
    @commands.group(name='monitor')
    @commands.has_permissions(administrator=True)
    async def monitor(self, ctx):
        """Monitoring commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a monitoring command. Use `!dsd help monitor` for more information.")

    @monitor.command(name='status')
    async def show_status(self, ctx):
        """Show current system status."""
        status = self.monitor.get_health_status()
        
        embed = discord.Embed(
            title="🔍 System Status",
            color=discord.Color.green() if status['status'] == 'healthy' 
                  else discord.Color.orange() if status['status'] == 'degraded'
                  else discord.Color.red()
        )
        
        # System metrics
        embed.add_field(
            name="System Resources",
            value=f"CPU: {status['system']['cpu_percent']}%\n"
                  f"Memory: {status['system']['memory_used_mb']:.1f} MB\n"
                  f"Threads: {status['system']['threads']}",
            inline=True
        )
        
        # Bot metrics
        embed.add_field(
            name="Bot Statistics",
            value=f"Guilds: {status['bot']['guilds']}\n"
                  f"Users: {status['bot']['users']}\n"
                  f"Latency: {status['bot']['latency_ms']}ms",
            inline=True
        )
        
        # Uptime
        embed.add_field(
            name="Uptime",
            value=status['uptime']['uptime_formatted'],
            inline=False
        )
        
        embed.set_footer(text=f"Status: {status['status'].title()} | Updated: {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        await ctx.send(embed=embed)

    @monitor.command(name='setchannel')
    async def set_metrics_channel(self, ctx, channel: discord.TextChannel = None):
        """Set or clear the metrics reporting channel."""
        if channel:
            self.metric_channels[str(ctx.guild.id)] = str(channel.id)
            await ctx.send(f"✅ Metrics will be posted to {channel.mention} every 5 minutes")
        else:
            self.metric_channels.pop(str(ctx.guild.id), None)
            await ctx.send("✅ Metrics channel cleared")

    @monitor.command(name='debug')
    async def show_debug(self, ctx):
        """Show detailed debug information."""
        embed = discord.Embed(
            title="🔧 Debug Information",
            color=discord.Color.blue()
        )
        
        # Add process info
        process_info = self.monitor.get_system_stats()
        embed.add_field(
            name="Process Information",
            value=f"Open Files: {process_info['open_files']}\n"
                  f"Active Connections: {process_info['connections']}\n"
                  f"Thread Count: {process_info['threads']}",
            inline=False
        )
        
        # Add bot info
        bot_info = self.monitor.get_bot_stats()
        embed.add_field(
            name="Bot Information",
            value=f"Commands Used: {bot_info['commands_used']}\n"
                  f"Events Processed: {bot_info['events_processed']}\n"
                  f"Average Latency: {bot_info['latency_ms']}ms",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Monitoring(bot))
    logger.info('Monitoring cog loaded')