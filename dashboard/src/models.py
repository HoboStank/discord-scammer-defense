from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'dashboard_users'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, unique=True)
    avatar_url = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Session(Base):
    __tablename__ = 'dashboard_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('dashboard_users.id'), nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class ServerStats(Base):
    __tablename__ = 'dashboard_server_stats'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False)
    total_scans = Column(Integer, default=0)
    detected_scammers = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    actions_taken = Column(JSON)  # Store counts of different actions (warns, kicks, bans)
    avg_detection_score = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'dashboard_audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('dashboard_users.id'), nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

class DashboardConfig(Base):
    __tablename__ = 'dashboard_configs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    min_detection_score = Column(Float, default=0.7)
    enabled_checks = Column(JSON, default=lambda: ["username", "avatar", "profile"])
    auto_actions = Column(JSON, default=lambda: {
        "warn": 0.7,
        "kick": 0.85,
        "ban": 0.95
    })
    alert_channel = Column(String)
    log_channel = Column(String)
    trusted_roles = Column(JSON, default=list)
    immune_roles = Column(JSON, default=list)
    custom_theme = Column(JSON)
    enabled_widgets = Column(JSON, default=lambda: [
        "stats", "recent_activity", "quick_actions"
    ])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert the config to a dictionary format."""
        return {
            "guild_id": self.guild_id,
            "min_detection_score": self.min_detection_score,
            "enabled_checks": self.enabled_checks,
            "auto_actions": self.auto_actions,
            "alert_channel": self.alert_channel,
            "log_channel": self.log_channel,
            "trusted_roles": self.trusted_roles,
            "immune_roles": self.immune_roles,
            "custom_theme": self.custom_theme,
            "enabled_widgets": self.enabled_widgets
        }

class ScammerDetection(Base):
    __tablename__ = 'dashboard_scammer_detections'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    username = Column(String, nullable=False)
    avatar_url = Column(String)
    guild_id = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    action = Column(String, nullable=False)  # warn, kick, ban
    status = Column(String, nullable=False, default='active')  # active, appealed, reversed
    check_results = Column(JSON)  # Detailed results from each check
    evidence_screenshot = Column(String)  # URL to screenshot if available
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reversed_at = Column(DateTime)
    reversed_by = Column(Integer, ForeignKey('dashboard_users.id'))
    appeal_id = Column(Integer, ForeignKey('dashboard_appeals.id'))
    
    # Relationships
    reverser = relationship("User", foreign_keys=[reversed_by])
    appeal = relationship("Appeal", back_populates="detection")

    def to_dict(self):
        """Convert detection to dictionary format."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "score": self.score,
            "action": self.action,
            "status": self.status,
            "detected_at": self.detected_at.isoformat(),
            "reversed_at": self.reversed_at.isoformat() if self.reversed_at else None,
            "has_appeal": bool(self.appeal_id)
        }

class Appeal(Base):
    __tablename__ = 'dashboard_appeals'
    
    id = Column(Integer, primary_key=True)
    detection_id = Column(Integer, ForeignKey('dashboard_scammer_detections.id'), nullable=False)
    user_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    evidence = Column(JSON)  # Additional evidence provided by user
    status = Column(String, nullable=False, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey('dashboard_users.id'))
    
    # Relationships
    detection = relationship("ScammerDetection", back_populates="appeal")
    resolver = relationship("User", foreign_keys=[resolved_by])