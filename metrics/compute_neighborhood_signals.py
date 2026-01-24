
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# --- Configuration ---
HISTORICAL_FILE = "data/processed/incidents_historical.parquet"
LIVE_FILE = "data/processed/incidents_live.parquet"
OUTPUT_FILE = "data/processed/neighborhood_signals.json"

def main():
    # 1. Load Data
    try:
        hist_df = pd.read_parquet(HISTORICAL_FILE)
        live_df = pd.read_parquet(LIVE_FILE)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return
    except Exception as e:
        # Handle cases like empty files (ArrowInvalid)
        print(f"Error reading parquet files: {e}")
        # If files are empty/invalid, we can't do much.
        return

    # Ensure required columns exist is a good practice, but we trust the input per instructions.
    
    # --- Pre-processing ---
    # Convert dates to datetime if they aren't already
    if 'opened_at' in live_df.columns and not pd.api.types.is_datetime64_any_dtype(live_df['opened_at']):
        live_df['opened_at'] = pd.to_datetime(live_df['opened_at'])
    
    # 2. Compute Signals
    
    # Identify unique neighborhood-service pairs from both datasets
    # We want a base DataFrame of all relevant pairs
    keys = ['service_type', 'neighborhood']
    all_pairs = pd.concat([
        hist_df[keys], 
        live_df[keys]
    ]).drop_duplicates()
    
    # --- Signal 1: Backlog Pressure (Live) ---
    # backlog_pressure = open_incidents / (avg_daily_closures + epsilon)
    
    # Open incidents count per pair
    live_open = live_df[live_df['status'] == 'open']
    open_counts = live_open.groupby(keys).size().reset_index(name='open_incidents')
    
    # Avg daily closures from historical
    # We need a time range to compute "daily". We'll assume the historical dataset spans some time.
    # If 'closed_at' exists we'd use that, but prompt didn't specify it.
    # Proxy: total closed / (max(opened_at) - min(opened_at)) or just a fixed period?
    # Prompt says: "avg number of closed incidents per day (from historical data)"
    # We'll try to find a date range. If 'closed_at' is missing, use 'opened_at' range of closed tickets.
    
    hist_closed = hist_df[hist_df['status'] == 'closed']
    
    if not hist_closed.empty and 'opened_at' in hist_closed.columns:
        # Convert if needed
        if not pd.api.types.is_datetime64_any_dtype(hist_closed['opened_at']):
            hist_closed['opened_at'] = pd.to_datetime(hist_closed['opened_at'])
            
        date_min = hist_closed['opened_at'].min()
        date_max = hist_closed['opened_at'].max()
        
        # Avoid zero division in time
        days_span = (date_max - date_min).days
        if days_span < 1:
            days_span = 1
    else:
        # Fallback if no dates or empty
        days_span = 30 # Default to a month? Or 1 to avoid math errors
    
    closure_counts = hist_closed.groupby(keys).size().reset_index(name='total_closures')
    closure_counts['avg_daily_closures'] = closure_counts['total_closures'] / days_span
    
    # --- Signal 2: Aging Tail 14d (Live) ---
    # (# open > 14d) / (total open)
    now = datetime.now()
    cutoff_date = now - timedelta(days=14)
    
    # We already have live_open
    aging_incidents = live_open[live_open['opened_at'] < cutoff_date]
    aging_counts = aging_incidents.groupby(keys).size().reset_index(name='aging_count')
    
    # --- Signal 3: Duplicate Rate (Historical) ---
    # is_duplicate = true / total
    hist_total_counts = hist_df.groupby(keys).size().reset_index(name='hist_total')
    
    duplicates = hist_df[hist_df['is_duplicate'] == True]
    dup_counts = duplicates.groupby(keys).size().reset_index(name='dup_count')
    
    # --- Signal 4: Mislabel Rate (Historical) ---
    # confidence < 0.7 / total
    mislabels = hist_df[hist_df['service_type_confidence'] < 0.7]
    mislabel_counts = mislabels.groupby(keys).size().reset_index(name='mislabel_count')
    
    # --- Signal 5: Agency Fragmentation (Historical) ---
    # 1 - (max_agency_share)
    # This is a bit more complex group by.
    frag_data = []
    if 'agency' in hist_df.columns:
        # Filter null agencies?
        hist_agency = hist_df.dropna(subset=['agency'])
        
        # For each group, calculate fragmentation
        for (st, n), group in hist_agency.groupby(keys):
            total = len(group)
            if total == 0:
                frag_data.append({'service_type': st, 'neighborhood': n, 'agency_fragmentation': None})
                continue
                
            max_share_count = group['agency'].value_counts().max()
            fragmentation = 1 - (max_share_count / total)
            frag_data.append({'service_type': st, 'neighborhood': n, 'agency_fragmentation': fragmentation})
            
    frag_df = pd.DataFrame(frag_data)
    
    # --- Merging Everything ---
    
    # Start with all pairs
    merged = all_pairs.copy()
    
    # Merge Backlog info
    merged = pd.merge(merged, open_counts, on=keys, how='left')
    merged = pd.merge(merged, closure_counts[['service_type', 'neighborhood', 'avg_daily_closures']], on=keys, how='left')
    
    # Fill NaNs
    merged['open_incidents'] = merged['open_incidents'].fillna(0)
    merged['avg_daily_closures'] = merged['avg_daily_closures'].fillna(0)
    
    # Compute Backlog Pressure
    epsilon = 0.01
    merged['backlog_pressure'] = merged['open_incidents'] / (merged['avg_daily_closures'] + epsilon)
    
    # Merge Aging info
    merged = pd.merge(merged, aging_counts, on=keys, how='left')
    merged['aging_count'] = merged['aging_count'].fillna(0)
    
    # Compute Aging Tail
    # Avoid div by zero (if open_incidents is 0, tail is 0)
    merged['aging_tail_14d'] = merged.apply(
        lambda x: x['aging_count'] / x['open_incidents'] if x['open_incidents'] > 0 else 0.0, 
        axis=1
    )
    
    # Merge Historical Totals
    merged = pd.merge(merged, hist_total_counts, on=keys, how='left')
    merged['hist_total'] = merged['hist_total'].fillna(0) # Should be > 0 if coming from hist, but could be 0 if only in live
    
    # Merge Duplicate info
    merged = pd.merge(merged, dup_counts, on=keys, how='left')
    merged['dup_count'] = merged['dup_count'].fillna(0)
    
    # Compute Duplicate Rate
    merged['duplicate_rate'] = merged.apply(
        lambda x: x['dup_count'] / x['hist_total'] if x['hist_total'] > 0 else 0.0,
        axis=1
    )
    
    # Merge Mislabel info
    merged = pd.merge(merged, mislabel_counts, on=keys, how='left')
    merged['mislabel_count'] = merged['mislabel_count'].fillna(0)
    
    # Compute Mislabel Rate
    merged['mislabel_rate'] = merged.apply(
        lambda x: x['mislabel_count'] / x['hist_total'] if x['hist_total'] > 0 else 0.0,
        axis=1
    )
    
    # Merge Fragmentation
    if not frag_df.empty:
        merged = pd.merge(merged, frag_df, on=keys, how='left')
    else:
        merged['agency_fragmentation'] = None
        
    # --- Final Cleanup ---
    # Select columns
    final_cols = [
        'service_type', 'neighborhood', 
        'backlog_pressure', 'aging_tail_14d', 
        'duplicate_rate', 'mislabel_rate', 
        'agency_fragmentation'
    ]
    
    # Round floats for cleanliness (optional)
    final_df = merged[final_cols].round(4)
    
    # Output
    records = final_df.to_dict(orient='records')
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(records, f, indent=2)
        
    print(f"Processed {len(final_df)} neighborhood-service pairs.")
    print(f"Signals saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
