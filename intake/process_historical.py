
# fairserve/intake/process_historical.py

import sys
import os
import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

# Ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from intake.api_client import CityAPIClient
from intake.processor import process_batch

def main():
    print("Starting Historical Data Ingestion...")
    
    client = CityAPIClient()
    
    # Define time range: last 6 months
    end_date = datetime.datetime.now()
    start_date = end_date - relativedelta(months=1)
    
    # Process in 1-week chunks
    current_start = start_date
    chunk_size = datetime.timedelta(weeks=1)
    
    all_dfs = []
    
    total_chunks = int((end_date - start_date).days / 7) + 1
    processed_count = 0
    
    while current_start < end_date:
        current_end = min(current_start + chunk_size, end_date)
        
        print(f"Processing chunk {processed_count + 1}/{total_chunks}: {current_start.date()} to {current_end.date()}...")
        
        # Fetch & Process Batches
        batch_count = 0
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/processed/historical'))
        os.makedirs(output_dir, exist_ok=True)
        
        for raw_batch in client.fetch_historical_batch(current_start, current_end):
             if raw_batch:
                 df_chunk = process_batch(raw_batch)
                 
                 # Save batch immediately
                 file_name = f"incidents_{current_start.date()}_{batch_count}.parquet"
                 file_path = os.path.join(output_dir, file_name)
                 df_chunk.to_parquet(file_path, index=False)
                 
                 batch_count += 1
                 print(f"  -> Batch {batch_count}: {len(raw_batch)} fetched. Saved to {file_name}")
        
        if batch_count == 0:
            print("  -> No data found.")
            
        current_start = current_end
        processed_count += 1
        
    print("Historical ingestion complete.")

if __name__ == "__main__":
    main()
