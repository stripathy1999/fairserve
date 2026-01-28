
import sys
import os
import time
import random
import datetime
import uuid
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intake.api_client import CityAPIClient

# Define output directory relative to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# We write to the QUEUE, not directly to processed parquet.
# process_live.py monitors this queue.
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "../data/queue")

def fetch_seed_data(days_back=7):
    """Fetches a pool of real data to sample from."""
    print(f"📡 Fetching seed data from the last {days_back} days...")
    client = CityAPIClient()
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    seed_pool = []
    # Fetch one batch (up to 1000 records) is enough for a seed pool
    try:
        for batch in client.fetch_historical_batch(start_date, end_date):
            seed_pool.extend(batch)
            if len(seed_pool) >= 1000:
                break
    except Exception as e:
        print(f"⚠️ Error fetching seed data: {e}")
            
    print(f"✅ Loaded {len(seed_pool)} real records into seed pool.")
    if not seed_pool:
        print("⚠️ Warning: No data fetched. Simulation will try to proceed but might fail if pool is empty.")
    return seed_pool

def simulate_random_stream():
    print(f"🚀 Starting Random Live Simulation")
    print(f"Logic: Pick 1 random incident every 1-5 minutes and push to Queue.")
    print(f"Output: {OUTPUT_DIR}")
    
    # Initialize seed data
    seed_pool = fetch_seed_data()
    if not seed_pool:
        # Fallback dummy data if API fails
        seed_pool = [{
            "service_request_id": "dummy",
            "service_name": "Street and Sidewalk Cleaning",
            "service_subtype": "General Cleaning",
            "service_details": "Simulated dummy request",
            "lat": 37.7749,
            "long": -122.4194,
            "requested_datetime": datetime.datetime.now().isoformat(),
            "status_description": "Open",
            "source": "simulation_fallback"
        }]

    # Ensure queue dir exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Press Ctrl+C to stop.\n")
    
    incident_count = 0
    try:
        while True:
            # 1. Wait random interval (1 to 5 minutes)
            # We wait FIRST or LAST? Usually wait between events.
            # Let's generate one immediately, then wait.
            
            incident_count += 1
            
            # Pick Random Incident
            real_record = random.choice(seed_pool)
            
            # Create Simulation Record
            record = real_record.copy()
            record["incident_id"] = str(uuid.uuid4())
            record["opened_at"] = datetime.datetime.now().isoformat()
            record["status"] = "Open"
            record["source"] = "simulation_random"
            
            # Save to Queue (JSON)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"sim_{timestamp}_{record['incident_id'][:6]}.json"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            
            try:
                with open(file_path, 'w') as f:
                    json.dump(record, f, indent=2)
                
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🎲 Generated Incident #{incident_count}")
                print(f"   category: {record.get('service_name', 'Unknown')}")
                print(f"   -> Pushed to Queue: {file_name}")
                
            except Exception as e:
                print(f"   ❌ Error writing to queue: {e}")

            # Determine next wait time (1 to 5 minutes = 60 to 300 seconds)
            wait_seconds = random.randint(60, 300)
            next_time = datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)
            print(f"   ⏳ Waiting {wait_seconds}s (until {next_time.strftime('%H:%M:%S')})...")
            
            time.sleep(wait_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")

if __name__ == "__main__":
    simulate_random_stream()
