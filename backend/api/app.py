import os
import sys
import glob
import datetime
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path to find data if needed (though we use absolute paths)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

app = FastAPI(title="FairServe Live API", description="API for streaming live incident data")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to live stream parquet files
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIVE_DATA_DIR = os.path.join(PROJECT_ROOT, "data/processed/live_stream")


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}


@app.get("/live")
def get_live_data(
    limit: int = 50,
    minutes_back: int = 180,
):
    """
    Retrieve recent live events.

    - **limit**: Max number of records to return.
    - **minutes_back**: Look back this many minutes for data files.
    """
    if not os.path.exists(LIVE_DATA_DIR):
        return {"data": [], "message": "No live data directory found."}

    files = glob.glob(os.path.join(LIVE_DATA_DIR, "*.parquet"))

    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=minutes_back)
    relevant_files = []

    for f in files:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f))
        if mtime >= cutoff_time:
            relevant_files.append(f)

    if not relevant_files:
        return {"data": [], "message": f"No data found in the last {minutes_back} minutes."}

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

    if "opened_at" in full_df.columns:
        full_df["opened_at"] = pd.to_datetime(full_df["opened_at"])
        full_df = full_df.sort_values(by="opened_at", ascending=False)

    result_df = full_df.head(limit)
    data = result_df.to_dict(orient="records")

    return {"data": data, "count": len(data), "total_available": len(full_df)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
