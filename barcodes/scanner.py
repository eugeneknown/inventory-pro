"""
InventoryPro - Barcode Scanner
Decodes barcodes and QR codes from uploaded image files.
"""
from PIL import Image
from pyzbar import pyzbar
from typing import Optional


def decode_barcode_from_file(image_path: str) -> Optional[str]:
    """
    Decode the first barcode/QR code found in an image file.
    Returns the serial number string, or None if nothing found.
    """
    try:
        img = Image.open(image_path)
        barcodes = pyzbar.decode(img)
        if barcodes:
            return barcodes[0].data.decode("utf-8").strip()
        return None
    except Exception as e:
        print(f"[Barcode] Decode error: {e}")
        return None


def decode_barcode_from_pil(image: Image.Image) -> Optional[str]:
    """Decode from an already-loaded PIL Image."""
    try:
        barcodes = pyzbar.decode(image)
        if barcodes:
            return barcodes[0].data.decode("utf-8").strip()
        return None
    except Exception as e:
        print(f"[Barcode] PIL decode error: {e}")
        return None
