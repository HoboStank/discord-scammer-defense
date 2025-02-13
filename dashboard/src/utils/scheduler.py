import asyncio
import aioschedule
from datetime import datetime
from sqlalchemy.orm import Session
from .maintenance import DatabaseCleaner
from ..models import get_db
import logging

logger = logging.getLogger(__name__)

async def run_scheduled_maintenance():
    """Run maintenance tasks on a schedule."""
    try:
        db = next(get_db())
        cleaner = DatabaseCleaner(db)
        cleaner.run_maintenance()
    except Exception as e:
        logger.error(f"Error during scheduled maintenance: {e}")
    finally:
        db.close()

async def schedule_maintenance():
    """Schedule maintenance tasks."""
    # Run maintenance daily at 3 AM
    aioschedule.every().day.at("03:00").do(run_scheduled_maintenance)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(3600)  # Check every hour

async def start_maintenance_scheduler():
    """Start the maintenance scheduler."""
    asyncio.create_task(schedule_maintenance())