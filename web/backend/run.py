#!/usr/bin/env python3
"""
Development server runner for Crypto Trading Backend.
"""

import os
import sys
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='apscheduler')

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("🚀 Starting Crypto Trading Backend...")
    print(f"🔐 Auth0 Domain: {os.getenv('AUTH0_DOMAIN', 'Not configured')}")
    print(f"🎯 API Audience: {os.getenv('AUTH0_API_AUDIENCE', 'Not configured')}")
    print(f"🌐 Frontend URL: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}")
    print("📡 Server starting on http://localhost:5000")
    print("📋 Health check: http://localhost:5000/api/health")
    print("🔐 Auth test: http://localhost:5000/api/auth/test")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
