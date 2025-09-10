#!/bin/bash

set -e

FRONTEND_DIR="../web/frontend"
DEPLOY_DIR="/var/www/my-pricer-frontend"
SECRETS_FILE="/etc/my-pricer/secrets/frontend.env"

echo "Building frontend..."
cd "$FRONTEND_DIR"

# Copy production secrets to .env.production
if sudo test -f "$SECRETS_FILE"; then
    sudo cp "$SECRETS_FILE" .env.production
    sudo chown $(whoami):$(whoami) .env.production
    echo "Using production secrets from $SECRETS_FILE"
else
    echo "Warning: Production secrets not found at $SECRETS_FILE"
fi

npm run build

echo "Deploying to production..."
sudo cp -r build/* "$DEPLOY_DIR/"

# Clean up
rm -f .env.production

echo "Frontend code deployed successfully!"
