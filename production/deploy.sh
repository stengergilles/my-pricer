#!/bin/bash

# Enable required Apache modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Install certbot if not present
sudo apt update
sudo apt install -y certbot python3-certbot-apache

# Create HTTP-only configs first (remove SSL sections)
sudo cp frontend.conf /etc/apache2/sites-available/frontend-temp.conf
sudo cp backend.conf /etc/apache2/sites-available/backend-temp.conf

# Remove SSL sections from temp configs
sudo sed -i '/<VirtualHost \*:443>/,/<\/VirtualHost>/d' /etc/apache2/sites-available/frontend-temp.conf
sudo sed -i '/<VirtualHost \*:443>/,/<\/VirtualHost>/d' /etc/apache2/sites-available/backend-temp.conf

# Enable HTTP-only sites temporarily
sudo a2ensite frontend-temp.conf
sudo a2ensite backend-temp.conf

# Test config and reload
sudo apache2ctl configtest && sudo systemctl reload apache2

# Get SSL certificates (certbot will create new SSL configs)
sudo certbot --apache -d my-pricer.gillesstenger.fr --non-interactive --agree-tos --email admin@gillesstenger.fr
sudo certbot --apache -d my-pricer-api.gillesstenger.fr --non-interactive --agree-tos --email admin@gillesstenger.fr

# Disable temp configs and enable the SSL ones created by certbot
sudo a2dissite frontend-temp.conf
sudo a2dissite backend-temp.conf
sudo rm /etc/apache2/sites-available/frontend-temp.conf
sudo rm /etc/apache2/sites-available/backend-temp.conf

# Create frontend directory
sudo mkdir -p /var/www/my-pricer-frontend

# Build and copy frontend
cd ../web/frontend
# Copy production env file for build-time injection
sudo cp /etc/my-pricer/secrets/frontend.env .env.local
# Build React app (env vars get baked into static files)
npm run build
# Remove existing files and copy built static files to Apache document root
sudo rm -rf /var/www/my-pricer-frontend/*
sudo cp -r build/* /var/www/my-pricer-frontend/ 2>/dev/null || sudo rsync -av build/ /var/www/my-pricer-frontend/
# Clean up env file from source
rm -f .env.local

# Set permissions
sudo chown -R www-data:www-data /var/www/my-pricer-frontend

# Test configuration and reload
sudo apache2ctl configtest
sudo systemctl reload apache2

echo "Production environment configured!"
echo "Frontend: https://my-pricer.gillesstenger.fr"
echo "Backend: https://my-pricer-api.gillesstenger.fr"
