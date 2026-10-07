"""Live smoke test probe for ScopeShift Gemini extraction.

Executes:
1. One real live text extraction call.
2. One real live PDF extraction call (using fixtures/brd.pdf).
3. One real live image extraction call (using fixtures/checkout.png).

Prints the model used for each call and exits non-zero (1) on any failure.
Requires GEMINI_API_KEY environment variable. Never fabricates passes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scopeshift.extraction import Extractor


def run_smoke() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY is not set.\n"
            "Live smoke probe requires a valid Gemini API key.\n"
            "Set GEMINI_API_KEY and re-run.",
            file=sys.stderr,
        )
        return 1

    model = os.environ.get("SCOPESHIFT_GEMINI_MODEL", "gemini-3.6-flash")
    raw_fb = os.environ.get("SCOPESHIFT_GEMINI_FALLBACKS", "gemini-3.5-flash")
    if "--no-fallbacks" in sys.argv or raw_fb.strip().lower() in ("none", "off", "0", ""):
        fallbacks = ""
        fb_list = []
    else:
        fallbacks = raw_fb
        fb_list = [m.strip() for m in fallbacks.split(",") if m.strip()]

    print(f"ScopeShift Live Smoke Probe")
    print(f"Target model: {model} (fallbacks: {fallbacks})")
    print("-" * 50)

    extractor = Extractor(api_key=api_key, model=model, fallbacks=fb_list)
    if not extractor._client:
        print("ERROR: Failed to initialize Gemini client.", file=sys.stderr)
        return 1

    fixtures_dir = REPO_ROOT / "fixtures"
    pdf_path = fixtures_dir / "brd.pdf"
    img_path = fixtures_dir / "checkout.png"

    if not pdf_path.exists():
        print(f"ERROR: Required fixture missing: {pdf_path}", file=sys.stderr)
        return 1
    if not img_path.exists():
        print(f"ERROR: Required fixture missing: {img_path}", file=sys.stderr)
        return 1

    # 1. Real Live Text Extraction Call
    print("[1/3] Probing live text extraction...")
    sample_text = (
        "Checkout Specification v1.0:\n"
        "REQ-PAY-01: Checkout shall support Card and UPI payments.\n"
        "REQ-CUR-01: Prices are charged in INR.\n"
    )
    res_text = extractor.extract_from_text(sample_text, source_type="brd")
    if res_text.mode != "live" or res_text.error_type is not None or not res_text.claims:
        print(
            f"FAIL: Text extraction failed.\n"
            f"  Mode: {res_text.mode}\n"
            f"  Model reported: {res_text.model}\n"
            f"  Claims count: {len(res_text.claims)}\n"
            f"  Error: {res_text.error_type}: {res_text.reason}",
            file=sys.stderr,
        )
        return 1
    print(f"  PASS: Text call succeeded.")
    print(f"  Model used: {res_text.model}")
    print(f"  Claims extracted: {len(res_text.claims)} (latency: {res_text.latency_ms:.1f}ms)\n")

    # 2. Real Live PDF Extraction Call
    print("[2/3] Probing live PDF extraction (fixtures/brd.pdf)...")
    res_pdf = extractor.extract_from_pdf(pdf_path)
    if res_pdf.mode != "live" or res_pdf.error_type is not None or not res_pdf.claims:
        print(
            f"FAIL: PDF extraction failed.\n"
            f"  Mode: {res_pdf.mode}\n"
            f"  Model reported: {res_pdf.model}\n"
            f"  Claims count: {len(res_pdf.claims)}\n"
            f"  Error: {res_pdf.error_type}: {res_pdf.reason}",
            file=sys.stderr,
        )
        return 1
    print(f"  PASS: PDF call succeeded.")
    print(f"  Model used: {res_pdf.model}")
    print(f"  Claims extracted: {len(res_pdf.claims)} (latency: {res_pdf.latency_ms:.1f}ms)\n")

    # 3. Real Live Image Extraction Call
    print("[3/3] Probing live Image extraction (fixtures/checkout.png)...")
    res_img = extractor.extract_from_image(img_path)
    if res_img.mode != "live" or res_img.error_type is not None or not res_img.claims:
        print(
            f"FAIL: Image extraction failed.\n"
            f"  Mode: {res_img.mode}\n"
            f"  Model reported: {res_img.model}\n"
            f"  Claims count: {len(res_img.claims)}\n"
            f"  Error: {res_img.error_type}: {res_img.reason}",
            file=sys.stderr,
        )
        return 1
    print(f"  PASS: Image call succeeded.")
    print(f"  Model used: {res_img.model}")
    print(f"  Claims extracted: {len(res_img.claims)} (latency: {res_img.latency_ms:.1f}ms)\n")

    print("-" * 50)
    print("ALL 3 SMOKE PROBES PASSED (Text, PDF, Image). Live Gemini operational.")
    return 0


if __name__ == "__main__":
    pre_fb = os.environ.get("SCOPESHIFT_GEMINI_FALLBACKS")
    if (REPO_ROOT / ".env").exists():
        try:
            import dotenv
            dotenv.load_dotenv(REPO_ROOT / ".env")
            if pre_fb is not None:
                os.environ["SCOPESHIFT_GEMINI_FALLBACKS"] = pre_fb
        except Exception:
            pass
    sys.exit(run_smoke())
