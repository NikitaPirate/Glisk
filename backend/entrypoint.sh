#!/bin/bash
set -e

echo "Starting GLISK Backend..."

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-glisk}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is ready!"

# Run database migrations
# Alembic has built-in locking via alembic_version table
# Multiple containers can safely run this - only one will execute migrations
echo "Running database migrations..."
uv run alembic upgrade head

echo "Migrations complete!"

# Get port from environment variable or use default
PORT=${PORT:-8000}

# Start the application
echo "Starting FastAPI application on port $PORT..."
exec uv run uvicorn glisk.app:app --host 0.0.0.0 --port $PORT
