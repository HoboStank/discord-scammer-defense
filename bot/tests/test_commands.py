import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

@pytest.fixture
def bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def message():
    message = MagicMock(spec=discord.Message)
    message.content = "!dsd"
    message.author = MagicMock(spec=discord.Member)
    message.author.bot = False
    message.guild = MagicMock(spec=discord.Guild)
    message.channel = MagicMock(spec=discord.TextChannel)
    message.channel.send = AsyncMock()
    return message

@pytest.mark.asyncio
async def test_help_command(bot, message):
    message.content = "!dsd help"
    
    # Mock the help command response
    async def mock_help(ctx):
        embed = discord.Embed(title="DSD Bot Help", description="Available commands:")
        await ctx.send(embed=embed)
    
    bot.help_command = MagicMock()
    bot.help_command.command = mock_help
    
    # Process the command
    ctx = await bot.get_context(message)
    await bot.invoke(ctx)
    
    # Verify help was sent
    message.channel.send.assert_called_once()
    embed = message.channel.send.call_args[1]['embed']
    assert "DSD Bot Help" in embed.title

@pytest.mark.asyncio
async def test_scan_command(bot, message):
    message.content = "!dsd scan @TestUser"
    target_member = MagicMock(spec=discord.Member)
    target_member.name = "TestUser"
    target_member.mention = "@TestUser"
    message.guild.get_member.return_value = target_member
    
    with patch('src.cogs.detection.Detection.check_user') as mock_check:
        mock_check.return_value = (["suspicious_name"], 5.0)
        
        # Process the command
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        # Verify scan results were sent
        message.channel.send.assert_called_once()
        embed = message.channel.send.call_args[1]['embed']
        assert "Scan Results" in embed.title

@pytest.mark.asyncio
async def test_config_commands(bot, message):
    # Test view config
    message.content = "!dsd config view"
    message.author.guild_permissions.administrator = True
    
    with patch('src.utils.server_config.ServerConfig.get') as mock_get:
        mock_get.return_value = {
            'min_detection_score': 0.7,
            'enabled_checks': ['username', 'avatar']
        }
        
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        embed = message.channel.send.call_args[1]['embed']
        assert "Server Configuration" in embed.title

@pytest.mark.asyncio
async def test_monitor_commands(bot, message):
    message.content = "!dsd monitor status"
    message.author.guild_permissions.administrator = True
    
    with patch('src.utils.monitoring.SystemMonitor.get_health_status') as mock_status:
        mock_status.return_value = {
            'status': 'healthy',
            'system': {'cpu_percent': 25, 'memory_used_mb': 500},
            'bot': {'guilds': 2, 'users': 300},
            'uptime': {'uptime_formatted': '1:00:00'}
        }
        
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        embed = message.channel.send.call_args[1]['embed']
        assert "System Status" in embed.title

@pytest.mark.asyncio
async def test_moderation_commands(bot, message):
    # Test warn command
    message.content = "!dsd warn @TestUser test reason"
    message.author.guild_permissions.manage_messages = True
    target_member = MagicMock(spec=discord.Member)
    target_member.name = "TestUser"
    target_member.mention = "@TestUser"
    message.guild.get_member.return_value = target_member
    
    with patch('src.utils.moderation.ModerationActions.warn_user') as mock_warn:
        mock_warn.return_value = True
        
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        message.channel.send.assert_called_with(f"Warning {target_member.mention} for: test reason")

@pytest.mark.asyncio
async def test_command_error_handling(bot, message):
    # Test missing permissions
    message.content = "!dsd warn @TestUser test"
    message.author.guild_permissions.manage_messages = False
    
    ctx = await bot.get_context(message)
    
    # Simulate error handling
    error = commands.MissingPermissions(['manage_messages'])
    await bot.on_command_error(ctx, error)
    
    message.channel.send.assert_called_with("❌ You don't have permission to use this command.")

@pytest.mark.asyncio
async def test_command_cooldowns(bot, message):
    # Test command cooldown
    message.content = "!dsd scan @TestUser"
    
    with patch('discord.ext.commands.cooldown') as mock_cooldown:
        ctx = await bot.get_context(message)
        
        # First call should work
        await bot.invoke(ctx)
        
        # Second call should trigger cooldown
        error = commands.CommandOnCooldown(mock_cooldown, retry_after=5.0)
        await bot.on_command_error(ctx, error)
        
        assert any("on cooldown" in str(call.args[0]) 
                  for call in message.channel.send.call_args_list)