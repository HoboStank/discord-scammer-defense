import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger('dsd_bot.api_client')

class APIClient:
    """Client for interacting with the Discord Scammer Defense API."""
    
    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_token: str):
        self.session = session
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response and errors."""
        if response.status >= 400:
            error_data = await response.json()
            error_msg = error_data.get('error', 'Unknown error')
            logger.error(f"API error: {error_msg} (Status: {response.status})")
            raise Exception(f"API error: {error_msg}")
        return await response.json()

    async def report_scammer(self, discord_id: str, username: str, 
                           detection_score: float, detection_reasons: list,
                           guild_id: str, profile_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Report a detected scammer to the API."""
        data = {
            'discord_id': discord_id,
            'username': username,
            'detection_score': detection_score,
            'detection_reasons': detection_reasons,
            'guild_id': guild_id,
            'profile_data': profile_data or {}
        }
        
        async with self.session.post(
            f"{self.base_url}/scammers/report",
            json=data,
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def check_user(self, discord_id: str) -> Dict[str, Any]:
        """Check if a user is in the scammer database."""
        async with self.session.get(
            f"{self.base_url}/users/{discord_id}/check",
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def submit_appeal(self, discord_id: str, guild_id: str,
                          reason: str, evidence: str) -> Dict[str, Any]:
        """Submit an appeal for a flagged user."""
        data = {
            'discord_id': discord_id,
            'guild_id': guild_id,
            'reason': reason,
            'evidence': evidence,
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        async with self.session.post(
            f"{self.base_url}/appeals",
            json=data,
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def get_server_stats(self, guild_id: str) -> Dict[str, Any]:
        """Get scammer detection statistics for a server."""
        async with self.session.get(
            f"{self.base_url}/servers/{guild_id}/stats",
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def get_appeal_status(self, appeal_id: str) -> Dict[str, Any]:
        """Get the status of an appeal."""
        async with self.session.get(
            f"{self.base_url}/appeals/{appeal_id}",
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def update_appeal(self, appeal_id: str, 
                          status: str, moderator_id: str,
                          reason: Optional[str] = None) -> Dict[str, Any]:
        """Update the status of an appeal."""
        data = {
            'status': status,
            'moderator_id': moderator_id,
            'reason': reason,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        async with self.session.put(
            f"{self.base_url}/appeals/{appeal_id}",
            json=data,
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

    async def report_metrics(self, guild_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Report server metrics to the API."""
        async with self.session.post(
            f"{self.base_url}/servers/{guild_id}/metrics",
            json=metrics,
            headers=self.headers
        ) as response:
            return await self._handle_response(response)

import aiohttp
import json
import asyncio
from typing import Dict, Any, Optional, List
from aiohttp import ClientTimeout
import logging

logger = logging.getLogger('dsd_bot.api_client')

class DashboardAPIError(Exception):
    """Custom exception for dashboard API errors."""
    pass

class DashboardAPIClient:
    def __init__(
        self, 
        api_url: str, 
        api_token: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0
    ):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = ClientTimeout(total=timeout)
        self._session = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Any:
        """Make an HTTP request with retry logic."""
        url = f"{self.api_url}{endpoint}"
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                session = await self._get_session()
                async with self._lock:  # Ensure thread-safety
                    async with session.request(
                        method,
                        url,
                        json=data,
                        params=params,
                        headers=self.headers
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401:
                            raise DashboardAPIError("Authentication failed. Check API token.")
                        elif response.status == 429:
                            retry_after = float(response.headers.get('Retry-After', self.retry_delay))
                            await asyncio.sleep(retry_after)
                        else:
                            error_text = await response.text()
                            raise DashboardAPIError(f"API request failed: {error_text}")

            except asyncio.TimeoutError:
                last_error = "Request timed out"
            except aiohttp.ClientError as e:
                last_error = f"Connection error: {str(e)}"
            except Exception as e:
                last_error = str(e)

            attempts += 1
            if attempts < self.max_retries:
                await asyncio.sleep(self.retry_delay * attempts)

        raise DashboardAPIError(f"Failed after {self.max_retries} attempts. Last error: {last_error}")

    async def send_detection(
        self,
        user_id: str,
        username: str,
        guild_id: str,
        score: float,
        action: str,
        check_results: Dict[str, Any],
        avatar_url: Optional[str] = None,
        evidence_screenshot: Optional[str] = None
    ) -> bool:
        """Send a new detection to the dashboard."""
        try:
            payload = {
                "user_id": user_id,
                "username": username,
                "avatar_url": avatar_url,
                "guild_id": guild_id,
                "score": score,
                "action": action,
                "check_results": check_results,
                "evidence_screenshot": evidence_screenshot
            }

            await self._make_request("POST", "/api/detections/new", data=payload)
            return True

        except DashboardAPIError as e:
            logger.error(f"Failed to send detection to dashboard: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending detection to dashboard: {e}")
            return False

    async def get_server_config(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get server configuration from the dashboard."""
        try:
            return await self._make_request("GET", f"/api/config/{guild_id}")
        except DashboardAPIError as e:
            logger.error(f"Failed to get server config: {e}")
            return None

    async def update_server_config(self, guild_id: str, config: Dict[str, Any]) -> bool:
        """Update server configuration in the dashboard."""
        try:
            await self._make_request(
                "POST",
                "/api/config/save",
                params={"guild_id": guild_id},
                data=config
            )
            return True
        except DashboardAPIError as e:
            logger.error(f"Failed to update server config: {e}")
            return False

    async def get_recent_detections(
        self,
        guild_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get recent detections for a server."""
        try:
            return await self._make_request(
                "GET",
                "/api/detections",
                params={
                    "guild_id": guild_id,
                    "limit": limit,
                    "offset": offset
                }
            )
        except DashboardAPIError as e:
            logger.error(f"Failed to get recent detections: {e}")
            return []

    def __del__(self):
        """Ensure the session is closed on cleanup."""
        if self._session and not self._session.closed:
            asyncio.create_task(self.close())