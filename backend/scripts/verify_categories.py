import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intake.processor import process_batch
from config.categories import get_all_categories

def test_category_logic():
    print("Running category logic tests...")
    
    # Ensure categories are loaded
    cats = get_all_categories()
    print(f"Loaded {len(cats)} categories for testing.")
    
    mock_data = [
        # Case 1: Match - Keywords agree with Category -> Keep Category
        {
            "incident_id": "1",
            "original_category": "Street and Sidewalk Cleaning",
            "description": "Just some trash on the street",
            "opened_at": "2023-01-01T10:00:00",
            "lat": 37.7749, "lon": -122.4194,
            "status": "Open"
        },
        # Case 2: Mismatch - Category says Encampment, Description says Graffiti -> Correct to Graffiti
        {
            "incident_id": "2",
            "original_category": "Encampments", 
            "description": "Huge graffiti spray paint on the wall", # 'graffiti', 'paint' -> Graffiti
            "opened_at": "2023-01-01T10:05:00",
            "lat": 37.7750, "lon": -122.4195,
            "status": "Open"
        },
        # Case 3: Ambiguity - Unknown category, description implies a known one
        {
             "incident_id": "3",
             "original_category": "Unknown Garbage", # Unknown category
             "description": "A tent on the sidewalk", # 'tent' -> Encampments
             "opened_at": "2023-01-01T10:10:00",
             "lat": 37.7751, "lon": -122.4196,
              "status": "Open"
        }
    ]

    df = process_batch(mock_data)
    
    print("\nResults:")
    print(df[['incident_id', 'original_category', 'description_redacted', 'service_type']])
    
    # Assertions
    failures = []
    
    # Row 0: Should stay "Street and Sidewalk Cleaning"
    r0 = df.iloc[0]
    if r0['service_type'] != "Street and Sidewalk Cleaning":
        failures.append(f"Row 0 Failed: Expected 'Street and Sidewalk Cleaning', got '{r0['service_type']}'")

    # Row 1: Should corrected to "Graffiti"
    r1 = df.iloc[1]
    if r1['service_type'] != "Graffiti":
        failures.append(f"Row 1 Failed: Expected 'Graffiti' (Correction), got '{r1['service_type']}'")
        
    # Row 2: Should corrected to "Encampments"
    r2 = df.iloc[2]
    if r2['service_type'] != "Encampments":
        failures.append(f"Row 2 Failed: Expected 'Encampments' (from Unknown), got '{r2['service_type']}'")

    if failures:
        print("\n❌ Verification FAILED:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("\n✅ Verification PASSED: Logic holds.")
        sys.exit(0)

if __name__ == "__main__":
    test_category_logic()
