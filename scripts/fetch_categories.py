
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# "Cases by Category" endpoint provided by user
# https://data.sfgov.org/api/v3/views/zd7k-pf58/query.json
ENDPOINT = "https://data.sfgov.org/resource/zd7k-pf58.json"

def fetch_categories():
    headers = {}
    token = os.getenv("SF_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
        
    try:
        # It seems to be a summary view, so fetching it directly gives rows
        response = requests.get(ENDPOINT, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print(f"Found {len(data)} categories:")
        for row in data:
            # Based on previous curl, keys are 'service_name' and 'service_request_id' (which looks like a count)
            name = row.get('service_name')
            count = row.get('service_request_id')
            print(f"- {name}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_categories()
