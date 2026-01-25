
# fairserve/intake/processor.py

import re
import datetime
from typing import List, Dict
import pandas as pd
import numpy as np
from intake.config import DEDUP_THRESHOLD_METERS, DEDUP_TIME_WINDOW_HOURS, OFFICIAL_CATEGORY_KEYWORDS

def normalize_record(record: Dict) -> Dict:
    """
    Cleans keys, parses dates, ensures schema consistency.
    """
    # Ensure all keys exist with defaults
    normalized = {
        "incident_id": record.get("incident_id"),
        "service_type": "other",  # Default, will be repaired
        "service_type_confidence": 0.0,
        "original_category": record.get("original_category"),
        "description_redacted": record.get("description") or "", # Ensure string
        "neighborhood": record.get("neighborhood"),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "opened_at": pd.to_datetime(record.get("opened_at")),
        "closed_at": pd.to_datetime(record.get("closed_at")) if record.get("closed_at") else None,
        "status": record.get("status"),
        "is_duplicate": False,
        "dedup_cluster_id": None,
        "agency": record.get("agency"),
        "source": record.get("source")
    }
    return normalized

def repair_category(record: Dict) -> Dict:
    """
    Checks description against config.OFFICIAL_CATEGORY_KEYWORDS. 
    If original_category is present and matches keywords (or no keywords found), keep it.
    If original_category clearly conflicts with keywords, override with keyword match.
    """
    description = record["description_redacted"].lower()
    original = str(record.get("original_category", "")).strip()
    
    # 1. Start with original as default
    best_match = original if original else "unknown"
    confidence = 1.0 if original else 0.0

    # 2. Check for keyword matches
    found_categories = []
    for category, keywords in OFFICIAL_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in description:
                found_categories.append(category)
                break # Matched this category, move to next
    
    # 3. Decision Logic
    if found_categories:
        # If original is one of the found categories (or effectively same group), trust original
        # Note: This is a strict string match. Logic could be fuzzier if needed.
        if original in found_categories:
            best_match = original
            confidence = 1.0
        else:
            # Conflict! Description says X, Category says Y (or Y is empty)
            # We trust the text content more if we have a match.
            # Pick the first one for now (could be improved with score)
            best_match = found_categories[0]
            confidence = 0.8 # Inferred
            
    record["service_type"] = best_match
    record["service_type_confidence"] = confidence
    return record

def redact_pii(text: str) -> str:
    """
    Regex substitution for emails and phone numbers.
    """
    if not text:
        return ""
        
    # Phone numbers (various formats)
    phone_pattern = r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'
    text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, '[REDACTED_EMAIL]', text)
    
    return text

def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sorts by time. Flags records within space/time thresholds.
    Sets duplicate_count for cluster leaders.
    """
    if df.empty:
        return df
        
    df = df.sort_values(by='opened_at').reset_index(drop=True)
    
    # Initialize columns if not present (safety)
    if 'is_duplicate' not in df.columns:
        df['is_duplicate'] = False
    if 'dedup_cluster_id' not in df.columns:
        df['dedup_cluster_id'] = None

    # Simple pairwise comparison for demonstration (O(N^2) worst case in window)
    # For production/spark, would use sliding window or spatial index
    
    # We will iterate and assign clusters.
    # A processed set to skip already clustered items
    processed_indices = set()
    
    time_window = pd.Timedelta(hours=DEDUP_TIME_WINDOW_HOURS)
    
    # Pre-calculate simple distance roughly (lat/lon to meters approximation)
    # 1 deg lat ~ 111km, 1 deg lon ~ 111km * cos(lat)
    # Using small angle approximation for speed
    
    for i in range(len(df)):
        if i in processed_indices:
            continue
            
        current = df.iloc[i]
        cluster_id = current['incident_id']
        cluster_members = [i]
        
        # Assign leader info
        df.at[i, 'dedup_cluster_id'] = cluster_id
        df.at[i, 'is_duplicate'] = False # Leader is not duplicate
        
        processed_indices.add(i)
        
        # Look ahead
        for j in range(i + 1, len(df)):
            if j in processed_indices:
                continue
                
            next_record = df.iloc[j]
            
            # Time check
            if (next_record['opened_at'] - current['opened_at']) > time_window:
                break # Sorted by time, so we can stop looking
                
            # Space check (Euclidean approximation for short distances)
            # 0.0009 degrees is roughly 100m
            lat_diff = abs(next_record['lat'] - current['lat'])
            lon_diff = abs(next_record['lon'] - current['lon'])
            
            if lat_diff > 0.002 or lon_diff > 0.002: # Coarse filter
                continue

            # Haversine-ish check (simplified)
            # Using pythagoras on degrees scaled to meters
            # mean lat for lon scaling
            avg_lat_rad = np.radians((current['lat'] + next_record['lat']) / 2)
            dx = (lon_diff) * 111320 * np.cos(avg_lat_rad)
            dy = (lat_diff) * 110540
            dist = np.sqrt(dx*dx + dy*dy)
            
            if dist <= DEDUP_THRESHOLD_METERS:
                 # It's a match!
                 df.at[j, 'dedup_cluster_id'] = cluster_id
                 df.at[j, 'is_duplicate'] = True
                 cluster_members.append(j)
                 processed_indices.add(j)
        
    return df

    # 3. Dedup (Batch level)
    df = flag_duplicates(df)
    
    return df

def process_batch(raw_records: List[Dict]) -> pd.DataFrame:
    """
    Master function: Normalization -> Repair (LLM) -> Redact -> Dedup.
    """
    if not raw_records:
        return pd.DataFrame()
        
    # 1. Normalize
    normalized_data = [normalize_record(r) for r in raw_records]
    
    # 2. Repair (LLM) & Redact
    # Import here to avoid circular dependencies if any at module level
    try:
        from image_processing.nemotron_client import verify_incident_text
    except ImportError:
        # Fallback if path issues
        print("Warning: Could not import Nemotron client. Skipping LLM verification.")
        verify_incident_text = None

    for record in normalized_data:
        # Redact first to protect PII before sending to LLM (good practice)
        record["description_redacted"] = redact_pii(record["description_redacted"])
        
        # Verify/Repair Category using LLM
        if verify_incident_text:
            # only call if we have a description
            desc = record["description_redacted"]
            orig_cat = record["original_category"]
            
            if desc:
                # This might be slow for large batches! 
                # Be mindful of rate limits/latency.
                try:
                    result = verify_incident_text(desc, orig_cat)
                    record["service_type"] = result.get("category", orig_cat)
                    record["service_type_confidence"] = result.get("confidence", 0.0)
                    # record["llm_reasoning"] = result.get("reasoning", "") # Optional
                except Exception as e:
                    print(f"LLM Verification failed for {record['incident_id']}: {e}")
            else:
                 record["service_type"] = orig_cat if orig_cat else "Unknown"
                 
        else:
             # Fallback to old logic if import failed
             repair_category(record)

    df = pd.DataFrame(normalized_data)
    
    # 3. Dedup (Batch level)
    df = flag_duplicates(df)
    
    return df
