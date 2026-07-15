#!/bin/bash

set -e

echo "Starting Luxury Price Miniapp API..."

if [ ! -f "database.db" ]; then
    echo "Initializing database..."
    python init_data.py
fi

uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
