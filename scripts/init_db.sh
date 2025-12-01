#!/bin/bash
# Initialize database tables
# Run this after starting the database container

set -e

echo "Initializing database tables..."

# Wait for database to be ready
until pg_isready -h localhost -p 5432 -U dataspace_user -d dataspace 2>/dev/null; do
    echo "Waiting for database..."
    sleep 2
done

# Run Python script to create tables
python3 -c "
from src.models import init_db
print('Creating database tables...')
init_db()
print('Database initialized successfully!')
"

echo "Done!"
