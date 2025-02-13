from sqlalchemy import create_engine
import os

# Database configuration
DATABASE_URL = 'postgresql://postgres:postgres123@localhost:5432/dsd_db'

def init_db():
    # Import the models here to avoid circular imports
    from src.models import Base
    
    print("Creating database engine...")
    engine = create_engine(DATABASE_URL)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete!")

if __name__ == "__main__":
    init_db()