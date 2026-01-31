import os
from dotenv import load_dotenv
from .paths import BACKEND_DIR

# Load environment variables from .env file in backend directory
load_dotenv(BACKEND_DIR / ".env")

class Settings:
    NIM_API_KEY = os.getenv("NIM_API_KEY")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    SF_DATA_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN")
    
    # Zone configuration
    ZONE1_URL = os.getenv("ZONE1_BASE", "http://localhost:8081")
    ZONE2_URL = os.getenv("ZONE2_BASE", "http://localhost:8080")
    AGENTIQ_URL = os.getenv("AGENTIQ_URL", "http://localhost:8005")

settings = Settings()
