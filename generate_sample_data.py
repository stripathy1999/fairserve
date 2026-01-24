
import pandas as pd
import numpy as np

def create_sample_data():
    np.random.seed(42)
    n_rows = 1000
    
    neighborhoods = ['Downtown', 'Westside', 'NorthEnd', 'SouthBay', 'Eastside']
    service_types = ['Pothole', 'StreetLight', 'Trash', 'Encampment']
    statuses = ['closed', 'open']
    
    data = {
        'status': np.random.choice(statuses, n_rows, p=[0.8, 0.2]),
        'response_time_hours': np.random.exponential(scale=24, size=n_rows), # Avg 24 hours
        'service_type': np.random.choice(service_types, n_rows),
        'neighborhood': np.random.choice(neighborhoods, n_rows)
    }
    
    df = pd.DataFrame(data)
    
    # Ensure some open cases have NaN response time (optional, but realistic)
    mask_open = df['status'] == 'open'
    df.loc[mask_open, 'response_time_hours'] = np.nan
    
    output_path = "data/processed/incidents_historical.parquet"
    df.to_parquet(output_path)
    print(f"Created sample data at {output_path} with {n_rows} rows.")

if __name__ == "__main__":
    create_sample_data()
