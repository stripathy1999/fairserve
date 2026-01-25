
import os
import sys
import glob
import datetime
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional

# Add project root to path to find data if needed (though we use absolute paths)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = FastAPI(title="FairServe Live API", description="API for streaming live incident data")

# Path to live stream parquet files
# Assuming script is in /api/ and data is in /data/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIVE_DATA_DIR = os.path.join(PROJECT_ROOT, "data/processed/live_stream")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/live")
def get_live_data(
    limit: int = 50, 
    minutes_back: int = 30
):
    """
    Retrieve recent live events.
    
    - **limit**: Max number of records to return.
    - **minutes_back**: Look back this many minutes for data files.
    """
    if not os.path.exists(LIVE_DATA_DIR):
         return {"data": [], "message": "No live data directory found."}

    # 1. Identify relevant files based on timestamp in filename
    # Filename format: batch_YYYYMMDD_HHMMSS_uuid.parquet
    # We want files modified or named within the last X minutes.
    # Using OS modification time is safer/simpler than parsing filenames for all files.
    
    files = glob.glob(os.path.join(LIVE_DATA_DIR, "*.parquet"))
    
    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=minutes_back)
    relevant_files = []
    
    for f in files:
        # Check modification time
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        if mtime >= cutoff_time:
            relevant_files.append(f)
            
    if not relevant_files:
        return {"data": [], "message": f"No data found in the last {minutes_back} minutes."}
        
    # 2. Read and concatenate
    dfs = []
    for f in relevant_files:
        try:
            df = pd.read_parquet(f)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            continue
            
    if not dfs:
        return {"data": []}
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # 3. Filter and Sort
    # Ensure opened_at is datetime
    if 'opened_at' in full_df.columns:
        full_df['opened_at'] = pd.to_datetime(full_df['opened_at'])
        full_df = full_df.sort_values(by='opened_at', ascending=False)
    
    # Slice
    result_df = full_df.head(limit)
    
    # Convert to dict (handling NaNs and dates)
    # orient='records' returns a list of dicts
    data = result_df.to_dict(orient='records')
    
    return {"data": data, "count": len(data), "total_available": len(full_df)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
