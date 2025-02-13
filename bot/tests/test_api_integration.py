import pytest
import aiohttp
import json
from datetime import datetime
from unittest.mock import patch
from src.utils.api_client import APIClient

API_BASE_URL = "http://localhost:5000/v1"

@pytest.fixture
async def api_client():
    """Create test API client."""
    async with aiohttp.ClientSession() as session:
        client = APIClient(session, API_BASE_URL, "test_token")
        yield client

@pytest.mark.asyncio
async def test_report_scammer(api_client):
    test_data = {
        "discord_id": "123456789",
        "username": "test_scammer",
        "detection_score": 0.85,
        "detection_reasons": ["suspicious_name", "new_account"],
        "guild_id": "987654321"
    }
    
    with patch.object(api_client.session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = lambda: {"id": 1}
        
        response = await api_client.report_scammer(**test_data)
        assert response["id"] == 1
        
        # Verify correct endpoint and data
        mock_post.assert_called_with(
            f"{API_BASE_URL}/scammers/report",
            json=test_data,
            headers=api_client.headers
        )

@pytest.mark.asyncio
async def test_check_user(api_client):
    discord_id = "123456789"
    
    with patch.object(api_client.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = lambda: {
            "is_scammer": True,
            "detection_score": 0.85,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        response = await api_client.check_user(discord_id)
        assert response["is_scammer"] is True
        assert "detection_score" in response
        
        mock_get.assert_called_with(
            f"{API_BASE_URL}/users/{discord_id}/check",
            headers=api_client.headers
        )

@pytest.mark.asyncio
async def test_submit_appeal(api_client):
    appeal_data = {
        "discord_id": "123456789",
        "guild_id": "987654321",
        "reason": "False positive",
        "evidence": "Explanation here"
    }
    
    with patch.object(api_client.session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = lambda: {"appeal_id": 1}
        
        response = await api_client.submit_appeal(**appeal_data)
        assert response["appeal_id"] == 1
        
        mock_post.assert_called_with(
            f"{API_BASE_URL}/appeals",
            json=appeal_data,
            headers=api_client.headers
        )

@pytest.mark.asyncio
async def test_get_server_stats(api_client):
    guild_id = "987654321"
    
    with patch.object(api_client.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = lambda: {
            "total_detections": 10,
            "active_appeals": 2,
            "scammer_count": 5
        }
        
        response = await api_client.get_server_stats(guild_id)
        assert "total_detections" in response
        assert "active_appeals" in response
        assert "scammer_count" in response
        
        mock_get.assert_called_with(
            f"{API_BASE_URL}/servers/{guild_id}/stats",
            headers=api_client.headers
        )

@pytest.mark.asyncio
async def test_error_handling(api_client):
    # Test 404 response
    with patch.object(api_client.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 404
        mock_get.return_value.__aenter__.return_value.json = lambda: {
            "error": "User not found"
        }
        
        with pytest.raises(Exception) as exc_info:
            await api_client.check_user("nonexistent")
        assert "User not found" in str(exc_info.value)
    
    # Test server error
    with patch.object(api_client.session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 500
        mock_post.return_value.__aenter__.return_value.json = lambda: {
            "error": "Internal server error"
        }
        
        with pytest.raises(Exception) as exc_info:
            await api_client.report_scammer(
                discord_id="123456789",
                username="test",
                detection_score=0.85,
                detection_reasons=[],
                guild_id="987654321"
            )
        assert "Internal server error" in str(exc_info.value)