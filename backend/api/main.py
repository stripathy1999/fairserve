import os
import sys
import glob
import datetime
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from typing import List, Optional

# --- Configuration & Path Setup ---
# Add project root to path to ensure we can import local modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

LIVE_DATA_DIR = os.path.join(PROJECT_ROOT, "data/processed/live_stream")

# --- Local Imports ---
try:
    from image_processing.processor import process_visual_upload
except ImportError as e:
    print(f"Warning: Could not import image_processing: {e}")
    process_visual_upload = None

# --- App Initialization ---
app = FastAPI(
    title="FairServe Live API", 
    description="API for streaming live incident data and processing visual reports."
)

# --- Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/visual-incident")
async def create_visual_incident(file: UploadFile = File(...)):
    """
    Generate an incident from an uploaded image/video using Nemotron VL.
    """
    if not process_visual_upload:
        return {"error": "Image processing module not available."}
        
    try:
        content = await file.read()
        result = process_visual_upload(content, file.filename)
        
        if "incident" in result:
            incident_data = result["incident"]
            print(incident_data)
            # Persist to Parquet (Live Data Stream)
            if not os.path.exists(LIVE_DATA_DIR):
                os.makedirs(LIVE_DATA_DIR, exist_ok=True)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            import uuid
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"visual_{timestamp}_{unique_id}.parquet"
            file_path = os.path.join(LIVE_DATA_DIR, file_name)
            
            # Wrap in list to create DataFrame
            df = pd.DataFrame([incident_data])
            df.to_parquet(file_path, index=False)
            
            # Return path for debug/confirmation
            result["storage_path"] = file_path
            
        return result
    except Exception as e:
        return {"error": f"Failed to process upload: {str(e)}"}

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
    data = result_df.to_dict(orient='records')
    
    return {"data": data, "count": len(data), "total_available": len(full_df)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
