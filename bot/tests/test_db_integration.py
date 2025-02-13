import pytest
import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from src.utils.db import get_db, store_scammer, log_detection, check_existing_scammer

# Use test database URL
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres123@localhost:5432/dsd_test_db')

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
async def test_db(db_engine):
    """Create fresh test database tables for each test."""
    from src.utils.db import Base
    
    # Drop and recreate all tables
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(bind=db_engine)
    
    # Override get_db to use test database
    async def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # Replace production get_db with test version
    original_get_db = get_db
    get_db.override = override_get_db
    
    yield TestingSessionLocal()
    
    # Restore original get_db
    get_db.override = None

@pytest.mark.asyncio
async def test_store_scammer(test_db):
    """Test storing a scammer profile."""
    discord_id = "123456789"
    username = "test_scammer"
    detection_score = 0.85
    detection_reasons = ["suspicious_name", "new_account"]
    avatar_hash = "test_hash"
    profile_data = {"joined_at": datetime.utcnow().isoformat()}
    
    # Store scammer
    scammer_id = await store_scammer(
        discord_id, username, detection_score, detection_reasons,
        avatar_hash, profile_data
    )
    
    assert scammer_id is not None
    
    # Verify stored data
    result = test_db.execute(
        text("SELECT * FROM scammer_profiles WHERE discord_id = :discord_id"),
        {"discord_id": discord_id}
    )
    scammer = dict(result.fetchone())
    
    assert scammer["username"] == username
    assert scammer["detection_score"] == detection_score
    assert "suspicious_name" in scammer["detection_reasons"]
    assert scammer["avatar_hash"] == avatar_hash

@pytest.mark.asyncio
async def test_log_detection(test_db):
    """Test logging a detection event."""
    # First create a scammer profile
    scammer_id = await store_scammer(
        "123456789", "test_scammer", 0.85,
        ["suspicious_name"], "test_hash", {}
    )
    
    # Log detection event
    event_id = await log_detection(
        scammer_id=scammer_id,
        guild_id="987654321",
        similarity_score=0.9,
        matched_features=["avatar_match", "name_match"],
        action_taken="warn"
    )
    
    assert event_id is not None
    
    # Verify logged event
    result = test_db.execute(
        text("SELECT * FROM detection_events WHERE id = :event_id"),
        {"event_id": event_id}
    )
    event = dict(result.fetchone())
    
    assert event["scammer_id"] == scammer_id
    assert event["guild_id"] == "987654321"
    assert event["similarity_score"] == 0.9
    assert "avatar_match" in event["matched_features"]
    assert event["action_taken"] == "warn"

@pytest.mark.asyncio
async def test_check_existing_scammer(test_db):
    """Test checking for existing scammer."""
    # Store test scammer
    discord_id = "123456789"
    await store_scammer(
        discord_id, "test_scammer", 0.85,
        ["suspicious_name"], "test_hash", {}
    )
    
    # Check for existing scammer
    scammer = await check_existing_scammer(discord_id)
    assert scammer is not None
    assert scammer["discord_id"] == discord_id
    
    # Check for non-existent scammer
    nonexistent = await check_existing_scammer("999999999")
    assert nonexistent is None

@pytest.mark.asyncio
async def test_transaction_rollback(test_db):
    """Test database transaction rollback on error."""
    discord_id = "123456789"
    
    # Attempt to store invalid data that should trigger rollback
    try:
        async with get_db() as db:
            db.execute(
                text("""
                    INSERT INTO scammer_profiles (discord_id, detection_score)
                    VALUES (:discord_id, :score)
                """),
                {"discord_id": discord_id, "score": "invalid"}  # Invalid score type
            )
            await db.commit()
    except Exception:
        pass  # Expected to fail
    
    # Verify no data was stored
    result = test_db.execute(
        text("SELECT * FROM scammer_profiles WHERE discord_id = :discord_id"),
        {"discord_id": discord_id}
    )
    assert result.fetchone() is None