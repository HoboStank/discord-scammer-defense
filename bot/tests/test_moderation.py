import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, patch
from src.cogs.moderation import Moderation
from datetime import datetime

@pytest.fixture
def bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def moderation_cog(bot):
    return Moderation(bot)

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 123456789
    member.name = "TestUser"
    member.mention = "@TestUser"
    member.guild.id = 987654321
    member.avatar = None
    return member

@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.guild.id = 987654321
    return ctx

@pytest.mark.asyncio
async def test_warn_user(moderation_cog, mock_member, mock_context):
    reason = "Test warning"
    
    with patch('src.utils.moderation.ModerationActions.warn_user') as mock_warn, \
         patch.object(mock_context, 'send') as mock_send:
        mock_warn.return_value = True
        await moderation_cog.warn_user(mock_context, mock_member, reason)
        
        mock_send.assert_called_once()
        assert "Warning" in mock_send.call_args[0][0]
        assert mock_member.mention in mock_send.call_args[0][0]

@pytest.mark.asyncio
async def test_ban_user(moderation_cog, mock_member, mock_context):
    reason = "Test ban"
    
    with patch('src.utils.moderation.ModerationActions.ban_user') as mock_ban, \
         patch.object(mock_context, 'send') as mock_send:
        mock_ban.return_value = True
        await moderation_cog.ban_user(mock_context, mock_member, reason)
        
        mock_send.assert_called_once()
        assert "Banning" in mock_send.call_args[0][0]
        assert mock_member.mention in mock_send.call_args[0][0]

@pytest.mark.asyncio
async def test_permission_checks(moderation_cog, mock_context):
    # Test permissions by simulating missing permissions
    mock_context.author.guild_permissions.manage_messages = False
    mock_context.author.guild_permissions.ban_members = False
    
    with pytest.raises(commands.MissingPermissions):
        await moderation_cog.warn_user(mock_context, MagicMock(), "test")
        
    with pytest.raises(commands.MissingPermissions):
        await moderation_cog.ban_user(mock_context, MagicMock(), "test")