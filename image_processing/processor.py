import cv2
import numpy as np
import uuid
import json
import datetime
from .nemotron_client import analyze_image

# Supported ARM KleidiCV optimizations happen automatically in recent OpenCV builds
# when cv2.resize or other supported ops are called.

MAX_DIMENSION = 1024

def process_visual_upload(file_bytes: bytes, filename: str) -> dict:
    """
    Processes an uploaded image, runs it through Nemotron, and generates an incident if applicable.
    
    Args:
        file_bytes: Raw file content.
        filename: Original filename.
        
    Returns:
        dict: Incident object or status message.
    """
    try:
        # 1. Decode Image (OpenCV)
        # Convert bytes to numpy array
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"error": "Could not decode image."}

        # 2. Pre-processing (ARM Optimized)
        # Resize if too large to save bandwidth/latency
        h, w = img.shape[:2]
        if h > MAX_DIMENSION or w > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(h, w)
            new_size = (int(w * scale), int(h * scale))
            # cv2.resize is accelerated by KleidiCV on ARM
            img = cv2.resize(img, new_size, interpolation=cv2.INTER_LINEAR)
            
        # Re-encode to bytes for API
        ext = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
            
        success, encoded_img = cv2.imencode(f'.{ext}', img)
        if not success:
            return {"error": "Could not encode processed image."}
            
        processed_bytes = encoded_img.tobytes()
        
        # 3. Analyze with Nemotron
        analysis_text = analyze_image(processed_bytes, ext)
        print(analysis_text)
        # 4. Parse Result
        # The prompt asks for JSON, but LLMs might wrap it in markdown block ```json ... ```
        clean_text = analysis_text.replace("```json", "").replace("```", "").strip()
        try:
            analysis_json = json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback if specific formatting failed
            analysis_json = {
                "description": clean_text,
                "category": "Unclassified",
                "is_incident": True # Default to True to be safe if it returned text
            }
            
        if not analysis_json.get("is_incident", False):
            return {
                "message": "No incident detected.",
                "analysis": analysis_json
            }
            
        # 5. Create Incident Object
        incident = {
            "incident_id": str(uuid.uuid4()),
            "service_type": analysis_json.get("category", "General Request"),
            "service_type_confidence": 0.95, # Placeholder from LLM
            "original_category": analysis_json.get("category", "General"),
            "description_redacted": analysis_json.get("description", ""),
            "neighborhood": "Unknown", # Need metadata/GPS for this
            "lat": 0.0,
            "lon": 0.0,
            "opened_at": datetime.datetime.now().isoformat(),
            "closed_at": None,
            "status": "Open",
            "is_duplicate": False,
            "dedup_cluster_id": None,
            "agency": "Generated",
            "source": "Visual API"
        }
        
        return {"incident": incident}

    except Exception as e:
        print(f"Error processing visual upload: {e}")
        return {"error": str(e)}
