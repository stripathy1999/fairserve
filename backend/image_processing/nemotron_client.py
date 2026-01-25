import requests
import os
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cloud Configuration (NVIDIA NIM)
INVOKE_URL_CLOUD = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME_CLOUD = "nvidia/nemotron-nano-12b-v2-vl"

# Local Configuration (vLLM)
LOCAL_API_BASE = "http://localhost:8000/v1"
# Based on user info
LOCAL_MODEL_NAME = "/home/dell/Desktop/deploy-vllm/models--nvidia_Nemotron-3-Nano-30B-A3B-FP8/"

def get_api_key():
    key = os.getenv("NIM_API_KEY")
    if not key:
        raise ValueError("NIM_API_KEY not found in environment variables.")
    return key

def _is_local_llm_available():
    """Checks if the local LLM endpoint is reachable."""
    try:
        # Quick health check (vLLM usually exposes /v1/models or just root)
        resp = requests.get("http://localhost:8000/v1/models", timeout=0.5)
        return resp.status_code == 200
    except:
        return False

def analyze_image(image_bytes: bytes, media_format: str = "jpeg") -> str:
    """
    Sends an image to the Nemotron VL model for analysis.
    Uses CLOUD endpoint because VL models can be heavy for local inference 
    unless the local model is explicitly a VL model. 
    Assuming Local LLM is for text-only based on the model name (Nemotron-3-Nano-30B).
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
    
    try:
        from .config.categories import get_all_categories
        all_categories = get_all_categories()
    except ImportError:
        try:
             from backend.config.categories import get_all_categories
             all_categories = get_all_categories()
        except ImportError:
             all_categories = []

    categories_context = f" Choose from: {', '.join(all_categories[:100])}..." if all_categories else ""

    query = (
        "Analyze this image. If it depicts an issue requiring maintenance or city services "
        "(e.g., pothole, graffiti, overflowing trash, broken light), describe it clearly. "
        f"Also suggest a category for the incident.{categories_context} "
        "Return the response in JSON format with keys: 'description', 'category', 'is_incident' (boolean)."
    )
    
    # --- Always use Cloud for Image Analysis for now ---
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
        "model": MODEL_NAME_CLOUD,
        "max_tokens": 1024,
        "temperature": 0.2, 
        "top_p": 1,
        "messages": [
            {"role": "system", "content": "/think"}, 
            {"role": "user", "content": message_content}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(INVOKE_URL_CLOUD, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return content
        
    except Exception as e:
        print(f"Error calling Nemotron API (Cloud): {e}")
        return json.dumps({
            "description": "Error analyzing image.", 
            "category": "Unknown", 
            "is_incident": False
        })

def verify_incident_text(description: str, original_category: str = None) -> dict:
    """
    Uses Nemotron LLM to verify and correct the incident category based on the description.
    Prefers Local LLM if available.
    """
    try:
        from .config.categories import get_all_categories
        all_categories = get_all_categories()
    except ImportError:
        try:
            from backend.config.categories import get_all_categories
            all_categories = get_all_categories()
        except ImportError:
            all_categories = ["Street and Sidewalk Cleaning", "Graffiti", "Pothole"]

    # Construct Prompt
    prompt = (
        f"Task: Classify this incident description into one of the official city service categories.\n\n"
        f"Description: \"{description}\"\n"
    )
    if original_category:
        prompt += f"Original Category: \"{original_category}\"\n"
        
    prompt += (
        f"\nSelect the best matching category from this list:\n"
        f"{json.dumps(all_categories)}\n\n"
        f"Return ONLY a JSON object with keys: 'category' (string), 'confidence' (float 0-1), 'reasoning' (short string)."
    )

    # --- Check for Local LLM ---
    use_local = _is_local_llm_available()
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for City Services. Output valid JSON only."}, 
        {"role": "user", "content": prompt}
    ]

    try:
        if use_local:
            print(f"⚡ using Local LLM: {LOCAL_MODEL_NAME}")
            url = f"{LOCAL_API_BASE}/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.1
            }
            response = requests.post(url, headers=headers, json=payload, timeout=20)
        else:
            print("☁️ Using Cloud Nemotron (NIM)")
            api_key = get_api_key()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": MODEL_NAME_CLOUD,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.1
            }
            response = requests.post(INVOKE_URL_CLOUD, headers=headers, json=payload, timeout=20)

        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Clean markdown
        clean_text = content.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback for simple string output
            print(f"Warning: LLM returned non-JSON: {clean_text[:50]}...")
            return {"category": original_category or "Unknown", "confidence": 0.0, "reasoning": "Parse Error"}
        
    except Exception as e:
        print(f"Error verifying text (Local={use_local}): {e}")
        return {"category": original_category, "confidence": 0.0, "reasoning": "Error"}
