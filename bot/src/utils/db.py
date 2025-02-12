import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import logging
from datetime import datetime
import json

# Set up logging
logger = logging.getLogger('dsd_bot.db')

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres123@db:5432/dsd_db')

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

async def store_scammer(discord_id: str, username: str, detection_score: float, detection_reasons: list, 
                       avatar_hash: str = None, profile_data: dict = None):
    """Store a detected scammer in the database."""
    try:
        with get_db() as db:
            # Check if scammer already exists
            query = text("""
                INSERT INTO scammer_profiles 
                    (discord_id, username, detection_score, detection_reasons, avatar_hash, profile_data, last_updated)
                VALUES 
                    (:discord_id, :username, :score, :reasons, :avatar_hash, :profile_data, :updated_at)
                ON CONFLICT (discord_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    detection_score = EXCLUDED.detection_score,
                    detection_reasons = EXCLUDED.detection_reasons,
                    avatar_hash = EXCLUDED.avatar_hash,
                    profile_data = EXCLUDED.profile_data,
                    last_updated = EXCLUDED.last_updated
                RETURNING id;
            """)
            result = db.execute(
                query,
                {
                    "discord_id": discord_id,
                    "username": username,
                    "score": detection_score,
                    "reasons": json.dumps(detection_reasons),
                    "avatar_hash": avatar_hash,
                    "profile_data": json.dumps(profile_data) if profile_data else None,
                    "updated_at": datetime.utcnow()
                }
            )
            scammer_id = result.fetchone()[0]
            logger.info(f"Stored/updated scammer profile for {username} (ID: {discord_id})")
            return scammer_id
    except Exception as e:
        logger.error(f"Error storing scammer: {e}")
        return None

async def log_detection(scammer_id: int, guild_id: str, similarity_score: float, 
                       matched_features: list, action_taken: str = None):
    """Log a detection event."""
    try:
        with get_db() as db:
            query = """
                INSERT INTO detection_events 
                    (scammer_id, guild_id, similarity_score, matched_features, action_taken)
                VALUES 
                    (%s, %s, %s, %s, %s)
                RETURNING id;
            """
            result = db.execute(
                query,
                (
                    scammer_id,
                    guild_id,
                    similarity_score,
                    json.dumps(matched_features),
                    action_taken
                )
            )
            event_id = result.fetchone()[0]
            logger.info(f"Logged detection event {event_id} for scammer {scammer_id} in guild {guild_id}")
            return event_id
    except Exception as e:
        logger.error(f"Error logging detection: {e}")
        return None

async def get_server_config(guild_id: str):
    """Get server configuration."""
    try:
        with get_db() as db:
            query = "SELECT * FROM server_configs WHERE guild_id = %s;"
            result = db.execute(query, (guild_id,))
            config = result.fetchone()
            
            if not config:
                # Create default config if none exists
                query = """
                    INSERT INTO server_configs 
                        (guild_id, min_detection_score, enabled_checks, auto_actions)
                    VALUES 
                        (%s, 0.7, %s, %s)
                    RETURNING *;
                """
                default_checks = json.dumps(["username", "avatar", "profile"])
                default_actions = json.dumps({
                    "warn": 0.7,
                    "kick": 0.85,
                    "ban": 0.95
                })
                result = db.execute(query, (guild_id, default_checks, default_actions))
                config = result.fetchone()
                
            return dict(config) if config else None
    except Exception as e:
        logger.error(f"Error getting server config: {e}")
        return None

async def check_existing_scammer(discord_id: str):
    """Check if a user is already marked as a scammer."""
    try:
        with get_db() as db:
            query = text("SELECT * FROM scammer_profiles WHERE discord_id = :discord_id")
            result = db.execute(query, {"discord_id": discord_id})
            scammer = result.fetchone()
            return dict(scammer) if scammer else None
    except Exception as e:
        logger.error(f"Error checking existing scammer: {e}")
        return None