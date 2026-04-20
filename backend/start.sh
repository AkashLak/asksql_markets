#!/bin/bash
set -e

if [ ! -f data/markets.db ]; then
  echo "Downloading markets.db from release asset..."
  curl -L "$DB_DOWNLOAD_URL" -o data/markets.db
  echo "Download complete."
fi

uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
