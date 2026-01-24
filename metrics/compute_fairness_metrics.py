
import pandas as pd
import json

# --- Configuration ---
INPUT_FILE = "/home/dell/Desktop/fairserve-1/data/processed/incidents_historical.parquet"
OUTPUT_FILE = "/home/dell/Desktop/fairserve-1/data/processed/fairness_metrics.json"

def main():
    # 1. Load data and filter for closed incidents
    try:
        df = pd.read_parquet(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # Filter closed incidents
    df = df[df['status'] == 'closed'].copy()

    if df.empty:
        print("No closed incidents found.")
        return

    # 2. Compute neighborhood-level metrics (N, median, p90)
    # Group by service_type, neighborhood
    # We need to compute count, p50 (median), p90
    
    # helper for p90
    def p90(x):
        return x.quantile(0.9)

    neighborhood_stats = df.groupby(['service_type', 'neighborhood'])['response_time_hours'].agg(
        N='count',
        p50_hr='median',
        p90_hr=p90
    ).reset_index()

    # 3. Compute city-wide baselines (p90) per service_type
    city_stats = df.groupby('service_type')['response_time_hours'].agg(
        city_p90_hr=p90
    ).reset_index()

    # 4. Join and Compute Ratio
    merged = pd.merge(neighborhood_stats, city_stats, on='service_type', how='left')

    # Avoid division by zero
    merged['ratio_p90'] = merged.apply(
        lambda row: row['p90_hr'] / row['city_p90_hr'] if row['city_p90_hr'] > 0 else 0.0, 
        axis=1
    )

    # 5. Rank and Worst-K Flag
    # Sort by service_type (asc) and ratio_p90 (desc)
    merged.sort_values(by=['service_type', 'ratio_p90'], ascending=[True, False], inplace=True)

    # Assign rank within each service_type
    merged['rank'] = merged.groupby('service_type').cumcount() + 1
    
    # Worst K flag (True if rank <= 3)
    merged['worst_k_flag'] = merged['rank'] <= 3

    # 6. Output to JSON
    # Convert to list of dicts
    records = merged.to_dict(orient='records')
    
    # Write to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(records, f, indent=2)

    # 7. Summary
    unique_services = merged['service_type'].nunique()
    total_neighborhoods = len(merged)
    print(f"Processed {unique_services} service types across {total_neighborhoods} neighborhood-service pairs.")
    print(f"Metrics saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
