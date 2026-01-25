import time
import random
import uuid
import json
import os
import datetime
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intake.api_client import CityAPIClient

QUEUE_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), "data/queue")

def ensure_queue_dir():
    if not os.path.exists(QUEUE_DIR):
        os.makedirs(QUEUE_DIR, exist_ok=True)

def fetch_seed_data(days_back=7):
    """Fetches a pool of real data to sample from."""
    print(f"📡 Fetching seed data from the last {days_back} days...")
    client = CityAPIClient()
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    seed_pool = []
    # Fetch one batch (up to 1000 records) is enough
    for batch in client.fetch_historical_batch(start_date, end_date):
        seed_pool.extend(batch)
        if len(seed_pool) >= 1000:
            break
            
    print(f"✅ Loaded {len(seed_pool)} real records into seed pool.")
    return seed_pool

def generate_live_incident(seed_pool):
    """
    Picks a random real record but ensures it looks 'fresh' for the simulation.
    """
    if not seed_pool:
        # Fallback if API fails or returns no data
        return {
             "incident_id": str(uuid.uuid4()),
             "original_category": "Simulation Fallback",
             "description": "API Fetch Failed - Fallback Data",
             "neighborhood": "Unknown",
             "lat": 37.7749, "lon": -122.4194,
             "opened_at": datetime.datetime.now().isoformat(),
             "status": "Open", 
             "source": "simulation_fallback"
        }

    real_record = random.choice(seed_pool)
    incident = real_record.copy()
    
    # Update fields to look "live"
    incident["incident_id"] = str(uuid.uuid4())
    incident["opened_at"] = datetime.datetime.now().isoformat()
    incident["status"] = "Open"
    incident["source"] = "simulation_replay"
    
    # Ensure all required fields for processor exist
    if "description" not in incident:
        # Try to find description in other keys if missing (based on mapping)
        incident["description"] = incident.get("service_details", "")
        
    return incident

def main():
    print("Starting Live Stream Simulation (Queue Mode)...")
    print("Fetching real historical data to seed the simulation...")
    
    ensure_queue_dir()
    seed_pool = fetch_seed_data()
    
    if not seed_pool:
        print("wARNING: No seed data found. Using fallback generation.")

    print("Generation Interval: 5-10 minutes (randomized)")
    
    try:
        while True:
            # 1. Generate
            incident = generate_live_incident(seed_pool)
            
            # 2. Save to Queue
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"live_{timestamp}_{unique_id}.json"
            file_path = os.path.join(QUEUE_DIR, file_name)
            
            with open(file_path, 'w') as f:
                json.dump(incident, f)
                
            print(f"[{datetime.datetime.now().time()}] Generated incident: {incident['incident_id']}")
            print(f"   Category: {incident.get('original_category', 'Unknown')}")
            print(f"   Saved to queue: {file_name}")
            
            # 3. Wait Random Interval (300-600s)
            wait_time = random.randint(300, 600)
            print(f"   Next event in {wait_time} seconds ({wait_time/60:.1f} mins)...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\nStopping Simulation.")

if __name__ == "__main__":
    main()
