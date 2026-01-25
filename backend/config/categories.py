import requests
import os
import datetime
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
SF_DATA_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN")
# Primary: SODA 3 Filtered View (Dynamic)
API_URL_PRIMARY = "https://data.sfgov.org/api/v3/views/zd7k-pf58/query.json"

# In-memory cache
_CACHED_CATEGORIES = []
_LAST_FETCH_TIME = None
CACHE_DURATION_HOURS = 24

def fetch_categories_from_api():
    """
    Fetches categories from SFGov API.
    Tries primary URL (SODA 3) first, then fallback (SODA 2).
    """
    headers = {
        "User-Agent": "FairServe/1.0",
        "Accept": "application/json"
    }
    if SF_DATA_APP_TOKEN:
        headers["X-App-Token"] = SF_DATA_APP_TOKEN
        
    # Try Primary
    try:
        print(f"Fetching categories from {API_URL_PRIMARY}...")
        response = requests.get(API_URL_PRIMARY, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # SODA 3 'query.json' often returns list of rows directly or a specific structure
            # Based on user info, this is a view. Let's assume list of rows.
            return _extract_categories(data)
        else:
            print(f"Primary API Access Failed: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"Error fetching from primary API: {e}")
    
    return []

def _extract_categories(data):
    """
    Parses API response to extract unique service names.
    Handles different potential schema shapes.
    """
    categories = set()
    if not isinstance(data, list):
        print("Warning: API response is not a list.")
        return []
        
    for item in data:
        # Check common keys
        cat = item.get("service_name") or item.get("category") or item.get("service_subtype")
        if cat:
            categories.add(str(cat).strip())
            
    sorted_cats = sorted(list(categories))
    if not sorted_cats:
        print("Warning: No categories extracted from data.")
    return sorted_cats

def get_all_categories(force_refresh=False):
    """
    Returns the list of valid service categories.
    Uses caching to avoid hitting API on every call.
    """
    global _CACHED_CATEGORIES, _LAST_FETCH_TIME
    
    now = datetime.datetime.now()
    
    # Check cache validity
    is_expired = False
    if _LAST_FETCH_TIME:
        elapsed = now - _LAST_FETCH_TIME
        if elapsed > datetime.timedelta(hours=CACHE_DURATION_HOURS):
            is_expired = True
            
    if not _CACHED_CATEGORIES or is_expired or force_refresh:
        fetched = fetch_categories_from_api()
        if fetched:
            _CACHED_CATEGORIES = fetched
            _LAST_FETCH_TIME = now
            print(f"Updated category cache: {_CACHED_CATEGORIES[:5]}... ({len(_CACHED_CATEGORIES)} total)")
        elif not _CACHED_CATEGORIES:
             # If fetch failed and we have nothing, fallback to a minimal hardcoded safety net
             # to prevent application crash on startup
             print("Critical: Could not fetch categories. Using emergency fallback.")
             _CACHED_CATEGORIES = ["Street and Sidewalk Cleaning", "Graffiti", "Pothole", "Encampments"]

    return _CACHED_CATEGORIES

# expose for legacy compatibility if needed, but prefer function call
# WARNING: This will be empty at import time until get_all_categories() is called!
# Best practice is to NOT use this variable directly in other modules.
ALL_CATEGORIES = [] 
