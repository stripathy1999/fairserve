
# fairserve/intake/process_live.py

import sys
import os
import time
import datetime
import pandas as pd
import json
import glob

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from intake.processor import process_batch

POLL_INTERVAL_SECONDS = 60* 5

def main():
    print("Starting Live Data Ingestion Daemon (Queue Mode)...")
    print("Press Ctrl+C to stop.")
    
    # Paths relative to this script: backend/intake/process_live.py
    # Data root: ../../data
    BASE_DIR = os.path.dirname(__file__)
    DATA_ROOT = os.path.abspath(os.path.join(BASE_DIR, '../../data'))
    
    QUEUE_DIR = os.path.join(DATA_ROOT, 'queue')
    OUTPUT_DIR = os.path.join(DATA_ROOT, 'processed/live_stream')
    
    # Ensure output directory exists (queue directory should be created by API)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
    print(f"Monitoring Queue: {QUEUE_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")

    try:
        while True:
            # 1. Scan for JSON files in queue
            if not os.path.exists(QUEUE_DIR):
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
                
            json_files = glob.glob(os.path.join(QUEUE_DIR, "*.json"))
            
            if json_files:
                print(f"[{datetime.datetime.now().time()}] Found {len(json_files)} new tickets in queue.")
                
                batch_data = []
                processed_files = []
                
                # 2. Read all files
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Handle both list of dicts and single dict
                            if isinstance(data, list):
                                batch_data.extend(data)
                            elif isinstance(data, dict):
                                batch_data.append(data)
                            processed_files.append(json_file)
                    except Exception as e:
                        print(f"Error reading {json_file}: {e}")
                
                if batch_data:
                    # 3. Process Batch
                    try:
                        df_batch = process_batch(batch_data)
                        
                        # 4. Save to unique Parquet file
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        filename = f"batch_{timestamp}.parquet"
                        output_file = os.path.join(OUTPUT_DIR, filename)
                        
                        df_batch.to_parquet(output_file, index=False)
                        print(f"Saved batch to {output_file}")
                        
                        # 5. Delete processed files only if processing succeeded
                        for f in processed_files:
                            try:
                                os.remove(f)
                            except OSError as e:
                                print(f"Error deleting {f}: {e}")
                                
                    except Exception as e:
                        print(f"Error processing batch: {e}")
                else:
                    # Valid files were found but contained no data? Clean them up.
                    for f in processed_files:
                        try:
                            os.remove(f)
                        except OSError:
                            pass

            else:
                pass
                
            time.sleep(POLL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\nStopping Live Ingestion.")

if __name__ == "__main__":
    main()
