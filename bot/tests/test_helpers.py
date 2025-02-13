import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, AsyncMock
from typing import Optional, Any, Dict

class MockContext:
    """Helper class to create mock command contexts."""
    @staticmethod
    def create(
        message_content: str,
        author_permissions: Dict[str, bool] = None,
        guild_id: str = "987654321",
        channel_id: str = "123456789"
    ):
        # Create basic mocks
        guild = MagicMock(spec=discord.Guild)
        guild.id = guild_id
        
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = channel_id
        channel.send = AsyncMock()
        channel.guild = guild
        
        author = MagicMock(spec=discord.Member)
        author.bot = False
        author.guild = guild
        author.guild_permissions = MagicMock()
        
        # Set up permissions
        if author_permissions:
            for perm, value in author_permissions.items():
                setattr(author.guild_permissions, perm, value)
        
        message = MagicMock(spec=discord.Message)
        message.content = message_content
        message.author = author
        message.guild = guild
        message.channel = channel
        
        return message

class CommandTestHelpers:
    """Helper methods for testing commands."""
    @staticmethod
    def assert_embed_field(embed: discord.Embed, field_name: str, expected_value: str) -> bool:
        """Check if an embed contains a field with the expected value."""
        for field in embed.fields:
            if field.name == field_name and expected_value in field.value:
                return True
        return False
    
    @staticmethod
    def assert_embed_contains(embed: discord.Embed, text: str) -> bool:
        """Check if an embed contains specific text in title, description, or fields."""
        if text in (embed.title or ""):
            return True
        if text in (embed.description or ""):
            return True
        for field in embed.fields:
            if text in field.name or text in field.value:
                return True
        return False
    
    @staticmethod
    def get_last_embed(mock_send) -> Optional[discord.Embed]:
        """Get the last embed sent through a mock send method."""
        if not mock_send.call_args:
            return None
        args, kwargs = mock_send.call_args
        return kwargs.get('embed') or (args[0] if args else None)

@pytest.fixture
def ctx_factory():
    """Fixture to create command contexts with different configurations."""
    return MockContext.create

@pytest.fixture
def cmd_helpers():
    """Fixture to access command test helper methods."""
    return CommandTestHelpers

@pytest.fixture
async def test_guild():
    """Create a mock guild with basic setup."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = "987654321"
    guild.name = "Test Guild"
    
    # Add some basic roles
    guild.roles = [
        MagicMock(spec=discord.Role, id="111", name="Admin"),
        MagicMock(spec=discord.Role, id="222", name="Moderator"),
        MagicMock(spec=discord.Role, id="333", name="Member")
    ]
    
    # Add some basic channels
    guild.channels = [
        MagicMock(spec=discord.TextChannel, id="444", name="general"),
        MagicMock(spec=discord.TextChannel, id="555", name="moderation"),
        MagicMock(spec=discord.TextChannel, id="666", name="alerts")
    ]
    
    return guild

@pytest.fixture
def error_regex():
    """Common regex patterns for error messages."""
    return {
        'missing_perms': r"(?i).*don't have permission.*",
        'invalid_input': r"(?i).*invalid.*",
        'not_found': r"(?i).*not found.*",
        'cooldown': r"(?i).*cooldown.*"
    }

async def verify_command_response(ctx, expected_patterns: Dict[str, str]) -> bool:
    """Helper function to verify command responses match expected patterns."""
    if not ctx.channel.send.call_args:
        return False
        
    response = ctx.channel.send.call_args[0][0]
    if isinstance(response, discord.Embed):
        content = f"{response.title} {response.description}"
        for field in response.fields:
            content += f" {field.name} {field.value}"
    else:
        content = str(response)
        
    return all(pattern in content for pattern in expected_patterns.values())