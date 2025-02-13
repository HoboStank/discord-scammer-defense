import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, patch, AsyncMock
from src.cogs.config import Configuration

@pytest.fixture
def bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def config_cog(bot):
    return Configuration(bot)

@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.guild.id = 987654321
    ctx.send = AsyncMock()
    return ctx

@pytest.fixture
def mock_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 123456789
    channel.mention = "#test-channel"
    return channel

@pytest.mark.asyncio
async def test_view_config(config_cog, mock_context):
    test_config = {
        'min_detection_score': 0.7,
        'enabled_checks': ['username', 'avatar'],
        'auto_actions': {'warn': 0.7, 'kick': 0.85, 'ban': 0.95},
        'alert_channel': '123456789',
        'log_channel': None
    }
    
    with patch('src.utils.server_config.ServerConfig.load') as mock_load, \
         patch('src.utils.server_config.ServerConfig.get') as mock_get:
        mock_load.return_value = test_config
        mock_get.side_effect = lambda key, default=None: test_config.get(key, default)
        
        await config_cog.view_config(mock_context)
        
        mock_context.send.assert_called_once()
        embed = mock_context.send.call_args[0][0]
        assert isinstance(embed, discord.Embed)
        assert "Server Configuration" in embed.title

@pytest.mark.asyncio
async def test_set_channel(config_cog, mock_context, mock_channel):
    with patch('src.utils.server_config.ServerConfig.set') as mock_set, \
         patch('src.utils.server_config.ServerConfig.save') as mock_save:
        mock_save.return_value = True
        
        # Test setting alert channel
        await config_cog.set_channel(mock_context, "alert", mock_channel)
        mock_set.assert_called_with('alert_channel', str(mock_channel.id))
        mock_context.send.assert_called_with(f"✅ Alert channel set to {mock_channel.mention}")

        # Test invalid channel type
        await config_cog.set_channel(mock_context, "invalid", mock_channel)
        assert any("must be either 'alert' or 'log'" in str(call.args[0]) 
                  for call in mock_context.send.call_args_list)

@pytest.mark.asyncio
async def test_set_action(config_cog, mock_context):
    test_actions = {'warn': 0.7, 'kick': 0.85, 'ban': 0.95}
    
    with patch('src.utils.server_config.ServerConfig.get') as mock_get, \
         patch('src.utils.server_config.ServerConfig.set') as mock_set, \
         patch('src.utils.server_config.ServerConfig.save') as mock_save:
        mock_get.return_value = test_actions
        mock_save.return_value = True
        
        # Test valid action and threshold
        await config_cog.set_action(mock_context, "warn", 0.8)
        mock_set.assert_called()
        assert mock_context.send.call_args[0][0].startswith("✅")

        # Test invalid action
        await config_cog.set_action(mock_context, "invalid", 0.8)
        assert any("must be either 'warn', 'kick', or 'ban'" in str(call.args[0]) 
                  for call in mock_context.send.call_args_list)

        # Test invalid threshold
        await config_cog.set_action(mock_context, "warn", 1.5)
        assert any("must be between 0 and 1" in str(call.args[0]) 
                  for call in mock_context.send.call_args_list)

@pytest.mark.asyncio
async def test_reset_config(config_cog, mock_context):
    with patch('src.utils.server_config.ServerConfig.save') as mock_save:
        mock_save.return_value = True
        
        await config_cog.reset_config(mock_context)
        mock_context.send.assert_called_with("✅ Server configuration reset to defaults")