import json
from google import genai
from google.genai import types
from data.database import get_connection


def get_gemini_api_key() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = 'gemini_api_key'")
    row = c.fetchone()
    return row[0] if row else ""

def get_gemini_model() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = 'gemini_model'")
    row = c.fetchone()
    conn.close()
    return row[0] if (row and row[0]) else "gemini-2.5-flash"

def save_gemini_api_key(api_key: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('gemini_api_key', ?)",
        (api_key,)
    )
    conn.commit()
    conn.close()


def fetch_item_info(brand: str, model: str) -> dict:
    """
    Calls the Gemini API to get the info and specs for any device.
    Returns a dict with 'description', 'category_hint', and 'specs'.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key configured. Please add it in Settings → Integrations.")

    model_name = get_gemini_model()
    client = genai.Client(api_key=api_key)

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

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    text = response.text.strip()
    # Strip any accidental markdown fences
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        print(f"[AI Autofill] Failed to parse JSON: {text}")
        raise ValueError("Failed to parse specifications from AI.")

def test_gemini_model() -> tuple[bool, str]:
    """Test if the configured Gemini model is valid and accessible."""
    api_key = get_gemini_api_key()
    if not api_key:
        return True, "" # Don't error if they haven't set it up yet
        
    model_name = get_gemini_model()
    client = genai.Client(api_key=api_key)
    try:
        # Minimal request to test model validity
        client.models.generate_content(
            model=model_name,
            contents="hello",
        )
        return True, ""
    except Exception as e:
        msg = str(e).lower()
        if "404" in msg or "not found" in msg:
            return False, f"The Gemini model '{model_name}' is not found or has been retired."
        return False, f"Gemini API Error: {str(e)}"
