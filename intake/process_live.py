
# fairserve/intake/process_live.py

import sys
import os
import time
import datetime
import pandas as pd

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from intake.api_client import CityAPIClient
from intake.processor import process_batch

POLL_INTERVAL_SECONDS = 5 # Short interval for demo purposes

def main():
    print("Starting Live Data Ingestion Daemon...")
    print("Press Ctrl+C to stop.")
    
    client = CityAPIClient()
    
    # initialize "last checked" to now
    last_checked = datetime.datetime.now()
    
    try:
        while True:
            # Poll
            new_data = client.fetch_new_data(last_checked)
            current_time = datetime.datetime.now()
            
            if new_data:
                ingest_live_batch(new_data)
                print(f"[{datetime.datetime.now().time()}] Ingested {len(new_data)} new tickets.")
            else:
                # print(".", end="", flush=True) # Heartbeat
                pass
                
            last_checked = current_time
            time.sleep(POLL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\nStopping Live Ingestion.")

def ingest_live_batch(data_batch):
    """
    Processes and saves a batch of live data.
    Can be called by the API poller or the simulator.
    """
    # basic check
    if not data_batch:
        return

    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/processed/live_stream'))
    
    # Process
    df_batch = process_batch(data_batch)
    
    # Ensure directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)

    # Use timestamp and UUID for unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    import uuid
    unique_id = uuid.uuid4().hex[:6]
    file_name = f"batch_{timestamp}_{unique_id}.parquet"
    file_path = os.path.join(output_path, file_name)
    
    df_batch.to_parquet(file_path, index=False)


if __name__ == "__main__":
    main()
