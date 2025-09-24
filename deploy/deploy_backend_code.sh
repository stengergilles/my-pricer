#!/bin/bash
#
set -x

# Determine the absolute path to the project root dynamically
# This script is in deploy/, so project root is one level up
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd -P)/.."
DEST_DIR="/opt/crypto-pricer/"
SERVICE_USER="crypto-pricer"

# Ensure destination exists
sudo mkdir -p "$DEST_DIR"

sudo rm -rf $DEST_DIR/*
sudo rsync -av "$SOURCE_DIR"/*.py "$DEST_DIR"/ || true
sudo rsync -av "$SOURCE_DIR"/*.pyx "$DEST_DIR"/ || true

# Recursively copy core and web/backend directories using rsync
sudo rsync -av "$SOURCE_DIR"/core/ "$DEST_DIR"/core/
sudo mkdir -p $DEST_DIR/web/backend
sudo rsync -av "$SOURCE_DIR"/web/backend/ "$DEST_DIR"/web/backend/

rm "$DEST_DIR"/web/backend/.env 
# Ensure all copied files are owned by the service user
sudo chown -R $SERVICE_USER:$SERVICE_USER "$DEST_DIR"

