
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
<<<<<<< HEAD
    start_date = end_date - relativedelta(months=1)
=======
    start_date = end_date - relativedelta(months=3)
>>>>>>> bca58ca (improved data engineering)
    
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
                 
                 # Derive partition column
                 df_chunk['opened_date'] = pd.to_datetime(df_chunk['opened_at']).dt.strftime('%Y-%m-%d')
                 
                 # Save batch (appended/managed by parquet dataset logic if strictly needed, 
                 # but simplest way to ensure partitions is writing the dataset)
                 # We can just write this chunk to the dataset directory.
                 
                 # Note: to_parquet with partition_cols will create the directory structure.
                 # If we give a filename, it might complain with partition_cols. 
                 # We should point to the directory.
                 
                 # PyArrow engine handles appending/writing multiple files to a partitioned dataset directory
                 # providing a unique UUID for the file fragment is implicit or we can specify `basename_template`.
                 
                 # Simplest approach for batch processing: 
                 # Use a distinct filename prefix or rely on the engine? 
                 # Actually, with partition_cols, the 'path' argument is the Root Directory of the dataset.
                 
                 unique_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                 df_chunk.to_parquet(output_dir, index=False, partition_cols=['opened_date', 'service_type'], basename_template=f"part_{unique_id}_{{i}}.parquet")
                 
                 batch_count += 1
                 print(f"  -> Batch {batch_count}: {len(raw_batch)} records. Saved to dataset at {output_dir}")
        
        if batch_count == 0:
            print("  -> No data found.")
            
        current_start = current_end
        processed_count += 1
        
    print("Historical ingestion complete.")

if __name__ == "__main__":
    main()
