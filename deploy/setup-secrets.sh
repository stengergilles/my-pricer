#!/bin/bash

# Create secure directory for production secrets
sudo mkdir -p /etc/my-pricer/secrets
sudo chmod 700 /etc/my-pricer/secrets

# Create production backend .env
sudo tee /etc/my-pricer/secrets/backend.env > /dev/null << 'EOF'
AUTH0_DOMAIN=your-production-auth0-domain.auth0.com
AUTH0_API_AUDIENCE=https://my-pricer-api.gillesstenger.fr
AUTH0_CLIENT_ID=your_production_backend_client_id
AUTH0_CLIENT_SECRET=your_production_backend_client_secret
FRONTEND_URL=https://my-pricer.gillesstenger.fr
EOF

# Create production frontend .env.local
sudo tee /etc/my-pricer/secrets/frontend.env > /dev/null << 'EOF'
REACT_APP_AUTH0_DOMAIN=your-production-auth0-domain.auth0.com
REACT_APP_AUTH0_CLIENT_ID=your_production_frontend_client_id
REACT_APP_AUTH0_AUDIENCE=https://my-pricer-api.gillesstenger.fr
REACT_APP_API_URL=https://my-pricer-api.gillesstenger.fr
EOF

# Set secure permissions
sudo chown -R www-data:www-data /etc/my-pricer/secrets
sudo chmod 600 /etc/my-pricer/secrets/backend.env /etc/my-pricer/secrets/frontend.env

echo "Edit the secret files with your production values:"
echo "sudo nano /etc/my-pricer/secrets/backend.env"
echo "sudo nano /etc/my-pricer/secrets/frontend.env"
