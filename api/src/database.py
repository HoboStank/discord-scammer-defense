from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/dsd_db')

# Create engine
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create thread-safe session factory
Session = scoped_session(SessionLocal)

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize the database."""
    from models import Base
    Base.metadata.create_all(bind=engine)

def get_session():
    """Get a new database session."""
    return SessionLocal()