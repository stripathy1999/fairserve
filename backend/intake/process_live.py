
import sys
import os
import time
import datetime
import glob
import json
import pandas as pd
import threading

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Attempt flexible import
try:
    from intake.processor import process_batch
except ImportError:
    from backend.intake.processor import process_batch

# Configuration
QUEUE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/queue'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/processed/live_stream'))
# Reduced poll interval for better responsiveness to demo
POLL_INTERVAL_SECONDS = 10 

# Global stop signal
_STOP_EVENT = threading.Event()

def ingest_queue():
    """
    Reads all JSON files from the queue, processes them, saves to Parquet, and deletes source files.
    """
    if not os.path.exists(QUEUE_DIR):
        # Silent return if dir doesn't exist yet
        return

    # 1. Find Files
    json_files = glob.glob(os.path.join(QUEUE_DIR, "*.json"))
    if not json_files:
        return

    print(f"[{datetime.datetime.now().time()}] Live Processor: Found {len(json_files)} items in queue.")

    # 2. Read Data
    raw_records = []
    processed_files = []
    
    for jf in json_files:
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
                # Handle if file content is list or dict
                if isinstance(data, list):
                    raw_records.extend(data)
                elif isinstance(data, dict):
                    raw_records.append(data)
                processed_files.append(jf)
        except Exception as e:
            print(f"Error reading {jf}: {e}")
            continue

    if not raw_records:
        return

    # 3. Process Batch
    print(f"Live Processor: Processing {len(raw_records)} records...")
    df_batch = process_batch(raw_records)

    # 4. Save to Parquet
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    import uuid
    unique_id = uuid.uuid4().hex[:6]
    file_name = f"batch_{timestamp}_{unique_id}.parquet"
    file_path = os.path.join(OUTPUT_DIR, file_name)
    
    try:
        df_batch.to_parquet(file_path, index=False)
        print(f"Live Processor: Saved processed batch to {file_path}")
        
        # 5. Delete Queue Files
        for jf in processed_files:
            try:
                os.remove(jf)
            except OSError as e:
                print(f"Error deleting {jf}: {e}")
                
    except Exception as e:
        print(f"Error saving parquet: {e}")

def run_scheduler(stop_event=None):
    """
    Runs the ingest loop until stop_event is set.
    """
    print("Starting Live Queue Consumer Background Thread...")
    if stop_event:
        global _STOP_EVENT
        _STOP_EVENT = stop_event
        
    while not _STOP_EVENT.is_set():
        try:
            ingest_queue()
        except Exception as e:
            print(f"Live Processor Error: {e}")
            
        # Sleep in small chunks to allow quick shutdown
        for _ in range(POLL_INTERVAL_SECONDS):
            if _STOP_EVENT.is_set():
                break
            time.sleep(1)
            
    print("Live Queue Consumer Stopped.")

def main():
    # Standalone run mode
    try:
        run_scheduler(threading.Event()) # Pass a fresh event that won't be set externally
    except KeyboardInterrupt:
        print("\nStopping Queue Consumer.")

if __name__ == "__main__":
    main()
