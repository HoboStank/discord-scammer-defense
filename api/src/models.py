from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ScammerProfile(Base):
    """Store information about detected scammers."""
    __tablename__ = 'scammer_profiles'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True, nullable=False)
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile data at time of detection
    username = Column(String)
    avatar_hash = Column(String)  # Store hash of avatar for comparison
    profile_data = Column(JSON)   # Store additional profile info (status, bio, etc.)
    
    # Detection details
    detection_score = Column(Float)
    detection_reasons = Column(JSON)  # List of reasons why flagged
    
    # Relationships
    detections = relationship("DetectionEvent", back_populates="scammer")
    appeals = relationship("Appeal", back_populates="scammer")

class DetectionEvent(Base):
    """Record of each time a scammer is detected."""
    __tablename__ = 'detection_events'

    id = Column(Integer, primary_key=True)
    scammer_id = Column(Integer, ForeignKey('scammer_profiles.id'))
    guild_id = Column(String, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Detection details
    similarity_score = Column(Float)
    matched_features = Column(JSON)  # What features matched (name, avatar, etc.)
    action_taken = Column(String)    # What action was taken (warn, kick, ban)
    
    # Relationships
    scammer = relationship("ScammerProfile", back_populates="detections")

class ServerConfig(Base):
    """Store per-server configuration."""
    __tablename__ = 'server_configs'

    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    
    # Detection settings
    min_detection_score = Column(Float, default=0.7)
    enabled_checks = Column(JSON)  # List of enabled detection methods
    
    # Auto-moderation settings
    auto_actions = Column(JSON)    # What actions to take at what scores
    alert_channel = Column(String) # Channel ID for alerts
    
    # Trusted roles/users
    trusted_roles = Column(JSON)   # Role IDs that can use admin commands
    immune_roles = Column(JSON)    # Role IDs that skip scanning
    
    # Logging
    log_channel = Column(String)   # Channel ID for logging
    log_level = Column(String, default='INFO')

class Appeal(Base):
    """Store appeal information."""
    __tablename__ = 'appeals'

    id = Column(Integer, primary_key=True)
    scammer_id = Column(Integer, ForeignKey('scammer_profiles.id'))
    guild_id = Column(String, nullable=False)
    
    # Appeal details
    submitted_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='pending')  # pending, approved, rejected
    reason = Column(String)
    evidence = Column(JSON)        # Links or text evidence
    
    # Voting
    votes = Column(JSON)          # {user_id: vote}
    resolved_at = Column(DateTime)
    resolved_by = Column(String)  # User ID who made final decision
    
    # Relationships
    scammer = relationship("ScammerProfile", back_populates="appeals")

class ModLog(Base):
    """Store moderation actions."""
    __tablename__ = 'mod_logs'

    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)  # User ID of target
    moderator_id = Column(String, nullable=False)  # User ID of moderator
    
    # Action details
    action = Column(String, nullable=False)  # warn, mute, kick, ban
    reason = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Additional data
    duration = Column(Integer)  # For temporary actions (mutes, bans)
    extra_data = Column(JSON)    # Any additional context (renamed from metadata)