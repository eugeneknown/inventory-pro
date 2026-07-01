import json
import google.generativeai as genai
from data.database import get_connection

def get_gemini_api_key() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = 'gemini_api_key'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def save_gemini_api_key(api_key: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('gemini_api_key', ?)", (api_key,))
    conn.commit()
    conn.close()

def fetch_item_info(brand: str, model: str) -> dict:
    """
    Calls the Gemini API to get the info and specs for any device.
    Returns a dict with 'description', 'category_hint', and 'specs'.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key configured. Please add it in Settings.")
    
    genai.configure(api_key=api_key)
    
    # We use gemini-flash-latest since it's very fast, cheap/free, and good at data extraction
    model_instance = genai.GenerativeModel("gemini-flash-latest")
    
    prompt = f"""
    I need the technical specifications and general info for the following device:
    Brand: {brand}
    Model: {model}
    
    Return EXACTLY a valid JSON object with no markdown formatting, no backticks, and these keys:
    - "description": (string) A 1-2 sentence description of what this device is.
    - "category_hint": (string) e.g. "Laptop", "Desktop", "Monitor", "Keyboard", "Mouse", "Headset", "Printer", "Tablet", "Phone", "Other"
    - "specs": (object) ONLY if this is a computer/laptop/tablet. Otherwise, this object should be empty {{}}.
        If it is a computer, provide:
        - "cpu": (string) e.g. "Intel Core i5-1240P" or "Apple M2"
        - "cpu_cores": (integer) e.g. 12
        - "cpu_ghz": (float) e.g. 1.7
        - "ram_gb": (integer) e.g. 16
        - "storage_gb": (integer) e.g. 512
        - "storage_type": (string) "SSD" or "HDD"
        - "gpu": (string) e.g. "Intel Iris Xe"
        - "purchase_year": (integer) The year this was typically released
    
    If you are completely unsure about a specific field, use null instead of guessing wildly.
    """
    
    response = model_instance.generate_content(prompt)
    
    # Clean up the response to parse JSON
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    try:
        data = json.loads(text.strip())
        return data
    except json.JSONDecodeError as e:
        print(f"[AI Autofill] Failed to parse JSON: {text}")
        raise ValueError("Failed to parse specifications from AI.")
