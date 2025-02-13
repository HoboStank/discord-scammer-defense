from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..models import UserSession, ScammerDetection, ServerStats
import logging

logger = logging.getLogger(__name__)

class DatabaseCleaner:
    def __init__(self, db: Session):
        self.db = db

    def cleanup_expired_sessions(self) -> int:
        """Remove expired user sessions."""
        try:
            result = self.db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            self.db.commit()
            return result
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            self.db.rollback()
            return 0

    def aggregate_old_stats(self, days: int = 90) -> bool:
        """Aggregate old statistics data to maintain performance."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Aggregate old detection data
            old_detections = (
                self.db.query(ScammerDetection)
                .filter(ScammerDetection.detected_at < cutoff_date)
                .all()
            )

            for guild_id in set(d.guild_id for d in old_detections):
                guild_detections = [d for d in old_detections if d.guild_id == guild_id]
                
                stats = self.db.query(ServerStats).filter_by(guild_id=guild_id).first()
                if not stats:
                    stats = ServerStats(guild_id=guild_id)
                    self.db.add(stats)

                # Update aggregated statistics
                total_detections = len(guild_detections)
                false_positives = len([d for d in guild_detections if d.status == 'reversed'])
                
                action_counts = {'warns': 0, 'kicks': 0, 'bans': 0}
                for detection in guild_detections:
                    action_counts[detection.action] = action_counts.get(detection.action, 0) + 1

                # Store aggregated data
                stats.total_scans += total_detections
                stats.detected_scammers += total_detections
                stats.false_positives += false_positives
                
                if not stats.actions_taken:
                    stats.actions_taken = action_counts
                else:
                    for action, count in action_counts.items():
                        stats.actions_taken[action] = stats.actions_taken.get(action, 0) + count

            # Remove aggregated detections
            self.db.query(ScammerDetection).filter(
                ScammerDetection.detected_at < cutoff_date,
                ScammerDetection.status.in_(['active', 'reversed'])  # Keep appealed detections
            ).delete()

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error aggregating old stats: {e}")
            self.db.rollback()
            return False

    def run_maintenance(self):
        """Run all maintenance tasks."""
        logger.info("Starting database maintenance...")
        
        cleaned_sessions = self.cleanup_expired_sessions()
        logger.info(f"Cleaned up {cleaned_sessions} expired sessions")
        
        if self.aggregate_old_stats():
            logger.info("Successfully aggregated old statistics")
        else:
            logger.error("Failed to aggregate old statistics")