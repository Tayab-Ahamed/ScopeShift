"""Generate the three ScopeShift demo fixtures: brd.pdf, checkout.png, client_note.txt."""
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

FX = Path("fixtures")
FX.mkdir(exist_ok=True)

BRD_TITLE = "Business Requirements Document - Online Store Checkout"
BRD_PAGES = [
    ["1. Purpose", "This document defines requirements for the Online Store checkout flow, v1.0.",
     "2. Payment Methods",
     "REQ-PAY-01: Checkout shall support UPI payments only.",
     "Business rule: UPI is the exclusive payment method for v1.0. No other payment method is in scope."],
    ["3. Currency", "REQ-CUR-01: All prices shall be shown and charged in INR."],
]
CLIENT_NOTE = (
    "From: Priya Nair (Client, Product Owner)\n"
    "To: Delivery team\n"
    "Subject: Checkout payment scope\n\n"
    "After reviewing the demo, we are changing scope. Checkout shall support Card payments. "
    "UPI moves to Phase 2.\n"
)


def make_brd():
    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    for i, lines in enumerate(BRD_PAGES):
        pdf.add_page()
        if i == 0:
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 10, BRD_TITLE, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
        for ln in lines:
            bold = ln[0].isdigit() and "." in ln[:3]
            pdf.set_font("Helvetica", "B" if bold else "", 12)
            pdf.multi_cell(0, 8, ln, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_y(-20)
        pdf.cell(0, 8, f"Page {i + 1}", align="C")
    pdf.output(str(FX / "brd.pdf"))
    (FX / "brd.txt").write_text(
        BRD_TITLE + "\n\n" + "\n\n".join("\n".join(p) for p in BRD_PAGES) + "\n", encoding="utf-8")


def font(size, bold=False):
    for name in ("arialbd.ttf" if bold else "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_screenshot():
    im = Image.new("RGB", (900, 620), "#f4f5f7")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 900, 60], fill="#1f2937")
    d.text((24, 18), "Online Store  |  Checkout", fill="white", font=font(22, True))
    d.rounded_rectangle([40, 90, 860, 560], 12, fill="white", outline="#d1d5db")
    d.text((70, 115), "Order summary", fill="#111827", font=font(24, True))
    d.text((70, 160), "Wireless Headphones x1", fill="#374151", font=font(20))
    d.text((700, 160), "INR 2,499", fill="#374151", font=font(20))
    d.line([70, 205, 830, 205], fill="#e5e7eb", width=2)
    d.text((70, 230), "Pay with", fill="#111827", font=font(22, True))
    d.rounded_rectangle([70, 285, 440, 365], 10, fill="#16a34a")
    d.text((190, 311), "Pay with UPI", fill="white", font=font(22, True))
    d.rounded_rectangle([460, 285, 830, 365], 10, fill="#2563eb")
    d.text((560, 311), "Pay with Card", fill="white", font=font(22, True))
    d.text((70, 410), "Total: INR 2,499", fill="#111827", font=font(26, True))
    d.text((70, 470), "Screenshot of staging build - UI state only", fill="#9ca3af", font=font(16))
    im.save(FX / "checkout.png")


if __name__ == "__main__":
    make_brd()
    make_screenshot()
    (FX / "client_note.txt").write_text(CLIENT_NOTE, encoding="utf-8")
    print("fixtures written to", FX.resolve())
