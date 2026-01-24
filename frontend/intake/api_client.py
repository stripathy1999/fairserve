
# intake/api_client.py

import requests
import datetime
from typing import List, Dict
from intake.config import API_ENDPOINT, API_APP_TOKEN

class CityAPIClient:
    def __init__(self):
        self.endpoint = API_ENDPOINT
        self.headers = {}
        if API_APP_TOKEN:
            self.headers["X-App-Token"] = API_APP_TOKEN

    def _map_record(self, soda_record: Dict) -> Dict:
        """
        Maps SODA API record to internal schema.
        """
        # Parse status to match expected open/closed roughly
        # The schema expects status string, so we pass it through
        
        # Mapping SODA fields to our schema
        return {
            "incident_id": soda_record.get("service_request_id"),
            "original_category": soda_record.get("service_name"), # e.g. "Street and Sidewalk Cleaning"
            "description": soda_record.get("service_details") or soda_record.get("service_subtype"), # Description often in details
            "neighborhood": soda_record.get("analysis_neighborhood"),
            "lat": float(soda_record.get("lat")) if soda_record.get("lat") else None,
            "lon": float(soda_record.get("long")) if soda_record.get("long") else None,
            "opened_at": soda_record.get("requested_datetime"),
            "closed_at": soda_record.get("closed_date"),
            "status": soda_record.get("status_description"),
            "agency": soda_record.get("agency_responsible"),
            "source": soda_record.get("source")
        }

    def fetch_historical_batch(self, start_date: datetime.datetime, end_date: datetime.datetime) -> any: # Generator[List[Dict], None, None]
        """
        Yields data for a specific historical time range using SODA API in batches of 1000.
        """
        limit = 1000
        offset = 0
        
        # SODA uses ISO8601 strings
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        while True:
            params = {
                "$where": f"requested_datetime >= '{start_str}' AND requested_datetime < '{end_str}'",
                "$limit": limit,
                "$offset": offset,
                "$order": "requested_datetime ASC"
            }
            
            try:
                response = requests.get(self.endpoint, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                    
                mapped_data = [self._map_record(r) for r in data]
                yield mapped_data # Yield batch immediately
                
                if len(data) < limit:
                    break
                    
                offset += limit
                
            except Exception as e:
                print(f"Error fetching historical data: {e}")
                break

    def fetch_new_data(self, since_timestamp: datetime.datetime) -> List[Dict]:
        """
        Fetches data since a specific timestamp.
        """
        start_str = since_timestamp.isoformat()
        limit = 1000 # Unlikely to get >1000 in 5 seconds, but good practice
        
        params = {
            "$where": f"requested_datetime > '{start_str}'",
            "$limit": limit,
            "$order": "requested_datetime ASC"
        }
        
        try:
            response = requests.get(self.endpoint, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            return [self._map_record(r) for r in data]
            
        except Exception as e:
            print(f"Error fetching live data: {e}")
            return []
