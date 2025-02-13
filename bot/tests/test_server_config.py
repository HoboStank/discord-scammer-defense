import pytest
from unittest.mock import MagicMock, patch
from src.utils.server_config import ServerConfig
import json

@pytest.fixture
def server_config():
    return ServerConfig("987654321")

def test_default_config(server_config):
    assert server_config.guild_id == "987654321"
    assert server_config._config is None
    assert isinstance(server_config.default_config, dict)
    assert 'min_detection_score' in server_config.default_config
    assert 'enabled_checks' in server_config.default_config
    assert 'auto_actions' in server_config.default_config

@pytest.mark.asyncio
async def test_load_config(server_config):
    test_config = {
        'guild_id': '987654321',
        'min_detection_score': 0.8,
        'enabled_checks': ['username', 'avatar'],
        'auto_actions': {'warn': 0.7, 'kick': 0.85, 'ban': 0.95}
    }
    
    with patch('src.utils.db.get_db') as mock_db_ctx:
        mock_db = MagicMock()
        mock_db_ctx.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = test_config
        
        config = await server_config.load()
        assert config == test_config
        assert server_config._config == test_config

@pytest.mark.asyncio
async def test_save_config(server_config):
    server_config._config = {
        'min_detection_score': 0.8,
        'enabled_checks': ['username', 'avatar'],
        'auto_actions': {'warn': 0.7, 'kick': 0.85, 'ban': 0.95},
        'alert_channel': '123456789',
        'trusted_roles': [],
        'immune_roles': [],
        'log_channel': None,
        'log_level': 'INFO'
    }
    
    with patch('src.utils.db.get_db') as mock_db_ctx:
        mock_db = MagicMock()
        mock_db_ctx.return_value.__enter__.return_value = mock_db
        
        success = await server_config.save()
        assert success is True
        mock_db.execute.assert_called_once()

def test_get_config_value(server_config):
    server_config._config = {'test_key': 'test_value'}
    assert server_config.get('test_key') == 'test_value'
    assert server_config.get('nonexistent', 'default') == 'default'
    
    # Test getting from default config when _config is None
    server_config._config = None
    assert server_config.get('min_detection_score') == server_config.default_config['min_detection_score']

def test_set_config_value(server_config):
    server_config.set('test_key', 'test_value')
    assert server_config._config['test_key'] == 'test_value'
    
    # Test setting when _config is None
    server_config._config = None
    server_config.set('new_key', 'new_value')
    assert server_config._config['new_key'] == 'new_value'
    assert isinstance(server_config._config, dict)

@pytest.mark.asyncio
async def test_should_take_action(server_config):
    server_config._config = {
        'auto_actions': {
            'warn': 0.7,
            'kick': 0.85,
            'ban': 0.95
        }
    }
    
    assert await server_config.should_take_action(0.6) is None  # Below all thresholds
    assert await server_config.should_take_action(0.75) == 'warn'
    assert await server_config.should_take_action(0.9) == 'kick'
    assert await server_config.should_take_action(0.96) == 'ban'

def test_role_checks(server_config):
    server_config._config = {
        'immune_roles': [123, 456],
        'trusted_roles': [789, 101]
    }
    
    mock_roles = [
        MagicMock(id=123),
        MagicMock(id=789)
    ]
    
    assert server_config.is_immune(mock_roles) is True
    assert server_config.is_trusted(mock_roles) is True
    
    # Test with non-matching roles
    mock_roles = [MagicMock(id=999)]
    assert server_config.is_immune(mock_roles) is False
    assert server_config.is_trusted(mock_roles) is False