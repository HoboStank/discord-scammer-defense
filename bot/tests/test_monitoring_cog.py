import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, patch, AsyncMock
from src.cogs.monitoring import Monitoring
from datetime import datetime, timezone

@pytest.fixture
def bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def monitoring_cog(bot):
    cog = Monitoring(bot)
    # Stop the metrics loop to prevent interference with tests
    cog.metrics_loop.cancel()
    return cog

@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.guild.id = 987654321
    ctx.send = AsyncMock()
    return ctx

@pytest.mark.asyncio
async def test_show_status(monitoring_cog, mock_context):
    test_status = {
        'status': 'healthy',
        'system': {
            'cpu_percent': 25.5,
            'memory_used_mb': 500,
            'threads': 5
        },
        'bot': {
            'guilds': 2,
            'users': 300,
            'latency_ms': 50
        },
        'uptime': {
            'uptime_formatted': '1:00:00'
        }
    }
    
    with patch.object(monitoring_cog.monitor, 'get_health_status') as mock_status:
        mock_status.return_value = test_status
        await monitoring_cog.show_status(mock_context)
        
        mock_context.send.assert_called_once()
        embed = mock_context.send.call_args[0][0]
        assert isinstance(embed, discord.Embed)
        assert "System Status" in embed.title
        assert embed.color == discord.Color.green()  # Healthy status

@pytest.mark.asyncio
async def test_set_metrics_channel(monitoring_cog, mock_context):
    # Test setting channel
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 123456789
    channel.mention = "#metrics"
    
    await monitoring_cog.set_metrics_channel(mock_context, channel)
    assert monitoring_cog.metric_channels[str(mock_context.guild.id)] == str(channel.id)
    mock_context.send.assert_called_with(f"✅ Metrics will be posted to {channel.mention} every 5 minutes")
    
    # Test clearing channel
    await monitoring_cog.set_metrics_channel(mock_context, None)
    assert str(mock_context.guild.id) not in monitoring_cog.metric_channels
    mock_context.send.assert_called_with("✅ Metrics channel cleared")

@pytest.mark.asyncio
async def test_show_debug(monitoring_cog, mock_context):
    test_system_stats = {
        'open_files': 5,
        'connections': 2,
        'threads': 10
    }
    
    test_bot_stats = {
        'commands_used': 100,
        'events_processed': 500,
        'latency_ms': 50
    }
    
    with patch.object(monitoring_cog.monitor, 'get_system_stats') as mock_system, \
         patch.object(monitoring_cog.monitor, 'get_bot_stats') as mock_bot:
        mock_system.return_value = test_system_stats
        mock_bot.return_value = test_bot_stats
        
        await monitoring_cog.show_debug(mock_context)
        
        mock_context.send.assert_called_once()
        embed = mock_context.send.call_args[0][0]
        assert isinstance(embed, discord.Embed)
        assert "Debug Information" in embed.title
        
        # Verify stats are included in embed fields
        field_values = [field.value for field in embed.fields]
        assert str(test_system_stats['threads']) in field_values[0]  # Process Information
        assert str(test_bot_stats['commands_used']) in field_values[1]  # Bot Information

@pytest.mark.asyncio
async def test_metrics_loop(monitoring_cog):
    # Setup test channels
    monitoring_cog.metric_channels = {
        '123': '456',
        '789': '012'
    }
    
    with patch.object(monitoring_cog.monitor, 'log_metrics') as mock_log:
        # Manually trigger the loop once
        await monitoring_cog.metrics_loop()
        
        # Should have called log_metrics for each configured channel
        assert mock_log.call_count == len(monitoring_cog.metric_channels)
        mock_log.assert_any_call('456')
        mock_log.assert_any_call('012')

@pytest.mark.asyncio
async def test_permission_checks(monitoring_cog, mock_context):
    # Test without admin permissions
    mock_context.author.guild_permissions.administrator = False
    
    with pytest.raises(commands.MissingPermissions):
        await monitoring_cog.show_status(mock_context)
    
    with pytest.raises(commands.MissingPermissions):
        await monitoring_cog.set_metrics_channel(mock_context, None)
        
    with pytest.raises(commands.MissingPermissions):
        await monitoring_cog.show_debug(mock_context)