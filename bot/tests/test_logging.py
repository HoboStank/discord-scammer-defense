import pytest
import discord
from unittest.mock import MagicMock, patch, AsyncMock
from src.utils.logging import ActionLogger
from datetime import datetime

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def logger(bot):
    return ActionLogger(bot)

@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321
    return guild

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 123456789
    member.name = "TestUser"
    member.mention = "@TestUser"
    member.avatar = None
    return member

@pytest.fixture
def mock_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.permissions_for.return_value.send_messages = True
    return channel

@pytest.mark.asyncio
async def test_create_action_embed(logger, mock_member):
    moderator = MagicMock(spec=discord.Member)
    moderator.id = 987654321
    moderator.name = "ModUser"
    
    embed = await logger.create_action_embed(
        "warn",
        mock_member,
        moderator,
        "Test reason",
        {"duration": "1 hour"}
    )
    
    assert isinstance(embed, discord.Embed)
    assert "Warning" in embed.title
    assert mock_member.mention in embed.description
    assert "Test reason" in [field.value for field in embed.fields]
    assert "1 hour" in [field.value for field in embed.fields]

@pytest.mark.asyncio
async def test_log_to_channel(logger, mock_guild, mock_channel):
    embed = discord.Embed(title="Test Log", description="Test message")
    
    # Test successful logging
    mock_guild.get_channel.return_value = mock_channel
    await logger.log_to_channel(mock_guild, "123456789", embed)
    mock_channel.send.assert_called_once_with(embed=embed)
    
    # Test missing channel
    mock_guild.get_channel.return_value = None
    await logger.log_to_channel(mock_guild, "invalid_id", embed)
    assert mock_channel.send.call_count == 1  # Should not have called send again

@pytest.mark.asyncio
async def test_log_mod_action(logger, mock_guild, mock_member):
    with patch('src.utils.db.get_db') as mock_db_ctx:
        mock_db = MagicMock()
        mock_db_ctx.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = [1]  # Return mock log ID
        
        log_id = await logger.log_mod_action(
            mock_guild,
            "warn",
            mock_member,
            mock_member,  # Using same member as moderator for test
            "Test warning",
            "123456789",
            {"duration": "1 hour"}
        )
        
        assert log_id is not None
        mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_history(logger):
    mock_history = [
        {"action": "warn", "timestamp": datetime.now(), "reason": "Test warning"},
        {"action": "ban", "timestamp": datetime.now(), "reason": "Test ban"}
    ]
    
    with patch('src.utils.db.get_db') as mock_db_ctx:
        mock_db = MagicMock()
        mock_db_ctx.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = mock_history
        
        history = await logger.get_user_history("987654321", "123456789", limit=10)
        
        assert len(history) == 2
        assert all(isinstance(entry, dict) for entry in history)
        mock_db.execute.assert_called_once()