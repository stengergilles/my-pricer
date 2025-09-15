#!/bin/bash

# Production deployment script for crypto trading system backend
set -e

APP_NAME="crypto-pricer"
DEPLOY_DIR="/opt/$APP_NAME"
SERVICE_USER="$APP_NAME"
PYTHON_VERSION="3.12"

echo "Deploying $APP_NAME backend to production..."

# Create service user
sudo useradd -r -s /bin/false $SERVICE_USER 2>/dev/null || true

# Call the dedicated code deployment script
sudo "$(dirname "$0")"/deploy_backend_code.sh
# Create deployment directory
sudo chown -R $SERVICE_USER:$SERVICE_USER $DEPLOY_DIR

# Copy the master startup script
sudo cp "$(dirname "$0")/start.sh" "$DEPLOY_DIR/start.sh"
sudo chmod +x "$DEPLOY_DIR/start.sh"
sudo chown $SERVICE_USER:$SERVICE_USER "$DEPLOY_DIR/start.sh"

# Link backend environment file if it doesn't exist
if [ ! -e "$DEPLOY_DIR/web/backend/.env" ]; then
    sudo ln -s /etc/my-pricer/secrets/backend.env $DEPLOY_DIR/web/backend/.env
fi

# Install Python dependencies
cd $DEPLOY_DIR
sudo -u $SERVICE_USER python$PYTHON_VERSION -m venv venv
sudo -u $SERVICE_USER ./venv/bin/pip install -r requirements.txt

# Build cython module
sudo -u $SERVICE_USER ./venv/bin/python setup.py build_ext --inplace

# Create a single systemd service for the entire application
sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null <<EOF
[Unit]
Description=Crypto Trading System Backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$DEPLOY_DIR
ExecStart=$DEPLOY_DIR/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Stop old services if they exist
sudo systemctl stop $APP_NAME-scheduler 2>/dev/null || true
sudo systemctl stop $APP_NAME-paper-trader 2>/dev/null || true
sudo systemctl disable $APP_NAME-scheduler 2>/dev/null || true
sudo systemctl disable $APP_NAME-paper-trader 2>/dev/null || true


# Enable and start the new single service
sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl restart $APP_NAME

echo "Backend deployed successfully to $DEPLOY_DIR"
echo "Service status: $(sudo systemctl is-active $APP_NAME)"
