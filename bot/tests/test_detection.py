import pytest
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta, timezone
from src.cogs.detection import Detection
from unittest.mock import MagicMock, patch
from PIL import Image
import io

@pytest.fixture
def bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    return bot

@pytest.fixture
def detection_cog(bot):
    return Detection(bot)

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 123456789
    member.name = "TestUser"
    member.nick = None
    member.guild.owner_id = 987654321
    member.guild.owner.name = "OwnerUser"
    member.created_at = datetime.now(timezone.utc) - timedelta(days=5)
    member.display_avatar = MagicMock()
    member.display_avatar.url = "http://example.com/avatar.png"
    member.roles = []
    return member

@pytest.mark.asyncio
async def test_normalize_unicode(detection_cog):
    # Test common Unicode tricks
    assert detection_cog.normalize_unicode("𝐚𝐛с") == "abc"
    assert detection_cog.normalize_unicode("ѕсаm") == "scam"
    assert detection_cog.normalize_unicode("normal") == "normal"
    assert detection_cog.normalize_unicode("аdмiп") == "admin"  # Cyrillic characters

@pytest.mark.asyncio
async def test_compare_usernames(detection_cog):
    # Test exact matches
    similarity, reasons = await detection_cog.compare_usernames("test", "test")
    assert similarity == 1.0
    assert len(reasons) > 0

    # Test character substitutions
    similarity, reasons = await detection_cog.compare_usernames("admin", "adm1n")
    assert similarity > 0.9
    assert any("substitutions" in reason.lower() for reason in reasons)

    # Test repeating characters
    similarity, reasons = await detection_cog.compare_usernames("admin", "adminn")
    assert similarity > 0.8
    assert any("repeated" in reason.lower() for reason in reasons)

    # Test completely different names
    similarity, reasons = await detection_cog.compare_usernames("totally", "different")
    assert similarity < 0.5

@pytest.mark.asyncio
async def test_check_suspicious_patterns(detection_cog):
    # Test common scam patterns
    patterns = await detection_cog.check_suspicious_patterns("Free nitro giveaway!")
    assert len(patterns) >= 2
    assert "free nitro" in patterns
    assert "giveaway" in patterns

    # Test clean message
    patterns = await detection_cog.check_suspicious_patterns("Hello world")
    assert len(patterns) == 0

    # Test multiple patterns
    patterns = await detection_cog.check_suspicious_patterns("Free nitro! Claim your steam gift now!")
    assert len(patterns) >= 3

@pytest.mark.asyncio
async def test_check_user(detection_cog, mock_member):
    # Test new account detection
    factors, risk = await detection_cog.check_user(mock_member)
    assert isinstance(risk, (int, float))
    assert isinstance(factors, list)
    assert any("account" in factor.lower() for factor in factors)
    assert risk > 0

    # Test with similar username to owner
    mock_member.name = "0wnerUser"  # Similar to "OwnerUser"
    factors, risk = await detection_cog.check_user(mock_member)
    assert risk > 3  # Should have higher risk due to similar name
    assert any("similar to server owner" in factor.lower() for factor in factors)

@pytest.mark.asyncio
async def test_handle_detection(detection_cog, mock_member):
    with patch('src.cogs.detection.store_scammer') as mock_store, \
         patch('src.cogs.detection.log_detection') as mock_log:
        
        mock_store.return_value = 1  # Simulated scammer ID
        await detection_cog.handle_detection(mock_member, 8.5, ["suspicious name", "new account"])
        
        # Verify database calls
        mock_store.assert_called_once()
        mock_log.assert_called_once()

@pytest.mark.asyncio
async def test_on_member_join(detection_cog, mock_member):
    with patch.object(detection_cog, 'check_user') as mock_check, \
         patch.object(detection_cog, 'handle_detection') as mock_handle:
        
        mock_check.return_value = (["suspicious factor"], 5.0)
        await detection_cog.on_member_join(mock_member)
        
        mock_check.assert_called_once_with(mock_member)
        mock_handle.assert_called_once()