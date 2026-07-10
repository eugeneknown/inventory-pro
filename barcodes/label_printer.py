"""
InventoryPro - Print-Ready Label Generator
Generates A4 PDF sheets with QR + Code128 labels for equipment.
"""
import os
import io
import qrcode
import barcode as python_barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image
from config import LABELS_DIR


# Label layout (A4 = 210mm × 297mm)
LABEL_W = 90 * mm
LABEL_H = 50 * mm
COLS = 2
ROWS = 5
MARGIN_X = (210 * mm - COLS * LABEL_W) / 2
MARGIN_Y = (297 * mm - ROWS * LABEL_H) / 2


def generate_label_pdf(items: list[dict], org_name: str = "InventoryPro") -> str:
    """
    Generate a print-ready A4 PDF with equipment labels.

    items: list of dicts with keys:
        - serial_number (str)
        - name (str)
        - brand (str, optional)
        - model (str, optional)

    Returns the path to the generated PDF.
    """
    os.makedirs(LABELS_DIR, exist_ok=True)
    _cleanup_old_labels(max_files=10)
    
    from datetime import datetime
    filename = f"labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(LABELS_DIR, filename)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    page_w, page_h = A4

    idx = 0
    while idx < len(items):
        for row in range(ROWS):
            for col in range(COLS):
                if idx >= len(items):
                    break
                item = items[idx]
                x = MARGIN_X + col * LABEL_W
                y = page_h - MARGIN_Y - (row + 1) * LABEL_H

                _draw_label(c, x, y, LABEL_W, LABEL_H, item, org_name)
                idx += 1

        if idx < len(items):
            c.showPage()

    c.save()
    print(f"[Labels] PDF saved: {pdf_path}")
    return pdf_path


def _cleanup_old_labels(max_files=10):
    """Delete old generated label PDFs to save disk space, keeping only the most recent."""
    if not os.path.exists(LABELS_DIR):
        return
    try:
        pdfs = [os.path.join(LABELS_DIR, f) for f in os.listdir(LABELS_DIR) if f.endswith(".pdf")]
        pdfs.sort(key=os.path.getmtime, reverse=True)
        for old_pdf in pdfs[max_files:]:
            try:
                os.remove(old_pdf)
            except OSError:
                pass
    except Exception:
        pass


def _draw_label(c: canvas.Canvas, x: float, y: float,
                w: float, h: float, item: dict, org_name: str):
    """Draw a single equipment label at position (x, y)."""
    pad = 3 * mm

    # Border
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setLineWidth(0.5)
    c.rect(x, y, w, h)

    # Header bar
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(x, y + h - 10 * mm, w, 10 * mm, fill=1, stroke=0)

    # Org name in header
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + pad, y + h - 7 * mm, org_name.upper())

    # Item name
    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Bold", 9)
    name = item.get("name", "Unknown Item")[:35]
    c.drawString(x + pad, y + h - 15 * mm, name)

    # Brand / Model
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    brand_model = " | ".join(filter(None, [item.get("brand"), item.get("model")]))
    if brand_model:
        c.drawString(x + pad, y + h - 20 * mm, brand_model[:40])

    serial = item.get("serial_number", "")

    # QR Code (right side)
    qr_size = 22 * mm
    qr_img = _make_qr(serial)
    if qr_img:
        qr_x = x + w - qr_size - pad
        qr_y = y + pad + 5 * mm
        c.drawInlineImage(qr_img, qr_x, qr_y, qr_size, qr_size)

    # Code128 barcode (bottom, left area)
    bc_w = w - qr_size - pad * 4
    bc_h = 10 * mm
    bc_img = _make_code128(serial)
    if bc_img:
        c.drawInlineImage(bc_img, x + pad, y + pad + 12 * mm, bc_w, bc_h)

    # Serial number text (human-readable)
    c.setFont("Courier-Bold", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(x + pad, y + pad + 7 * mm, f"S/N: {serial}")


def _make_qr(data: str) -> Image.Image:
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")
    except Exception as e:
        print(f"[Label] QR error: {e}")
        return None


def _make_code128(data: str) -> Image.Image:
    try:
        bc_class = python_barcode.get_barcode_class("code128")
        buffer = io.BytesIO()
        bc = bc_class(data, writer=ImageWriter())
        bc.write(buffer, options={
            "write_text": False,
            "module_height": 8.0,
            "quiet_zone": 1.0,
        })
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")
    except Exception as e:
        print(f"[Label] Code128 error: {e}")
        return None
