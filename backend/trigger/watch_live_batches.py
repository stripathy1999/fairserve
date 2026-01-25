#!/usr/bin/env python3
import sys
import time
import subprocess
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

# --- Configuration ---
# Absolute path recommended for watcher stability
WATCH_DIR = "/home/dell/Desktop/fairserve-1/backend/data/processed/live_stream"
TRIGGER_SCRIPT = "/home/dell/Desktop/fairserve-1/backend/scripts/trigger_zone2.py"

class LiveBatchHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if not filename.endswith('.parquet'):
            return
            
        print(f"\n[EVENT] New file detected: {filename}")
        print(f"[ACTION] Triggering Zone 2 pipeline at {datetime.now().isoformat()}...")
        
        # Call the existing pipeline trigger script
        # We pass python executable ensuring the same environment
        try:
            result = subprocess.run(
                [sys.executable, TRIGGER_SCRIPT],
                capture_output=True,
                text=True
            )
            
            # Print output from the trigger script
            print("--- Pipeline Output Start ---")
            print(result.stdout)
            if result.stderr:
                print("--- Pipeline Stderr ---")
                print(result.stderr)
            print("--- Pipeline Output End ---")
            
            if result.returncode == 0:
                print(f"[SUCCESS] Pipeline completed successfully at {datetime.now().isoformat()}")
            else:
                print(f"[FAILURE] Pipeline failed with code {result.returncode}")
                
        except Exception as e:
            print(f"[ERROR] Failed to execute trigger script: {e}")

def main():
    if not os.path.exists(WATCH_DIR):
        print(f"Creating watch directory: {WATCH_DIR}")
        os.makedirs(WATCH_DIR, exist_ok=True)
        
    print(f"Starting FairServe Live Watcher...")
    print(f"Monitoring: {WATCH_DIR}")
    print(f"Triggering: {TRIGGER_SCRIPT}")
    print("Press Ctrl+C to stop.")
    
    event_handler = LiveBatchHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
