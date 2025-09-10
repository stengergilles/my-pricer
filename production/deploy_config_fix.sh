#!/bin/bash

# Deploy ConfigProvider fix to production
set -e

FRONTEND_DIR="../web/frontend"
DEPLOY_DIR="/opt/crypto-pricer/web/frontend/build"

echo "Building frontend..."
cd "$FRONTEND_DIR"
npm run build

echo "Deploying to production..."
sudo cp -r build/* "$DEPLOY_DIR/"

echo "ConfigProvider fix deployed successfully!"
