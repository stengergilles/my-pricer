import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Auth0 Configuration (GET THESE FROM YOUR AUTH0 DASHBOARD) ---
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN") # e.g., "your-tenant.us.auth0.com"
AUTH0_M2M_CLIENT_ID = os.getenv("AUTH0_M2M_CLIENT_ID") # Client ID of your Machine to Machine application
AUTH0_M2M_CLIENT_SECRET = os.getenv("AUTH0_M2M_CLIENT_SECRET") # Client Secret of your Machine to Machine application
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE") # Identifier of your API in Auth0, e.g., "https://my-pricer-api"

# --- Your Backend API Configuration ---
BASE_URL = "http://localhost:5000/api/scheduler" # Your backend scheduler API base URL

def get_auth0_token():
    """Acquires an OAuth2 token from Auth0 using the Client Credentials Grant."""
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    headers = {"content-type": "application/json"}
    payload = {
        "client_id": AUTH0_M2M_CLIENT_ID,
        "client_secret": AUTH0_M2M_CLIENT_SECRET,
        "audience": AUTH0_API_AUDIENCE,
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(token_url, headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for HTTP errors
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error acquiring Auth0 token: {e}")
        return None

def clear_all_scheduler_jobs():
    """Clears all scheduled jobs from the backend scheduler."""
    token = get_auth0_token()
    if not token:
        print("Failed to acquire Auth0 token. Cannot clear jobs.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Get all jobs
        response = requests.get(f"{BASE_URL}/jobs", headers=headers)
        response.raise_for_status()
        jobs = response.json()

        if not jobs:
            print("No jobs to clear.")
            return

        print(f"Found {len(jobs)} jobs to clear.")
        for job in jobs:
            job_id = job['id']
            print(f"Deleting job: {job_id}")
            delete_response = requests.delete(f"{BASE_URL}/jobs/{job_id}", headers=headers)
            delete_response.raise_for_status()
            print(f"Job {job_id} deleted successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error clearing jobs: {e}")

if __name__ == "__main__":
    # Check if Auth0 environment variables are set
    if not all([AUTH0_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET, AUTH0_API_AUDIENCE]):
        print("Auth0 environment variables (AUTH0_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET, AUTH0_API_AUDIENCE) are not set.")
        print("Please configure them in your .env file or as system environment variables.")
    else:
        clear_all_scheduler_jobs()