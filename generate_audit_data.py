
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_audit_data():
    np.random.seed(999) # Deterministic
    
    # Configuration
    SERVICE_TYPES = ["Encampment", "Graffiti"]
    NEIGHBORHOODS = ["Bayview", "Sunset", "Marina", "Mission", "Tenderloin"] # 5 neighborhoods
    AGENCIES = ["DPW", "SFPD", "DPH"]
    
    # Historical Data Generation
    # Need > 2.5x ratio in one neighborhood. 
    # Let's make "Bayview" slow, "Marina" fast.
    
    n_hist = 2000
    rows = []
    
    # 6 Month span
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    for _ in range(n_hist):
        st = np.random.choice(SERVICE_TYPES)
        nh = np.random.choice(NEIGHBORHOODS)
        
        # Determine performance profile
        if nh == "Bayview":
            # Slow
            resp_hours = np.random.exponential(scale=100) # Avg 100h
        elif nh == "Marina":
            # Fast
            resp_hours = np.random.exponential(scale=20) # Avg 20h
        else:
            resp_hours = np.random.exponential(scale=50) # Avg 50h
            
        status = "closed"
        
        # Mislabels: 20%
        conf = np.random.uniform(0.5, 1.0)
        if np.random.random() < 0.2:
            conf = 0.5 # < 0.7
            
        # Duplicates: 20%
        is_dup = np.random.random() < 0.2
        
        # Agency
        agency = np.random.choice(AGENCIES)
        
        opened = start_date + timedelta(days=np.random.randint(0, 180))
        closed = opened + timedelta(hours=resp_hours)
        
        rows.append({
            "incident_id": f"HIST-{_}",
            "opened_at": opened,
            "closed_at": closed,
            "status": status,
            "response_time_hours": resp_hours,
            "service_type": st,
            "service_type_confidence": conf,
            "neighborhood": nh,
            "lat": 37.7 + np.random.normal(0, 0.01),
            "lon": -122.4 + np.random.normal(0, 0.01),
            "is_duplicate": is_dup,
            "dedup_cluster_id": f"C-{_}",
            "canonical_incident_id": f"HIST-{_}",
            "agency": agency,
            "redacted_text": "...",
            "pii_flags": []
        })
        
    hist_df = pd.DataFrame(rows)
    hist_df.to_parquet("data/processed/incidents_historical.parquet")
    print(f"Generated {len(hist_df)} historical records.")
    
    # Live Data Generation
    # Need high backlog pressure > 1.5 in one neighborhood (Bayview?)
    # Pressure = open / avg_daily_closures
    # Bayview Avg closed ~ N_bayview / 180. Say 400 / 180 = 2.2/day.
    # To get ratio > 1.5, need > 3.3 open tickets. Easy.
    # Aging tail: > 30% older than 14d.
    
    n_live = 500
    live_rows = []
    
    for _ in range(n_live):
        st = np.random.choice(SERVICE_TYPES)
        nh = np.random.choice(NEIGHBORHOODS)
        
        status = "open"
        resp_hours = np.nan
        
        # Aging: make Bayview often old
        if nh == "Bayview" and np.random.random() < 0.6:
            # Older than 14d
            age_days = np.random.randint(15, 60)
        else:
            age_days = np.random.randint(0, 30)
            
        opened = datetime.now() - timedelta(days=age_days)
        
        live_rows.append({
            "incident_id": f"LIVE-{_}",
            "opened_at": opened,
            "closed_at": pd.NaT,
            "status": status,
            "response_time_hours": resp_hours,
            "service_type": st,
            "service_type_confidence": 0.9,
            "neighborhood": nh,
            "lat": 37.7 + np.random.normal(0, 0.01),
            "lon": -122.4 + np.random.normal(0, 0.01),
            "is_duplicate": False,
            "dedup_cluster_id": None,
            "canonical_incident_id": None,
            "agency": np.random.choice(AGENCIES),
            "redacted_text": "...",
            "pii_flags": []
        })

    # Ensure Bayview has enough open tickets for pressure
    # We want Bayview pressure > 1.5. 
    # Force add some if random didn't give enough?
    # Random should give ~100. Closure rate ~2. 100/2 = 50 pressure.
    # So pressure will be VERY high. Correct.

    live_df = pd.DataFrame(live_rows)
    live_df.to_parquet("data/processed/incidents_live.parquet")
    print(f"Generated {len(live_df)} live records.")

if __name__ == "__main__":
    generate_audit_data()
