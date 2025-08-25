#!/bin/bash
#
# Sets the FRONTEND_URL environment variable and launches the Flask backend.
# Usage: ./run_backend.sh [YOUR_FRONTEND_URL]
# Example: ./run_backend.sh http://192.168.1.5:3000
# Default FRONTEND_URL: http://localhost:3000
#
# Note: This script assumes you are running it from the web/backend/ directory.

DEFAULT_FRONTEND_URL="http://localhost:3000"

# Set FRONTEND_URL
if [ -z "$1" ]; then
  export FRONTEND_URL="$DEFAULT_FRONTEND_URL"
  echo "FRONTEND_URL set to default: $FRONTEND_URL"
else
  export FRONTEND_URL="$1"
  echo "FRONTEND_URL set to: $FRONTEND_URL"
fi

# Navigate to the backend directory (if not already there)
# This is important because app.py might rely on relative paths
# from its own location.
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR" || exit

echo "Launching Flask backend..."
# Execute the Flask application
# Using python -u for unbuffered output, useful for logging
exec python -u app.py
