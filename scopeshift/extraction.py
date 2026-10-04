"""Extraction engine for ScopeShift.

Connects to Gemini structured outputs when an API key is available,
and provides deterministic, proven fallback results for offline/stage-safety scenarios.
Gemini proposes claims; code validates citations and decides authority.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .claims import CLAIM_IDS


EXTRACTION_PROMPT = """You are an evidence extraction assistant for ScopeShift.
Analyze the provided document and extract structured factual claims related to checkout scope.

Output ONLY a JSON array of claim objects matching this schema:
[
  {
    "claim_id": "checkout.payment_methods" or "checkout.currency",
    "observation": "concise factual summary of what the document says or shows",
    "quote": "exact verbatim substring from the text, or text visible in the screenshot",
    "proposed_scope_change": true if this source explicitly states a scope change or override, false otherwise,
    "value": object describing the claim (e.g. {"methods": ["Card"], "exclusive": false} or {"currency": "INR"}),
    "region": [x, y, width, height] for screenshots (optional for text)
  }
]
Constraints:
- You must ONLY use the claim_id values: "checkout.payment_methods" or "checkout.currency".
- The quote MUST be an exact verbatim substring from the document.
- Only mark proposed_scope_change: true if the text explicitly states scope change.
"""


@dataclass
class ExtractionResult:
    claims: list[dict]
    mode: str  # "live" or "fallback"
    latency_ms: float
    model: Optional[str] = None
    raw_response: Optional[str] = None


class Extractor:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    def extract_from_text(self, text: str, source_type: str, force_fallback: bool = False) -> ExtractionResult:
        start_time = time.time()
        if self._client and not force_fallback:
            try:
                from google.genai import types
                prompt = f"{EXTRACTION_PROMPT}\nSource Type: {source_type}\nText:\n{text}"
                cfg = types.GenerateContentConfig(response_mime_type="application/json")
                resp = self._client.models.generate_content(model=self.model, contents=[prompt], config=cfg)
                claims = json.loads(resp.text)
                latency = (time.time() - start_time) * 1000
                return ExtractionResult(claims=claims, mode="live", latency_ms=latency, model=self.model, raw_response=resp.text)
            except Exception:
                pass  # Fall through to fallback on stage / network error

        # Deterministic proven fallback
        latency = (time.time() - start_time) * 1000
        claims = self._fallback_text(text, source_type)
        return ExtractionResult(claims=claims, mode="fallback", latency_ms=latency, model="deterministic-fallback")

    def extract_from_image(self, image_path: Path | str, force_fallback: bool = False) -> ExtractionResult:
        start_time = time.time()
        image_path = Path(image_path)
        if self._client and not force_fallback and image_path.exists():
            try:
                from google.genai import types
                prompt = f"{EXTRACTION_PROMPT}\nSource Type: screenshot\nAnalyze UI elements."
                img_part = types.Part.from_bytes(data=image_path.read_bytes(), mime_type="image/png")
                cfg = types.GenerateContentConfig(response_mime_type="application/json")
                resp = self._client.models.generate_content(model=self.model, contents=[prompt, img_part], config=cfg)
                claims = json.loads(resp.text)
                latency = (time.time() - start_time) * 1000
                return ExtractionResult(claims=claims, mode="live", latency_ms=latency, model=self.model, raw_response=resp.text)
            except Exception:
                pass

        latency = (time.time() - start_time) * 1000
        claims = [
            {
                "claim_id": "checkout.payment_methods",
                "observation": "Staging checkout UI shows a 'Pay with Card' button alongside UPI.",
                "quote": "Pay with Card",
                "proposed_scope_change": False,
                "value": {"methods": ["Card"]},
                "region": [460, 285, 370, 80],
            }
        ]
        return ExtractionResult(claims=claims, mode="fallback", latency_ms=latency, model="deterministic-fallback")

    def extract_from_pdf(self, pdf_path: Path | str, force_fallback: bool = False) -> ExtractionResult:
        pdf_path = Path(pdf_path)
        text = ""
        if pdf_path.exists():
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception:
                text = ""
        if not text:
            txt_path = pdf_path.with_suffix(".txt")
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8")
        return self.extract_from_text(text, "brd", force_fallback=force_fallback)

    def _fallback_text(self, text: str, source_type: str) -> list[dict]:
        claims = []
        if source_type == "brd":
            if "UPI" in text:
                claims.append({
                    "claim_id": "checkout.payment_methods",
                    "observation": "BRD specifies UPI as the sole in-scope payment method.",
                    "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
                    "proposed_scope_change": False,
                    "value": {"methods": ["UPI"], "exclusive": True},
                })
            if "INR" in text:
                claims.append({
                    "claim_id": "checkout.currency",
                    "observation": "BRD specifies INR currency.",
                    "quote": "REQ-CUR-01: All prices shall be shown and charged in INR.",
                    "proposed_scope_change": False,
                    "value": {"currency": "INR"},
                })
        elif source_type == "client_note":
            claims.append({
                "claim_id": "checkout.payment_methods",
                "observation": "Client instructs scope change: Card is in scope, UPI deferred to Phase 2.",
                "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
                "proposed_scope_change": True,
                "value": {"methods": ["Card"], "deferred": ["UPI"]},
            })
        return claims
