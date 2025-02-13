import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_notification(self, embed: Dict[str, Any]) -> bool:
        """Send a Discord webhook notification."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "embeds": [embed]
                }
                async with session.post(
                    self.webhook_url,
                    json=payload
                ) as response:
                    return response.status == 204
        except Exception as e:
            print(f"Error sending webhook notification: {e}")
            return False

    @staticmethod
    def create_detection_embed(detection: Any) -> Dict[str, Any]:
        """Create an embed for a new scammer detection."""
        return {
            "title": "New Scammer Detected",
            "color": 0xED4245,  # Discord red
            "fields": [
                {
                    "name": "User",
                    "value": f"{detection.username} (`{detection.user_id}`)",
                    "inline": True
                },
                {
                    "name": "Score",
                    "value": f"{detection.score:.2f}",
                    "inline": True
                },
                {
                    "name": "Action Taken",
                    "value": detection.action.title(),
                    "inline": True
                }
            ],
            "thumbnail": {"url": detection.avatar_url} if detection.avatar_url else None,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def create_appeal_embed(appeal: Any, action: str) -> Dict[str, Any]:
        """Create an embed for appeal updates."""
        color = 0x57F287 if action == "approved" else 0xED4245  # Green for approved, red for rejected
        return {
            "title": f"Appeal {action.title()}",
            "color": color,
            "fields": [
                {
                    "name": "User",
                    "value": f"{appeal.detection.username} (`{appeal.user_id}`)",
                    "inline": True
                },
                {
                    "name": "Original Action",
                    "value": appeal.detection.action.title(),
                    "inline": True
                },
                {
                    "name": "Appeal Reason",
                    "value": appeal.reason[:1024],  # Discord field value limit
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def create_config_update_embed(guild_id: str, changes: Dict[str, Any], user: Any) -> Dict[str, Any]:
        """Create an embed for configuration changes."""
        return {
            "title": "Configuration Updated",
            "color": 0x5865F2,  # Discord blurple
            "fields": [
                {
                    "name": "Server ID",
                    "value": guild_id,
                    "inline": True
                },
                {
                    "name": "Updated By",
                    "value": f"{user.username} (`{user.discord_id}`)",
                    "inline": True
                },
                {
                    "name": "Changes",
                    "value": "\n".join(f"• {k}: {v}" for k, v in changes.items())[:1024],
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def create_reversal_embed(detection: Any, reverser: Any, reason: Optional[str] = None) -> Dict[str, Any]:
        """Create an embed for action reversals."""
        return {
            "title": "Detection Reversed",
            "color": 0xFEE75C,  # Discord yellow
            "fields": [
                {
                    "name": "User",
                    "value": f"{detection.username} (`{detection.user_id}`)",
                    "inline": True
                },
                {
                    "name": "Original Action",
                    "value": detection.action.title(),
                    "inline": True
                },
                {
                    "name": "Reversed By",
                    "value": f"{reverser.username} (`{reverser.discord_id}`)",
                    "inline": True
                },
                *([] if not reason else [{
                    "name": "Reason",
                    "value": reason[:1024],
                    "inline": False
                }])
            ],
            "timestamp": datetime.utcnow().isoformat()
        }