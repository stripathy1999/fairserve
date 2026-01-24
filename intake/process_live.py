
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
    
    # specific file for live append
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/processed/incidents_live.parquet'))
    
    # initialize "last checked" to now
    last_checked = datetime.datetime.now()
    
    try:
        while True:
            # Poll
            new_data = client.fetch_new_data(last_checked)
            current_time = datetime.datetime.now()
            
            if new_data:
                # Process
                df_batch = process_batch(new_data)
                
                # Append to parquet
                # Parquet append is tricky (requires reading or partitioned dataset).
                # For simplicity here, we'll read-concat-write (inefficient for big data, OK for demo)
                # OR just write separate timestamps files.
                # Requirement says "Appends results to... incidents_live.parquet"
                
                if os.path.exists(output_path):
                    existing_df = pd.read_parquet(output_path)
                    combined_df = pd.concat([existing_df, df_batch], ignore_index=True)
                else:
                    combined_df = df_batch
                
                combined_df.to_parquet(output_path, index=False)
                
                print(f"[{datetime.datetime.now().time()}] Ingested {len(new_data)} new tickets.")
            else:
                # print(".", end="", flush=True) # Heartbeat
                pass
                
            last_checked = current_time
            time.sleep(POLL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\nStopping Live Ingestion.")

if __name__ == "__main__":
    main()
