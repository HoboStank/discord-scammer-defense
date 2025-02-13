from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import jwt
import aiohttp
from datetime import datetime, timedelta
import secrets
from typing import Optional
from .models import User, Session as UserSession

# Configuration - These should be moved to environment variables
DISCORD_CLIENT_ID = "YOUR_CLIENT_ID"
DISCORD_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
DISCORD_REDIRECT_URI = "http://localhost:8000/auth/callback"
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
JWT_SECRET = "your-secret-key"  # Change this in production

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://discord.com/api/oauth2/authorize",
    tokenUrl="https://discord.com/api/oauth2/token"
)

class Auth:
    def __init__(self, db: Session):
        self.db = db

    def create_discord_oauth_url(self) -> str:
        """Generate Discord OAuth2 URL for login."""
        state = secrets.token_urlsafe(32)
        params = {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": "identify email guilds",
            "state": state
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://discord.com/oauth2/authorize?{query}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange OAuth2 code for access token."""
        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with session.post(
                f"{DISCORD_API_ENDPOINT}/oauth2/token",
                data=data,
                headers=headers
            ) as resp:
                return await resp.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get Discord user information."""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(
                f"{DISCORD_API_ENDPOINT}/users/@me",
                headers=headers
            ) as resp:
                return await resp.json()

    def create_session(self, user_id: int) -> str:
        """Create a new session for the user."""
        session = UserSession(
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        self.db.add(session)
        self.db.commit()
        return session.session_token

    def validate_session(self, session_token: str) -> Optional[User]:
        """Validate a session token and return the associated user."""
        session = self.db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if session:
            return self.db.query(User).get(session.user_id)
        return None

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency to get the current authenticated user."""
    session_token = request.cookies.get("session")
    if not session_token:
        return None
        
    auth = Auth(db)
    return auth.validate_session(session_token)