from typing import Dict, List, Optional, Union
import json
from .db import get_db
from sqlalchemy import text

class ServerConfig:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id
        self.default_config = {
            'min_detection_score': 0.7,
            'enabled_checks': ['username', 'avatar', 'profile'],
            'auto_actions': {
                'warn': 0.7,    # Warn at 70% confidence
                'kick': 0.85,   # Kick at 85% confidence
                'ban': 0.95     # Ban at 95% confidence
            },
            'alert_channel': None,
            'trusted_roles': [],
            'immune_roles': [],
            'log_channel': None,
            'log_level': 'INFO'
        }
        self._config = None

    async def load(self) -> Dict:
        """Load server configuration from database."""
        try:
            with get_db() as db:
                query = text("""
                    SELECT * FROM server_configs 
                    WHERE guild_id = :guild_id
                """)
                result = db.execute(query, {'guild_id': self.guild_id})
                config = result.fetchone()
                
                if not config:
                    # Create default config
                    query = text("""
                        INSERT INTO server_configs 
                            (guild_id, min_detection_score, enabled_checks, auto_actions)
                        VALUES 
                            (:guild_id, :score, :checks, :actions)
                        RETURNING *;
                    """)
                    result = db.execute(
                        query,
                        {
                            'guild_id': self.guild_id,
                            'score': self.default_config['min_detection_score'],
                            'checks': json.dumps(self.default_config['enabled_checks']),
                            'actions': json.dumps(self.default_config['auto_actions'])
                        }
                    )
                    config = result.fetchone()
                
                self._config = dict(config)
                return self._config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config

    async def save(self) -> bool:
        """Save current configuration to database."""
        try:
            with get_db() as db:
                query = text("""
                    UPDATE server_configs 
                    SET 
                        min_detection_score = :score,
                        enabled_checks = :checks,
                        auto_actions = :actions,
                        alert_channel = :alert_ch,
                        trusted_roles = :trusted,
                        immune_roles = :immune,
                        log_channel = :log_ch,
                        log_level = :log_lvl
                    WHERE guild_id = :guild_id
                """)
                db.execute(
                    query,
                    {
                        'guild_id': self.guild_id,
                        'score': self._config['min_detection_score'],
                        'checks': json.dumps(self._config['enabled_checks']),
                        'actions': json.dumps(self._config['auto_actions']),
                        'alert_ch': self._config['alert_channel'],
                        'trusted': json.dumps(self._config['trusted_roles']),
                        'immune': json.dumps(self._config['immune_roles']),
                        'log_ch': self._config['log_channel'],
                        'log_lvl': self._config['log_level']
                    }
                )
                return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        if self._config is None:
            return self.default_config.get(key, default)
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if self._config is None:
            self._config = self.default_config.copy()
        self._config[key] = value

    async def should_take_action(self, risk_score: float) -> Optional[str]:
        """Determine what action to take based on risk score."""
        actions = self.get('auto_actions')
        
        # Check actions from most severe to least
        if risk_score >= actions['ban']:
            return 'ban'
        elif risk_score >= actions['kick']:
            return 'kick'
        elif risk_score >= actions['warn']:
            return 'warn'
        
        return None

    def is_immune(self, member_roles: List[int]) -> bool:
        """Check if a member is immune from auto-moderation."""
        immune_roles = self.get('immune_roles', [])
        return any(role.id in immune_roles for role in member_roles)

    def is_trusted(self, member_roles: List[int]) -> bool:
        """Check if a member has trusted role."""
        trusted_roles = self.get('trusted_roles', [])
        return any(role.id in trusted_roles for role in member_roles)