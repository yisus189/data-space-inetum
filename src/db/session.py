from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace')

# Only create engine if not in test mode (tests will override this)
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except (ImportError, SQLAlchemyError) as e:
    # In tests or when psycopg is not available, use a dummy sessionmaker
    # Tests will override get_db anyway
    engine = None
    SessionLocal = None

def get_db():
    if SessionLocal is None:
        # Tests should override this
        raise RuntimeError("Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
