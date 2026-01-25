#!/usr/bin/env python3
import os
import json
import subprocess
import sys
from datetime import datetime

# --- Configuration ---
LIVE_DIR = "data/processed/live_stream"
STATE_FILE = "data/processed/.processed_live_batches.json"

PIPELINE_SCRIPTS = [
    "metrics/compute_fairness_metrics.py",
    "metrics/compute_neighborhood_signals.py",
    "state/build_city_state.py",
    "sim/simulator.py",
    "sim/verifier.py"
]

def load_processed_batches():
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Corrupted state file {STATE_FILE}. Starting fresh.")
        return []

def save_processed_batches(batches):
    with open(STATE_FILE, 'w') as f:
        json.dump(batches, f, indent=2)

def run_pipeline():
    print(f"\n--- Starting Zone 2 Recompute at {datetime.now().isoformat()} ---")
    
    for script in PIPELINE_SCRIPTS:
        print(f"Running {script}...")
        
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run([sys.executable, script], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"!!! FAILURE !!!")
            print(f"Script {script} failed with return code {result.returncode}")
            print("Stderr output:")
            print(result.stderr)
            print("Stdout output:")
            print(result.stdout)
            print("Aborting pipeline.")
            return False
            
        print(f"SUCCESS: {script}")
        # Optional: Print script output if needed, or keep it quiet unless error
        # print(result.stdout)
        
    print(f"--- Zone 2 Recompute COMPLETED at {datetime.now().isoformat()} ---\n")
    return True

def main():
    # 1. Scan for batches
    if not os.path.exists(LIVE_DIR):
        print(f"Live directory {LIVE_DIR} does not exist. Creating it.")
        os.makedirs(LIVE_DIR, exist_ok=True)
        # Even if created, it's empty, so return
        print("No new live batches — skipping Zone 2 recompute.")
        return

    all_files = os.listdir(LIVE_DIR)
    batch_files = sorted([f for f in all_files if f.endswith('.parquet')])
    
    # 2. Check state
    processed = set(load_processed_batches())
    
    new_batches = [f for f in batch_files if f not in processed]
    
    if not new_batches:
        print("No new live batches — skipping Zone 2 recompute.")
        return
        
    print(f"Detected {len(new_batches)} new batch(es):")
    for f in new_batches:
        print(f"  - {f}")
        
    # 3. Trigger Pipeline
    success = run_pipeline()
    
    # 4. Update State (only on success)
    if success:
        # Add new batches to processed list
        # We assume strict append semantics; if a file was processed before, it stays processed.
        # We just need to ensure we add the new ones.
        updated_processed = sorted(list(processed.union(new_batches)))
        save_processed_batches(updated_processed)
        print("State updated. New batches marked as processed.")
    else:
        print("Pipeline failed. State NOT updated.")
        sys.exit(1)

if __name__ == "__main__":
    main()
