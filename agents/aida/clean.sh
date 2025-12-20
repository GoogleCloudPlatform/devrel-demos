#!/bin/bash
set -e

echo "Cleaning up project artifacts..."

# Remove databases
echo "Removing databases..."
rm -f schema.db packs.db

# Remove osquery data
echo "Removing osquery_data..."
rm -rf osquery_data

# Remove models (since we don't download them anymore)
echo "Removing models..."
rm -rf models

# Remove virtual environment
echo "Removing .venv..."
rm -rf .venv

# Remove pycache
echo "Removing __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "Cleanup complete. You can now run ./setup.sh"
