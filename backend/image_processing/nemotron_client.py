import requests
import os
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "nvidia/nemotron-nano-12b-v2-vl"

def get_api_key():
    key = os.getenv("NIM_API_KEY")
    if not key:
        raise ValueError("NIM_API_KEY not found in environment variables.")
    return key

def analyze_image(image_bytes: bytes, media_format: str = "jpeg") -> str:
    """
    Sends an image to the Nemotron VL model for analysis.
    
    Args:
        image_bytes: Raw bytes of the image/video.
        media_format: Format extension (jpeg, png, mp4, etc).
        
    Returns:
        str: The text description/response from the model.
    """
    api_key = get_api_key()
    
    # Map format to mime type
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }
    
    mime_type = mime_map.get(media_format.lower(), "image/jpeg")
    base64_data = base64.b64encode(image_bytes).decode("utf-8")
    
    # Construct Payload
    query = (
        "Analyze this image. If it depicts an issue requiring maintenance or city services "
        "(e.g., pothole, graffiti, overflowing trash, broken light), describe it clearly. "
        "Also suggest a category for the incident. "
        "Return the response in JSON format with keys: 'description', 'category', 'is_incident' (boolean)."
    )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    message_content = [
        {"type": "text", "text": query},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_data}"
            }
        }
    ]
    
    payload = {
        "model": MODEL_NAME,
        "max_tokens": 1024,
        "temperature": 0.2, # Low temp for deterministic format
        "top_p": 1,
        "messages": [
            {"role": "system", "content": "/think"}, # Enable CoT for better reasoning
            {"role": "user", "content": message_content}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract content
        content = result['choices'][0]['message']['content']
        return content
        
    except Exception as e:
        print(f"Error calling Nemotron API: {e}")
        # Return a safe error JSON string to prevent downstream crashes
        return json.dumps({
            "description": "Error analyzing image.", 
            "category": "Unknown", 
            "is_incident": False
        })
