#!/bin/bash

# Master startup script for the crypto trading system.
# Runs the application using the Flask development server, which is expected to start all services.

set -e

DEPLOY_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$DEPLOY_DIR"

echo "🚀 Starting crypto trading system..."

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
else
    echo "Virtual environment not found. Please run the deployment script first."
    exit 1
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$DEPLOY_DIR"

# Set the port for the Flask application
export API_PORT=5001

# Navigate to the backend directory
cd "web/backend"

echo "Launching Flask backend (which starts all services) on port $API_PORT..."
# Execute the Flask application. This is expected to start all services.
python -u app.py > /tmp/start.log
