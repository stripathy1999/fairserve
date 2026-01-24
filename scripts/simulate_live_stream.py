
import sys
import os
import time
import random
import datetime
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from intake.processor import process_batch
from intake.api_client import CityAPIClient

OUTPUT_DIR = "data/processed/live_stream"

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
    print(f"🚀 Starting Live Simulation (Replaying Real Data)")
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
            
            # Process
            df = process_batch(raw_data)
            
            # Deduplicate: Remove duplicates from this batch
            initial_count = len(df)
            df = df[df['is_duplicate'] == False]
            dedup_count = len(df)
            
            if dedup_count < initial_count:
                print(f"   ✂️  Removed {initial_count - dedup_count} duplicates.")
            
            # Save results (Parquet)
            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
            
            # Use timestamp and UUID for unique filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"batch_{timestamp}_{unique_id}.parquet"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            
            df.to_parquet(file_path, index=False)
            
            # Stats
            print(f"   ✅ Processed {len(df)} records. Saved to {file_path}")
            if not df.empty:
                print(f"   Sample Limit: {df.iloc[0]['service_type']} (Confidence: {df.iloc[0]['service_type_confidence']})")
            
            print(f"   Waiting {interval_seconds}s for next batch...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")

if __name__ == "__main__":
    # Allow command line overrides for testing: python simulate_live_stream.py [interval] [size]
    interval = 15 * 60 # 15 minutes
    size = 20
    
    if len(sys.argv) > 1:
        interval = int(sys.argv[1])
    if len(sys.argv) > 2:
        size = int(sys.argv[2])
        
    simulate_stream(interval, size)
