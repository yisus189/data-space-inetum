from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace')

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except (ImportError, SQLAlchemyError) as e:
    # If engine creation fails (e.g., in tests or when psycopg is not installed),
    # create a dummy engine. Tests will override get_db anyway.
    engine = None
    SessionLocal = None

def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database session not initialized. Ensure database drivers are installed and configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
