from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import models
from database import get_db, init_db
from datetime import datetime
import uvicorn
from pydantic import BaseModel

app = FastAPI(title="Discord Scammer Defense API")

# Pydantic models for request/response
class ScammerCreate(BaseModel):
    discord_id: str
    username: str
    detection_score: float
    detection_reasons: dict
    profile_data: Optional[dict] = None
    avatar_hash: Optional[str] = None

class ScammerResponse(BaseModel):
    discord_id: str
    username: str
    first_detected: datetime
    detection_score: float
    detection_reasons: dict
    
    class Config:
        orm_mode = True

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()

@app.get("/")
async def root():
    """API root endpoint."""
    return {"message": "Discord Scammer Defense API"}

@app.post("/scammers/", response_model=ScammerResponse)
async def create_scammer(scammer: ScammerCreate, db: Session = Depends(get_db)):
    """Create a new scammer profile."""
    db_scammer = models.ScammerProfile(
        discord_id=scammer.discord_id,
        username=scammer.username,
        detection_score=scammer.detection_score,
        detection_reasons=scammer.detection_reasons,
        profile_data=scammer.profile_data,
        avatar_hash=scammer.avatar_hash
    )
    
    try:
        db.add(db_scammer)
        db.commit()
        db.refresh(db_scammer)
        return db_scammer
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/scammers/{discord_id}", response_model=ScammerResponse)
async def get_scammer(discord_id: str, db: Session = Depends(get_db)):
    """Get a scammer profile by Discord ID."""
    scammer = db.query(models.ScammerProfile).filter(
        models.ScammerProfile.discord_id == discord_id
    ).first()
    
    if not scammer:
        raise HTTPException(status_code=404, detail="Scammer not found")
    return scammer

@app.get("/scammers/", response_model=List[ScammerResponse])
async def list_scammers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List scammer profiles with pagination."""
    scammers = db.query(models.ScammerProfile).offset(skip).limit(limit).all()
    return scammers

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )