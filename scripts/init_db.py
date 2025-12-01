#!/usr/bin/env python3
"""Initialize database schema."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db.session import engine, Base
from src.db.models import Provider, Dataset, DatasetVersion, AuditLog, Policy, Contract, ContractAgreement


def init_db():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
