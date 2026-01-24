
# intake/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()




# Map of Official Category -> Keywords
OFFICIAL_CATEGORY_KEYWORDS = {
    "Street and Sidewalk Cleaning": ["trash", "garbage", "litter", "debris", "needle", "feces"],
    "Graffiti": ["graffiti", "tag", "paint", "spray"],
    "Encampments": ["encampment", "tent", "homeless", "sleeping"]
}

DEDUP_THRESHOLD_METERS = 100
DEDUP_TIME_WINDOW_HOURS = 24

# SF Open Data API (SODA)
API_ENDPOINT = "https://data.sfgov.org/resource/vw6y-z8j6.json"
# App Token from environment variable
API_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN")
