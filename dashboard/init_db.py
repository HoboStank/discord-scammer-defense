from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.models import Base

# Database URL - Change this based on your configuration
DATABASE_URL = "sqlite:///./dashboard.db"  # Using SQLite for development

def init_db():
    """Initialize the database, creating all tables."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    # Create a session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create a test session to verify connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()