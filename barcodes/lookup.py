"""
InventoryPro - Online Product Lookup
Fetches product info using Brand + Model Name via DuckDuckGo Instant Answer API.
Also attempts to parse computer specs from the returned description text.
No API key required.
"""
import re
import requests
from typing import Optional

TIMEOUT = 6
DDGO_URL = "https://api.duckduckgo.com/"


def lookup_by_model(brand: str, model: str) -> Optional[dict]:
    """
    Search DuckDuckGo Instant Answer API using brand + model name.
    Returns a dict with pre-fill fields, or None if nothing found.

    Returned keys: name, description, category_hint, specs (dict)
    """
    if not brand and not model:
        return None

    # Try AI Autofill first
    try:
        from utils.ai_autofill import fetch_item_info
        ai_data = fetch_item_info(brand, model)
        if ai_data:
            return {
                "name": f"{brand} {model}".strip(),
                "description": ai_data.get("description") or f"AI generated specifications for {brand} {model}.",
                "category_hint": ai_data.get("category_hint") or "Other",
                "specs": ai_data.get("specs", {}),
                "source": "Gemini AI",
            }
    except Exception as e:
        print(f"[Lookup] AI Autofill skipped/failed: {e}")

    # Fallback to DuckDuckGo
    query = f"{brand} {model} specifications".strip()
    try:
        resp = requests.get(
            DDGO_URL,
            params={
                "q":          query,
                "format":     "json",
                "no_redirect": "1",
                "no_html":    "1",
                "t":          "inventorypro",
            },
            timeout=TIMEOUT
        )
        if resp.status_code != 200:
            return None

        data = resp.json()

        # Pull best available text
        abstract   = data.get("AbstractText", "").strip()
        heading    = data.get("Heading", "").strip()
        related    = data.get("RelatedTopics", [])
        related_text = ""
        if related and isinstance(related[0], dict):
            related_text = related[0].get("Text", "").strip()

        description = abstract or related_text

        if not description and not heading:
            return None

        # Build name — prefer heading, fallback to brand+model
        name = heading or f"{brand} {model}".strip()

        # Detect category from description keywords
        category_hint = _detect_category(description or name)

        # Try to extract specs from description text
        specs = _extract_specs(description)

        return {
            "name":          name,
            "description":   description[:500] if description else "",
            "category_hint": category_hint,
            "specs":         specs,
            "source":        "duckduckgo",
        }

    except requests.exceptions.Timeout:
        print("[Lookup] Timeout — check internet connection.")
    except Exception as e:
        print(f"[Lookup] Error: {e}")
    return None


def _detect_category(text: str) -> Optional[str]:
    """Guess item category from description text."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["laptop", "notebook", "ultrabook"]):
        return "Laptop"
    if any(w in text_lower for w in ["desktop", "tower", "workstation"]):
        return "Desktop"
    if any(w in text_lower for w in ["monitor", "display", "screen"]):
        return "Monitor"
    if any(w in text_lower for w in ["printer", "laser", "inkjet"]):
        return "Printer"
    if any(w in text_lower for w in ["tablet", "ipad"]):
        return "Tablet"
    if any(w in text_lower for w in ["phone", "smartphone"]):
        return "Phone"
    if any(w in text_lower for w in ["headset", "headphone", "earphone"]):
        return "Headset"
    if any(w in text_lower for w in ["scanner"]):
        return "Scanner"
    if any(w in text_lower for w in ["keyboard"]):
        return "Keyboard"
    if any(w in text_lower for w in ["mouse"]):
        return "Mouse"
    return None


def _extract_specs(text: str) -> dict:
    """
    Attempt to extract computer specs from a plain-text description.
    Returns a dict with any found values (keys match ComputerSpecs fields).
    """
    specs = {}
    if not text:
        return specs

    t = text.lower()

    # RAM — e.g. "16GB RAM", "16 GB memory", "8gb ddr4"
    ram = re.search(r'(\d+)\s*gb\s*(ram|memory|ddr\d*)', t)
    if ram:
        specs["ram_gb"] = int(ram.group(1))

    # Storage type — detect SSD/HDD keyword anywhere
    if re.search(r'\bssd\b|\bnvme\b|\bm\.2\b|\bemmc\b', t):
        specs["storage_type"] = "SSD"
    elif re.search(r'\bhdd\b|\bhard\s*disk\b|\bhard\s*drive\b', t):
        specs["storage_type"] = "HDD"

    # Storage size — e.g. "512GB SSD", "1TB HDD", "256 GB storage"
    storage = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc|storage)?', t)
    if storage:
        val = int(storage.group(1))
        unit = storage.group(2)
        kind = storage.group(3) or ""
        if unit == "tb":
            val *= 1024
        if val > 32:   # skip values that look like RAM (≤32GB without RAM keyword)
            specs["storage_gb"] = val
            if kind in ("ssd", "nvme", "emmc"):
                specs["storage_type"] = "SSD"
            elif kind == "hdd":
                specs["storage_type"] = "HDD"

    # CPU speed — e.g. "2.8 GHz", "3.5GHz"
    ghz = re.search(r'(\d+\.?\d*)\s*ghz', t)
    if ghz:
        specs["cpu_ghz"] = float(ghz.group(1))

    # CPU cores — e.g. "quad-core", "8-core", "4 cores"
    cores = re.search(r'(\d+)[- ]?core', t)
    if cores:
        specs["cpu_cores"] = int(cores.group(1))
    elif "dual-core" in t or "dual core" in t:
        specs["cpu_cores"] = 2
    elif "quad-core" in t or "quad core" in t:
        specs["cpu_cores"] = 4
    elif "hexa" in t:
        specs["cpu_cores"] = 6
    elif "octa" in t:
        specs["cpu_cores"] = 8

    # GPU — e.g. "Intel Iris Xe", "NVIDIA GeForce RTX 3050"
    gpu = re.search(
        r'(intel\s+(?:iris|uhd|arc)[^\.,]{0,30}|nvidia\s+geforce[^\.,]{0,30}|amd\s+radeon[^\.,]{0,30})',
        t
    )
    if gpu:
        specs["gpu"] = gpu.group(1).strip().title()

    return specs
