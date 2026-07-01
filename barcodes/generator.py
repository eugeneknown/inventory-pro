"""
InventoryPro - Serial Number Generator
Auto-generates unique serial numbers for items without one.
"""
import uuid
from datetime import datetime
from config import SERIAL_PREFIX


def generate_serial() -> str:
    """
    Generate a unique serial number in format: INV-YYYYMMDD-XXXXX
    Example: INV-20240615-A3F2C
    """
    date_part = datetime.now().strftime("%Y%m%d")
    unique_part = str(uuid.uuid4()).upper().replace("-", "")[:5]
    return f"{SERIAL_PREFIX}-{date_part}-{unique_part}"
