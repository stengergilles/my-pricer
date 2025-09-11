#!/bin/bash

# Copy backend code to production
sudo rsync -av --delete web/backend/ /opt/crypto-pricer/backend/
sudo rsync -av --delete core/ /opt/crypto-pricer/core/

# Restart production service
sudo systemctl restart crypto-pricer 
