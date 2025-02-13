import pytest
import discord
from unittest.mock import MagicMock, patch, AsyncMock
from src.utils.monitoring import SystemMonitor
from datetime import datetime, timezone, timedelta

@pytest.fixture
def bot():
    bot = MagicMock(spec=discord.Client)
    bot.guilds = [
        MagicMock(member_count=100),
        MagicMock(member_count=200)
    ]
    bot.latency = 0.05  # 50ms
    return bot

@pytest.fixture
def monitor(bot):
    monitor = SystemMonitor(bot)
    # Set a fixed start time for consistent testing
    monitor.start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    return monitor

def test_get_system_stats(monitor):
    with patch('psutil.Process') as mock_process:
        process = MagicMock()
        process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        process.cpu_percent.return_value = 25.5
        process.num_threads.return_value = 5
        process.open_files.return_value = []
        process.connections.return_value = []
        mock_process.return_value = process
        
        stats = monitor.get_system_stats()
        assert isinstance(stats, dict)
        assert abs(stats['memory_used_mb'] - 100) < 0.1  # Around 100MB
        assert stats['cpu_percent'] == 25.5
        assert stats['threads'] == 5
        assert stats['open_files'] == 0
        assert stats['connections'] == 0

def test_get_bot_stats(monitor):
    stats = monitor.get_bot_stats()
    assert isinstance(stats, dict)
    assert stats['guilds'] == 2
    assert stats['users'] == 300  # Sum of member_count
    assert stats['latency_ms'] == 50.0  # 0.05 * 1000
    assert 'commands_used' in stats
    assert 'events_processed' in stats

def test_get_uptime(monitor):
    uptime = monitor.get_uptime()
    assert isinstance(uptime, dict)
    assert 'start_time' in uptime
    assert 'uptime_seconds' in uptime
    assert 'uptime_formatted' in uptime
    # Should be around 1 hour (3600 seconds) based on fixture
    assert 3500 < uptime['uptime_seconds'] < 3700

def test_get_health_status(monitor):
    with patch.object(monitor, 'get_system_stats') as mock_system, \
         patch.object(monitor, 'get_bot_stats') as mock_bot, \
         patch.object(monitor, 'get_uptime') as mock_uptime:
        
        # Test healthy status
        mock_system.return_value = {
            'cpu_percent': 25.5,
            'memory_used_mb': 500,
            'threads': 5,
            'open_files': 0,
            'connections': 0
        }
        mock_bot.return_value = {
            'guilds': 2,
            'users': 300,
            'latency_ms': 100,
            'commands_used': 0,
            'events_processed': 0
        }
        mock_uptime.return_value = {
            'uptime_seconds': 3600,
            'uptime_formatted': '1:00:00'
        }
        
        status = monitor.get_health_status()
        assert status['status'] == 'healthy'
        
        # Test degraded status (high CPU)
        mock_system.return_value['cpu_percent'] = 90
        status = monitor.get_health_status()
        assert status['status'] == 'degraded'
        
        # Test error handling
        mock_system.side_effect = Exception("Test error")
        status = monitor.get_health_status()
        assert status['status'] == 'error'
        assert 'error' in status

@pytest.mark.asyncio
async def test_log_metrics(monitor):
    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    
    with patch.object(monitor.bot, 'get_channel') as mock_get_channel:
        mock_get_channel.return_value = mock_channel
        
        # Test with valid channel
        await monitor.log_metrics('123456789')
        mock_channel.send.assert_called_once()
        embed = mock_channel.send.call_args[0][0]
        assert isinstance(embed, discord.Embed)
        assert "System Metrics" in embed.title
        
        # Test with invalid channel
        mock_get_channel.return_value = None
        await monitor.log_metrics('invalid_id')
        # Should not try to send to invalid channel
        assert mock_channel.send.call_count == 1