from sqlalchemy import create_engine
import sys

DATABASE_URL = 'postgresql://postgres:postgres123@localhost:5432/dsd_db'

def test_connection():
    try:
        print("Testing database connection...")
        engine = create_engine(DATABASE_URL)
        connection = engine.connect()
        print("Successfully connected to the database!")
        connection.close()
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)