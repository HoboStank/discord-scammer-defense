from fastapi import FastAPI, Request, Depends, HTTPException, Response, Body, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Union
from .models import Base, User, ServerStats, AuditLog, DashboardConfig, ScammerDetection
from .auth import Auth, get_current_user
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import json
from .utils.webhook import WebhookNotifier
import os
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from .utils.scheduler import start_maintenance_scheduler

app = FastAPI(title="Discord Scammer Defense Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./dashboard.db"  # Configure as needed
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Add webhook configuration
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
webhook = WebhookNotifier(WEBHOOK_URL) if WEBHOOK_URL else None

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the application starts."""
    await start_maintenance_scheduler()

@app.get("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Show login page with Discord OAuth button."""
    auth = Auth(db)
    oauth_url = auth.create_discord_oauth_url()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login", "oauth_url": oauth_url}
    )

@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Discord OAuth callback."""
    auth = Auth(db)
    
    try:
        # Exchange code for token
        token_data = await auth.exchange_code(code)
        if "error" in token_data:
            raise HTTPException(status_code=400, detail="Failed to authenticate")

        # Get user info from Discord
        user_info = await auth.get_user_info(token_data["access_token"])
        
        # Create or update user
        user = db.query(User).filter_by(discord_id=user_info["id"]).first()
        if not user:
            user = User(
                discord_id=user_info["id"],
                username=user_info["username"],
                email=user_info.get("email"),
                avatar_url=f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}.png"
                if user_info.get("avatar") else None
            )
            db.add(user)
            db.commit()

        # Create session
        session_token = auth.create_session(user.id)
        
        # Set session cookie and redirect
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=True,  # Set to True in production
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        return response

    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login",
                "error": "Authentication failed. Please try again."
            }
        )

@app.get("/logout")
async def logout(response: Response):
    """Log out user by clearing session cookie."""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="session")
    return response

# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Require authentication for all routes except login and auth."""
    public_paths = {"/login", "/auth/callback", "/static"}
    if not any(request.url.path.startswith(path) for path in public_paths):
        user = await get_current_user(request, next(get_db()))
        if not user:
            return RedirectResponse(url="/login")
    return await call_next(request)

@app.get("/")
async def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Render the dashboard home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Dashboard"}
    )

@app.get("/stats")
async def server_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Show server statistics page with detailed analytics."""
    # Get server stats for different time periods for trend calculation
    current_period = datetime.utcnow() - timedelta(days=30)
    previous_period = current_period - timedelta(days=30)
    
    current_stats = db.query(ServerStats).filter(
        ServerStats.last_updated >= current_period
    ).first()

    previous_stats = db.query(ServerStats).filter(
        ServerStats.last_updated >= previous_period,
        ServerStats.last_updated < current_period
    ).first()

    # Calculate trends
    if current_stats and previous_stats:
        stats = {
            'total_scans': current_stats.total_scans,
            'detected_scammers': current_stats.detected_scammers,
            'false_positives': current_stats.false_positives,
            'accuracy_rate': (
                (current_stats.detected_scammers - current_stats.false_positives) / 
                current_stats.detected_scammers * 100 if current_stats.detected_scammers > 0 else 0
            ),
            'actions': current_stats.actions_taken or {'warns': 0, 'kicks': 0, 'bans': 0},
            'scan_trend': calculate_trend(current_stats.total_scans, previous_stats.total_scans),
            'scammer_trend': calculate_trend(current_stats.detected_scammers, previous_stats.detected_scammers),
            'false_positive_trend': calculate_trend(current_stats.false_positives, previous_stats.false_positives),
            'accuracy_trend': calculate_trend(
                (current_stats.detected_scammers - current_stats.false_positives) / current_stats.detected_scammers * 100 if current_stats.detected_scammers > 0 else 0,
                (previous_stats.detected_scammers - previous_stats.false_positives) / previous_stats.detected_scammers * 100 if previous_stats.detected_scammers > 0 else 0
            )
        }
    else:
        stats = create_default_stats()

    # Prepare detection trend data (last 7 days)
    detection_trend_data = {
        'labels': [],
        'datasets': [
            {
                'label': 'Detections',
                'data': [],
                'borderColor': '#5865F2',
                'tension': 0.1,
                'fill': False
            },
            {
                'label': 'False Positives',
                'data': [],
                'borderColor': '#ED4245',
                'tension': 0.1,
                'fill': False
            }
        ]
    }
    
    # Get daily stats for the last 7 days
    for i in range(7, 0, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        detection_trend_data['labels'].append(date_str)
        
        daily_stats = get_daily_stats(db, date)
        detection_trend_data['datasets'][0]['data'].append(daily_stats['detections'])
        detection_trend_data['datasets'][1]['data'].append(daily_stats['false_positives'])

    # Prepare action distribution data
    action_distribution_data = {
        'labels': ['Warnings', 'Kicks', 'Bans'],
        'datasets': [{
            'data': [
                stats['actions']['warns'],
                stats['actions']['kicks'],
                stats['actions']['bans']
            ],
            'backgroundColor': ['#FEE75C', '#5865F2', '#ED4245']
        }]
    }

    # Prepare hourly activity data
    hourly_activity = get_hourly_activity(db)
    hourly_activity_data = {
        'labels': [f"{h:02d}:00" for h in range(24)],
        'datasets': [{
            'data': [hourly_activity.get(h, 0) for h in range(24)],
            'backgroundColor': '#5865F2'
        }]
    }

    # Prepare score distribution data
    score_ranges = [
        (0, 0.2), (0.2, 0.4), (0.4, 0.6),
        (0.6, 0.8), (0.8, 0.9), (0.9, 1.0)
    ]
    score_distribution = get_score_distribution(db, score_ranges)
    score_distribution_data = {
        'labels': [f"{start:.1f}-{end:.1f}" for start, end in score_ranges],
        'datasets': [{
            'data': [score_distribution.get(f"{start:.1f}-{end:.1f}", 0) for start, end in score_ranges],
            'backgroundColor': '#5865F2'
        }]
    }

    # Get recent detections
    recent_detections = (
        db.query(ScammerDetection)
        .order_by(ScammerDetection.detected_at.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "title": "Statistics",
            "stats": stats,
            "detection_trend_data": detection_trend_data,
            "action_distribution_data": action_distribution_data,
            "hourly_activity_data": hourly_activity_data,
            "score_distribution_data": score_distribution_data,
            "recent_detections": recent_detections
        }
    )

def calculate_trend(current: float, previous: float) -> float:
    """Calculate percentage change between two periods."""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100

def create_default_stats() -> dict:
    """Create default stats structure."""
    return {
        'total_scans': 0,
        'detected_scammers': 0,
        'false_positives': 0,
        'accuracy_rate': 0,
        'actions': {'warns': 0, 'kicks': 0, 'bans': 0},
        'scan_trend': 0,
        'scammer_trend': 0,
        'false_positive_trend': 0,
        'accuracy_trend': 0
    }

def get_daily_stats(db: Session, date: datetime) -> dict:
    """Get statistics for a specific day."""
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    
    detections = db.query(ScammerDetection).filter(
        ScammerDetection.detected_at >= start,
        ScammerDetection.detected_at < end
    ).count()
    
    false_positives = db.query(ScammerDetection).filter(
        ScammerDetection.detected_at >= start,
        ScammerDetection.detected_at < end,
        ScammerDetection.status == 'reversed'
    ).count()
    
    return {
        'detections': detections,
        'false_positives': false_positives
    }

def get_hourly_activity(db: Session) -> dict:
    """Get detection counts grouped by hour."""
    hourly_counts = {}
    detections = db.query(ScammerDetection).filter(
        ScammerDetection.detected_at >= datetime.utcnow() - timedelta(days=7)
    ).all()
    
    for detection in detections:
        hour = detection.detected_at.hour
        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
    
    return hourly_counts

def get_score_distribution(db: Session, ranges: list) -> dict:
    """Get distribution of detection scores."""
    distribution = {}
    detections = db.query(ScammerDetection).filter(
        ScammerDetection.detected_at >= datetime.utcnow() - timedelta(days=30)
    ).all()
    
    for detection in detections:
        for start, end in ranges:
            range_key = f"{start:.1f}-{end:.1f}"
            if start <= detection.score < end:
                distribution[range_key] = distribution.get(range_key, 0) + 1
                break
    
    return distribution

@app.get("/config")
async def server_config(request: Request):
    """Show server configuration page."""
    return templates.TemplateResponse(
        "config.html",
        {"request": request, "title": "Configuration"}
    )

@app.get("/scammers")
async def scammer_list(request: Request):
    """Show list of detected scammers."""
    return templates.TemplateResponse(
        "scammers.html",
        {"request": request, "title": "Scammer List"}
    )

@app.get("/appeals")
async def appeal_management(
    request: Request,
    status: str = Query("pending", regex="^(all|pending|approved|rejected)$"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Show appeal management page."""
    if not current_user:
        return RedirectResponse(url="/login")

    # Build base query
    query = db.query(Appeal).order_by(Appeal.created_at.desc())

    # Apply status filter
    if status != "all":
        query = query.filter(Appeal.status == status)

    # Apply search filter
    if search:
        query = query.join(ScammerDetection).filter(
            ScammerDetection.username.ilike(f"%{search}%") |
            Appeal.user_id.ilike(f"%{search}%")
        )

    # Get total count for pagination
    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size

    # Get paginated appeals
    appeals = query.offset((page - 1) * page_size).limit(page_size).all()

    return templates.TemplateResponse(
        "appeals.html",
        {
            "request": request,
            "title": "Appeals",
            "appeals": appeals,
            "page": page,
            "total_pages": total_pages,
            "status": status
        }
    )

class ConfigUpdate(BaseModel):
    min_detection_score: float
    enabled_checks: List[str]
    warn_threshold: float
    kick_threshold: float
    ban_threshold: float
    alert_channel: Optional[str]
    log_channel: Optional[str]
    trusted_roles: List[str]
    immune_roles: List[str]

@app.post("/api/config/save")
async def save_config(
    request: Request,
    config: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save server configuration changes."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Convert to format expected by server_config
        formatted_config = {
            "min_detection_score": config.min_detection_score,
            "enabled_checks": config.enabled_checks,
            "auto_actions": {
                "warn": config.warn_threshold,
                "kick": config.kick_threshold,
                "ban": config.ban_threshold
            },
            "alert_channel": config.alert_channel,
            "log_channel": config.log_channel,
            "trusted_roles": config.trusted_roles,
            "immune_roles": config.immune_roles
        }
        
        # Save to database
        dashboard_config = db.query(DashboardConfig).filter_by(
            guild_id=request.query_params.get("guild_id")
        ).first()
        
        if dashboard_config:
            for key, value in formatted_config.items():
                setattr(dashboard_config, key, value)
        else:
            dashboard_config = DashboardConfig(
                guild_id=request.query_params.get("guild_id"),
                **formatted_config
            )
            db.add(dashboard_config)
        
        # Log the configuration change
        audit_log = AuditLog(
            user_id=current_user.id,
            action="config_update",
            details={"changes": formatted_config}
        )
        db.add(audit_log)
        
        # Send webhook notification for config changes
        if webhook:
            embed = webhook.create_config_update_embed(
                guild_id=request.query_params.get("guild_id"),
                changes=formatted_config,
                user=current_user
            )
            await webhook.send_notification(embed)
        
        db.commit()
        return JSONResponse({"status": "success"})
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/{guild_id}")
async def get_config(
    guild_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get server configuration."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    config = db.query(DashboardConfig).filter_by(guild_id=guild_id).first()
    if not config:
        # Return default configuration
        return {
            "min_detection_score": 0.7,
            "enabled_checks": ["username", "avatar", "profile"],
            "auto_actions": {
                "warn": 0.7,
                "kick": 0.85,
                "ban": 0.95
            },
            "alert_channel": None,
            "log_channel": None,
            "trusted_roles": [],
            "immune_roles": []
        }
    
    return config.to_dict()

@app.get("/api/scammers")
async def get_scammers(
    request: Request,
    time_filter: str = Query("30d", regex="^(24h|7d|30d|all)$"),
    status: str = Query("all", regex="^(all|active|appealed|reversed)$"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of detected scammers with filtering and pagination."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Build base query
    query = db.query(ScammerDetection).order_by(ScammerDetection.detected_at.desc())

    # Apply time filter
    if time_filter != "all":
        time_deltas = {
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        if time_filter in time_deltas:
            query = query.filter(
                ScammerDetection.detected_at >= datetime.utcnow() - time_deltas[time_filter]
            )

    # Apply status filter
    if status != "all":
        query = query.filter(ScammerDetection.status == status)

    # Apply search filter
    if search:
        query = query.filter(
            ScammerDetection.username.ilike(f"%{search}%") |
            ScammerDetection.user_id.ilike(f"%{search}%")
        )

    # Get total count for pagination
    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size

    # Apply pagination
    scammers = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "scammers": [s.to_dict() for s in scammers],
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count
    }

@app.get("/api/scammers/{user_id}/evidence")
async def get_scammer_evidence(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed evidence for a specific scammer detection."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    detection = db.query(ScammerDetection).filter_by(user_id=user_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    return {
        "user_id": detection.user_id,
        "detected_at": detection.detected_at,
        "score": detection.score,
        "triggered_checks": detection.check_results,
        "screenshot": detection.evidence_screenshot,
        "action_taken": detection.action,
        "status": detection.status
    }

@app.post("/api/scammers/{user_id}/reverse")
async def reverse_action(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reverse a scammer detection action."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    detection = db.query(ScammerDetection).filter_by(user_id=user_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    if detection.status != "active":
        raise HTTPException(status_code=400, detail="Can only reverse active detections")

    try:
        # Update detection status
        detection.status = "reversed"
        detection.reversed_at = datetime.utcnow()
        detection.reversed_by = current_user.id

        # Log the reversal
        audit_log = AuditLog(
            user_id=current_user.id,
            action="reverse_detection",
            details={
                "scammer_id": user_id,
                "original_action": detection.action,
                "reason": "Manual reversal by admin"
            }
        )
        db.add(audit_log)
        
        # Send webhook notification
        if webhook:
            embed = webhook.create_reversal_embed(
                detection=detection,
                reverser=current_user,
                reason="Manual reversal by admin"
            )
            await webhook.send_notification(embed)
        
        db.commit()
        return {"status": "success", "message": "Action reversed successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/appeals/{appeal_id}/approve")
async def approve_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve an appeal and reverse the associated detection."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    appeal = db.query(Appeal).filter_by(id=appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")

    if appeal.status != "pending":
        raise HTTPException(status_code=400, detail="Can only handle pending appeals")

    try:
        # Update appeal status
        appeal.status = "approved"
        appeal.resolved_at = datetime.utcnow()
        appeal.resolved_by = current_user.id

        # Update detection status
        detection = appeal.detection
        detection.status = "reversed"
        detection.reversed_at = datetime.utcnow()
        detection.reversed_by = current_user.id

        # Create audit log entry
        audit_log = AuditLog(
            user_id=current_user.id,
            action="approve_appeal",
            details={
                "appeal_id": appeal_id,
                "detection_id": detection.id,
                "user_id": appeal.user_id
            }
        )
        db.add(audit_log)

        # Send webhook notification
        if webhook:
            embed = webhook.create_appeal_embed(appeal, "approved")
            await webhook.send_notification(embed)
        
        db.commit()
        return {"status": "success", "message": "Appeal approved successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/appeals/{appeal_id}/reject")
async def reject_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an appeal."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    appeal = db.query(Appeal).filter_by(id=appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")

    if appeal.status != "pending":
        raise HTTPException(status_code=400, detail="Can only handle pending appeals")

    try:
        # Update appeal status
        appeal.status = "rejected"
        appeal.resolved_at = datetime.utcnow()
        appeal.resolved_by = current_user.id

        # Create audit log entry
        audit_log = AuditLog(
            user_id=current_user.id,
            action="reject_appeal",
            details={
                "appeal_id": appeal_id,
                "detection_id": appeal.detection.id,
                "user_id": appeal.user_id
            }
        )
        db.add(audit_log)

        # Send webhook notification
        if webhook:
            embed = webhook.create_appeal_embed(appeal, "rejected")
            await webhook.send_notification(embed)
        
        db.commit()
        return {"status": "success", "message": "Appeal rejected successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class DetectionUpdate(BaseModel):
    user_id: str
    username: str
    avatar_url: Optional[str]
    guild_id: str
    score: float
    action: str
    check_results: Dict[str, Any]
    evidence_screenshot: Optional[str]

@app.post("/api/detections/new")
async def record_detection(
    detection: DetectionUpdate,
    db: Session = Depends(get_db)
):
    """Record a new scammer detection from the bot."""
    try:
        # Create new detection record
        new_detection = ScammerDetection(
            user_id=detection.user_id,
            username=detection.username,
            avatar_url=detection.avatar_url,
            guild_id=detection.guild_id,
            score=detection.score,
            action=detection.action,
            check_results=detection.check_results,
            evidence_screenshot=detection.evidence_screenshot
        )
        db.add(new_detection)

        # Update server stats
        stats = db.query(ServerStats).filter_by(guild_id=detection.guild_id).first()
        if not stats:
            stats = ServerStats(guild_id=detection.guild_id)
            db.add(stats)

        stats.total_scans += 1
        stats.detected_scammers += 1
        if detection.score > stats.avg_detection_score:
            stats.avg_detection_score = (stats.avg_detection_score + detection.score) / 2

        # Update action counts
        if not stats.actions_taken:
            stats.actions_taken = {'warns': 0, 'kicks': 0, 'bans': 0}
        stats.actions_taken[detection.action] = stats.actions_taken.get(detection.action, 0) + 1

        # Send webhook notification
        if webhook:
            embed = webhook.create_detection_embed(new_detection)
            await webhook.send_notification(embed)

        db.commit()
        return {"status": "success", "detection_id": new_detection.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)