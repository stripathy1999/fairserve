
import sys
import os
import time
import random
import datetime
import uuid

# Add project root to path
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intake.api_client import CityAPIClient
from intake.process_live import ingest_live_batch

def fetch_seed_data(days_back=7):
    """Fetches a pool of real data to sample from."""
    print(f"📡 Fetching seed data from the last {days_back} days...")
    client = CityAPIClient()
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    seed_pool = []
    # Fetch one batch (up to 1000 records) is enough for a seed pool
    for batch in client.fetch_historical_batch(start_date, end_date):
        seed_pool.extend(batch)
        if len(seed_pool) >= 1000:
            break
            
    print(f"✅ Loaded {len(seed_pool)} real records into seed pool.")
    if not seed_pool:
        print("⚠️ Warning: No data fetched. Simulation will fail.")
    return seed_pool

def generate_mock_batch(seed_pool, size=20):
    batch = []
    base_time = datetime.datetime.now()
    
    if not seed_pool:
        return []

    for i in range(size):
        # Pick a random real record
        real_record = random.choice(seed_pool)
        
        # Create a new event based on the real one
        record = real_record.copy()
        record["incident_id"] = str(uuid.uuid4()) # New ID
        record["opened_at"] = base_time.isoformat() # New Time
        record["status"] = "Open"
        record["source"] = "simulation_replay"
        
        batch.append(record)
    return batch

def simulate_stream(interval_seconds=15*60, batch_size=20):
    print(f"🚀 Starting Live Simulation (Direct Integration)")
    print(f"Rate: {batch_size} records every {interval_seconds} seconds.")
    
    # Initialize seed data
    seed_pool = fetch_seed_data()
    if not seed_pool:
        return

    print("Press Ctrl+C to stop.\n")
    
    batch_count = 0
    try:
        while True:
            batch_count += 1
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Generating batch #{batch_count} ({batch_size} records)...")
            
            raw_data = generate_mock_batch(seed_pool, batch_size)
            
            # Send to Ingestion
            ingest_live_batch(raw_data)
            
            print(f"   ✅ Sent {len(raw_data)} records to ingestion.")
            
            print(f"   Waiting {interval_seconds}s for next batch...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")

if __name__ == "__main__":
    # Hardcoded values as per requirements: 15 minutes, 20 records
    interval = 15 * 60 
    size = 20
    
    simulate_stream(interval, size)
