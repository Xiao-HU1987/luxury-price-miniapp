#!/bin/bash

set -e

echo "Starting Luxury Price Miniapp API..."

echo "Running database initialization (this may take a moment)..."
python init_data.py || {
  echo "WARNING: Database initialization failed, continuing with service startup..."
}

echo "Starting uvicorn server..."
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
