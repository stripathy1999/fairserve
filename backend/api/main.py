import os
import sys
import glob
import datetime
import pandas as pd
import uvicorn
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from typing import List, Optional
import json

# --- Configuration & Path Setup ---
# Add project root to path to ensure we can import local modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config.paths import PROCESSED_DIR, QUEUE_DIR
LIVE_DATA_DIR = os.path.join(PROCESSED_DIR, "live_stream")

# --- Local Imports ---
try:
    from image_processing.processor import process_visual_upload
except ImportError as e:
    print(f"Warning: Could not import image_processing: {e}")
    process_visual_upload = None

# --- Background Processing Setup ---
# Decoupled: Services are now started via external script (start_services.ps1)

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
            
            # Persist to Queue (JSON)
            if not os.path.exists(QUEUE_DIR):
                os.makedirs(QUEUE_DIR, exist_ok=True)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            import uuid
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"visual_{timestamp}_{unique_id}.json"
            file_path = os.path.join(QUEUE_DIR, file_name)
            
            with open(file_path, 'w') as f:
                json.dump(incident_data, f)
            
            # Return path for debug/confirmation
            result["storage_path"] = file_path
            result["status"] = "Queued for processing"
            
        return result
            
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
    try:
        if not os.path.exists(LIVE_DATA_DIR):
             return {"data": [], "message": "No live data directory found."}

        # 1. Identify relevant files based on timestamp in filename
        # Filename format: batch_YYYYMMDD_HHMMSS_uuid.parquet
        files = glob.glob(os.path.join(LIVE_DATA_DIR, "*.parquet"))
        
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=minutes_back)
        relevant_files = []
        
        for f in files:
            try:
                # Check modification time
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f))
                if mtime >= cutoff_time:
                    relevant_files.append(f)
            except OSError:
                continue
                
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
        # Using handling for NaNs/Dates by converting timestamps to str if needed
        def safe_json_serialize(obj):
            if pd.isna(obj):
                return None
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            return obj

        # Records dict usually handles basic types, but pandas Timestamp needs care if not native python
        data = result_df.to_dict(orient='records')
        
        # Sanitize data for JSON
        sanitized_data = []
        for record in data:
            new_record = {}
            for k, v in record.items():
                new_record[k] = safe_json_serialize(v)
            sanitized_data.append(new_record)
        
        return {"data": sanitized_data, "count": len(sanitized_data), "total_available": len(full_df)}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "detail": traceback.format_exc()})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
