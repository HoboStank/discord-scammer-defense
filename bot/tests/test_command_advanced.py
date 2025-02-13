import pytest
import discord
from discord.ext import commands
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

@pytest.mark.asyncio
async def test_command_aliases(bot, message):
    """Test that command aliases work correctly."""
    aliases = {
        "!dsd s @TestUser": "!dsd scan @TestUser",
        "!dsd w @TestUser": "!dsd warn @TestUser",
        "!dsd b @TestUser": "!dsd ban @TestUser"
    }
    
    target_member = MagicMock(spec=discord.Member)
    target_member.name = "TestUser"
    target_member.mention = "@TestUser"
    message.guild.get_member.return_value = target_member
    
    for alias, full_command in aliases.items():
        message.content = alias
        ctx_alias = await bot.get_context(message)
        
        message.content = full_command
        ctx_full = await bot.get_context(message)
        
        # Both contexts should invoke the same command
        assert ctx_alias.command == ctx_full.command

@pytest.mark.asyncio
async def test_config_subcommands(bot, message):
    """Test configuration subcommands."""
    test_cases = [
        {
            'command': '!dsd config setchannel alert #alerts',
            'expected_result': {'type': 'alert', 'channel_id': '123456789'},
            'success_message': '✅ Alert channel set'
        },
        {
            'command': '!dsd config setaction warn 0.8',
            'expected_result': {'action': 'warn', 'threshold': 0.8},
            'success_message': '✅ Warn threshold set'
        },
        {
            'command': '!dsd config setrole trusted @Moderator',
            'expected_result': {'role_type': 'trusted', 'role_id': '123456789'},
            'success_message': '✅ Added @Moderator to trusted roles'
        }
    ]
    
    message.author.guild_permissions.administrator = True
    
    for case in test_cases:
        message.content = case['command']
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        assert any(case['success_message'] in str(call.args[0]) 
                  for call in message.channel.send.call_args_list)

@pytest.mark.asyncio
async def test_parameter_validation(bot, message):
    """Test command parameter validation."""
    validation_cases = [
        {
            'command': '!dsd scan',  # Missing required user parameter
            'error': commands.MissingRequiredArgument,
            'error_message': 'Missing required argument'
        },
        {
            'command': '!dsd config setaction warn invalid',  # Invalid threshold value
            'error': commands.BadArgument,
            'error_message': 'Threshold must be between 0 and 1'
        },
        {
            'command': '!dsd ban @TestUser',  # Missing reason
            'error': commands.MissingRequiredArgument,
            'error_message': 'Missing required argument: reason'
        }
    ]
    
    for case in validation_cases:
        message.content = case['command']
        ctx = await bot.get_context(message)
        
        error = case['error'](ctx.command, case['error_message'])
        await bot.on_command_error(ctx, error)
        
        assert any(case['error_message'] in str(call.args[0]) 
                  for call in message.channel.send.call_args_list)

@pytest.mark.asyncio
async def test_command_context_propagation(bot, message):
    """Test that command context is properly propagated to cogs."""
    message.content = "!dsd scan @TestUser"
    
    with patch('src.cogs.detection.Detection.check_user') as mock_check:
        mock_check.return_value = (["suspicious_name"], 5.0)
        
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        
        # Verify context was passed correctly
        assert ctx.guild == message.guild
        assert ctx.channel == message.channel
        assert ctx.author == message.author
        assert ctx.message == message

@pytest.mark.asyncio
async def test_concurrent_commands(bot, message):
    """Test handling multiple commands concurrently."""
    commands_to_test = [
        "!dsd scan @TestUser",
        "!dsd config view",
        "!dsd monitor status"
    ]
    
    tasks = []
    for cmd in commands_to_test:
        message.content = cmd
        ctx = await bot.get_context(message)
        tasks.append(bot.invoke(ctx))
    
    # Run commands concurrently
    await asyncio.gather(*tasks)
    
    # Verify all commands were processed
    assert message.channel.send.call_count == len(commands_to_test)

@pytest.mark.asyncio
async def test_command_history(bot, message):
    """Test command history tracking."""
    commands_executed = []
    
    async def track_command(ctx):
        commands_executed.append(ctx.command.name)
        await ctx.send(f"Executed {ctx.command.name}")
    
    # Mock command execution
    bot.dispatch = MagicMock(side_effect=track_command)
    
    test_commands = [
        "!dsd scan @TestUser",
        "!dsd warn @TestUser test",
        "!dsd config view"
    ]
    
    for cmd in test_commands:
        message.content = cmd
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
    
    # Verify command history
    assert len(commands_executed) == len(test_commands)
    assert all(cmd in commands_executed for cmd in ['scan', 'warn', 'config'])