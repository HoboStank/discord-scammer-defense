from discord.ext import commands
import discord
import logging
from utils.server_config import ServerConfig

logger = logging.getLogger('dsd_bot.config')

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.configs = {}

    async def get_config(self, guild_id: str) -> ServerConfig:
        """Get server configuration, using cache if available."""
        if guild_id not in self.configs:
            config = ServerConfig(guild_id)
            await config.load()
            self.configs[guild_id] = config
        return self.configs[guild_id]

    @commands.group(name='config')
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        """Configure bot settings for your server."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a configuration command. Use `!dsd help config` for more information.")

    @config.command(name='view')
    async def view_config(self, ctx):
        """View current server configuration."""
        config = await self.get_config(str(ctx.guild.id))
        
        embed = discord.Embed(
            title="Server Configuration",
            color=discord.Color.blue()
        )
        
        # Detection settings
        embed.add_field(
            name="Detection Settings",
            value=f"Minimum Score: {config.get('min_detection_score')}\n" +
                  f"Enabled Checks: {', '.join(config.get('enabled_checks'))}",
            inline=False
        )
        
        # Auto-actions
        actions = config.get('auto_actions')
        embed.add_field(
            name="Automated Actions",
            value="\n".join([f"{k.title()}: {v*100}% confidence" for k, v in actions.items()]),
            inline=False
        )
        
        # Channels
        alert_channel = ctx.guild.get_channel(int(config.get('alert_channel'))) if config.get('alert_channel') else None
        log_channel = ctx.guild.get_channel(int(config.get('log_channel'))) if config.get('log_channel') else None
        
        embed.add_field(
            name="Channels",
            value=f"Alert Channel: {alert_channel.mention if alert_channel else 'Not set'}\n" +
                  f"Log Channel: {log_channel.mention if log_channel else 'Not set'}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @config.command(name='setchannel')
    async def set_channel(self, ctx, channel_type: str, channel: discord.TextChannel):
        """Set alert or log channel."""
        if channel_type not in ['alert', 'log']:
            await ctx.send("❌ Channel type must be either 'alert' or 'log'")
            return
        
        config = await self.get_config(str(ctx.guild.id))
        config.set(f'{channel_type}_channel', str(channel.id))
        await config.save()
        
        await ctx.send(f"✅ {channel_type.title()} channel set to {channel.mention}")

    @config.command(name='setaction')
    async def set_action(self, ctx, action: str, threshold: float):
        """Set threshold for automated actions (warn/kick/ban)."""
        if action not in ['warn', 'kick', 'ban']:
            await ctx.send("❌ Action must be either 'warn', 'kick', or 'ban'")
            return
            
        if not 0 <= threshold <= 1:
            await ctx.send("❌ Threshold must be between 0 and 1")
            return
        
        config = await self.get_config(str(ctx.guild.id))
        actions = config.get('auto_actions')
        actions[action] = threshold
        config.set('auto_actions', actions)
        await config.save()
        
        await ctx.send(f"✅ {action.title()} threshold set to {threshold*100}% confidence")

    @config.command(name='setrole')
    async def set_role(self, ctx, role_type: str, role: discord.Role):
        """Set trusted or immune roles."""
        if role_type not in ['trusted', 'immune']:
            await ctx.send("❌ Role type must be either 'trusted' or 'immune'")
            return
        
        config = await self.get_config(str(ctx.guild.id))
        roles = config.get(f'{role_type}_roles', [])
        
        if str(role.id) in roles:
            roles.remove(str(role.id))
            message = f"✅ Removed {role.name} from {role_type} roles"
        else:
            roles.append(str(role.id))
            message = f"✅ Added {role.name} to {role_type} roles"
        
        config.set(f'{role_type}_roles', roles)
        await config.save()
        
        await ctx.send(message)

    @config.command(name='setcheck')
    async def set_check(self, ctx, check: str, enabled: bool):
        """Enable or disable specific detection checks."""
        valid_checks = ['username', 'avatar', 'profile']
        if check not in valid_checks:
            await ctx.send(f"❌ Check must be one of: {', '.join(valid_checks)}")
            return
        
        config = await self.get_config(str(ctx.guild.id))
        checks = config.get('enabled_checks', [])
        
        if enabled and check not in checks:
            checks.append(check)
        elif not enabled and check in checks:
            checks.remove(check)
            
        config.set('enabled_checks', checks)
        await config.save()
        
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"✅ {check.title()} check {status}")

    @config.command(name='reset')
    async def reset_config(self, ctx):
        """Reset server configuration to defaults."""
        config = await self.get_config(str(ctx.guild.id))
        config._config = config.default_config.copy()
        await config.save()
        
        await ctx.send("✅ Server configuration reset to defaults")

async def setup(bot):
    await bot.add_cog(Configuration(bot))
    logger.info('Configuration cog loaded')