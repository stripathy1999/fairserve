import sys
import os
import requests
import random
import json
import datetime
from dotenv import load_dotenv

# Add parent dir to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from intake.config import API_ENDPOINT, API_APP_TOKEN

def  get_random_incident():
    load_dotenv()
    
    headers = {}
    if API_APP_TOKEN:
        headers["X-App-Token"] = API_APP_TOKEN

    # Fetch recent data (last 7 days to ensure we get something)
    # We want a random sample, so we'll fetch a batch of recent ones and pick one.
    limit = 50
    params = {
        "$limit": limit,
        "$order": "requested_datetime DESC"
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("No data found from API.")
            return

        # Pick random
        choice = random.choice(data)
        
        print(json.dumps(choice, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_random_incident()
