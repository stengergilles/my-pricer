#!/bin/bash

# Determine the absolute path to the project root dynamically
# This script is in deploy/, so project root is one level up
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd -P)/.."
DEST_DIR="/opt/crypto-pricer/"

# Ensure destination exists
sudo mkdir -p "$DEST_DIR"

# Copy all necessary Python code
# Exclude development-only files/folders, frontend build artifacts, and the 'data' directory
sudo rsync -av --delete \
    --exclude '.git/' \
    --exclude '.github/' \
    --exclude '.ruff_cache/' \
    --exclude 'build/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude 'tests/' \
    --exclude 'web/frontend/' \
    --exclude 'data/' \
    --exclude '*.pyc' \
    --exclude '*.log' \
    --exclude '*.coverage' \
    --exclude '.env' \
    --exclude 'venv/' \
    "$SOURCE_DIR/" "$DEST_DIR"

# Restart production service (this will be called by deploy_backend.sh, so it's commented out here)
# sudo systemctl restart crypto-pricer