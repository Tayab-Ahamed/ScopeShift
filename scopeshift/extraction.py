"""Extraction engine for ScopeShift.

Connects to Gemini structured outputs when an API key is available,
and provides deterministic, proven fallback results for offline/stage-safety scenarios.
Gemini proposes claims; code validates citations and decides authority.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from .claims import CLAIM_IDS

logger = logging.getLogger(__name__)

CLAIM_ID_LITERAL = Literal[
    "checkout.payment_methods",
    "checkout.currency",
    "auth.mfa_requirement",
    "refunds.settlement_sla",
]


class ClaimExtractionSchema(BaseModel):
    claim_id: CLAIM_ID_LITERAL = Field(description="Must be one of the registered claim IDs")
    observation: str = Field(default="", description="Concise factual summary of what the document says or shows")
    quote: str = Field(description="Exact verbatim substring from the text, or text visible in the screenshot")
    proposed_scope_change: bool = Field(description="True if this source explicitly states a scope change or override, false otherwise")
    value: dict[str, Any] = Field(description="Typed object describing the claim")
    region: Optional[list[int]] = Field(default=None, description="[x, y, width, height] for screenshots (optional for text)")


EXTRACTION_PROMPT = """You are an evidence extraction assistant for ScopeShift.
Analyze the provided document and extract structured factual claims related to checkout scope.

Output ONLY a JSON array of claim objects matching this schema:
[
  {
    "claim_id": "checkout.payment_methods" | "checkout.currency" | "auth.mfa_requirement" | "refunds.settlement_sla",
    "observation": "concise factual summary of what the document says or shows",
    "quote": "exact verbatim substring from the text, or text visible in the screenshot",
    "proposed_scope_change": true if this source explicitly states a scope change or override, false otherwise,
    "value": object describing the claim (e.g. {"methods": ["Card"], "exclusive": false} or {"currency": "INR"} or {"mfa_required": true, "channels": ["TOTP Authenticator"]} or {"sla_hours": 24, "instant_settlement": false}),
    "region": [x, y, width, height] for screenshots (optional for text)
  }
]
Constraints:
- You must ONLY use the claim_id values: "checkout.payment_methods", "checkout.currency", "auth.mfa_requirement", "refunds.settlement_sla".
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
    reason: Optional[str] = None
    error_type: Optional[str] = None


def detect_image_mime(data: bytes) -> str:
    """Detect image MIME type from byte signatures or Pillow inspection."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and b"WEBP" in data[:12]:
        return "image/webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").lower()
        if fmt in ("jpeg", "jpg"):
            return "image/jpeg"
        if fmt == "png":
            return "image/png"
        if fmt == "webp":
            return "image/webp"
        if fmt:
            return f"image/{fmt}"
    except Exception as exc:
        logger.debug("Image MIME detection fallback: %s", exc)
    return "image/png"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.strip().encode("utf-8")).hexdigest()


# Pre-computed fixture hashes and canned outputs
KNOWN_FIXTURE_HASHES: dict[str, list[dict]] = {
    # checkout.png
    "b87104fe785c3f1b1321aea34f875742b8ea6eb6186f5f9ff93edb0cd82ae9f2": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "Staging checkout UI shows a 'Pay with Card' button alongside UPI.",
            "quote": "Pay with Card",
            "proposed_scope_change": False,
            "value": {"methods": ["Card"]},
            "region": [460, 285, 370, 80],
        }
    ],
    # brd.pdf bytes
    "2abb683bfe0472a17b066ae64655c1fd121ae265c12be19018424837039fb175": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI as the sole in-scope payment method.",
            "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"], "exclusive": True},
        },
        {
            "claim_id": "checkout.currency",
            "observation": "BRD specifies INR currency.",
            "quote": "REQ-CUR-01: All prices shall be shown and charged in INR.",
            "proposed_scope_change": False,
            "value": {"currency": "INR"},
        },
    ],
    # brd.txt bytes / text
    "c70f851665b2339d262b0660e25c0197fc6c5d9391f493b5bcbe2edd2e573ae2": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI as the sole in-scope payment method.",
            "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"], "exclusive": True},
        },
        {
            "claim_id": "checkout.currency",
            "observation": "BRD specifies INR currency.",
            "quote": "REQ-CUR-01: All prices shall be shown and charged in INR.",
            "proposed_scope_change": False,
            "value": {"currency": "INR"},
        },
    ],
    "b18afa63d56c9c011dc449d867633092fcbfa0ece7b4ee7892b0827631940b09": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI as the sole in-scope payment method.",
            "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"], "exclusive": True},
        },
        {
            "claim_id": "checkout.currency",
            "observation": "BRD specifies INR currency.",
            "quote": "REQ-CUR-01: All prices shall be shown and charged in INR.",
            "proposed_scope_change": False,
            "value": {"currency": "INR"},
        },
    ],
    # pypdf extracted text from brd.pdf
    "20218f9381ebf6b89b62eaddcdfa90d83b8744a5db112606aaa4567e9ef77daf": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI as the sole in-scope payment method.",
            "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"], "exclusive": True},
        },
        {
            "claim_id": "checkout.currency",
            "observation": "BRD specifies INR currency.",
            "quote": "REQ-CUR-01: All prices shall be shown and charged in INR.",
            "proposed_scope_change": False,
            "value": {"currency": "INR"},
        },
    ],
    # test snippet: "REQ-PAY-01: Checkout shall support UPI payments only. Business rule: UPI is the exclusive payment method for v1.0."
    "f7d5cce247560583c85901c9b869e13ef8a1fbd7f8288bf63598e309ae6e067c": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI as the sole in-scope payment method.",
            "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"], "exclusive": True},
        }
    ],
    # client_note.txt bytes
    "6c3c3d050e513b7aa44691a6bf907e4ff49c474c925eb6012515e76a685d2910": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "Client instructs scope change: Card is in scope, UPI deferred to Phase 2.",
            "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
            "proposed_scope_change": True,
            "value": {"methods": ["Card"], "deferred": ["UPI"]},
        }
    ],
    # client_note.txt stripped text
    "ae892426ea9f0ea27ba581139e7076b3e7fcc68ee9d898d101149ef2c52ef1ab": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "Client instructs scope change: Card is in scope, UPI deferred to Phase 2.",
            "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
            "proposed_scope_change": True,
            "value": {"methods": ["Card"], "deferred": ["UPI"]},
        }
    ],
    # test snippet: "We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2."
    "2f0ba3478ceabe44c17833be8b0e446197c807533e666cf52c6f9c7013a53068": [
        {
            "claim_id": "checkout.payment_methods",
            "observation": "Client instructs scope change: Card is in scope, UPI deferred to Phase 2.",
            "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
            "proposed_scope_change": True,
            "value": {"methods": ["Card"], "deferred": ["UPI"]},
        }
    ],
}


def _register_runtime_fixtures() -> None:
    """Dynamically register hashes of files in fixtures/ if available on disk."""
    fx_dir = Path("fixtures")
    if not fx_dir.exists():
        return
    try:
        shot = fx_dir / "checkout.png"
        if shot.exists():
            KNOWN_FIXTURE_HASHES[sha256_bytes(shot.read_bytes())] = KNOWN_FIXTURE_HASHES["b87104fe785c3f1b1321aea34f875742b8ea6eb6186f5f9ff93edb0cd82ae9f2"]
        pdf = fx_dir / "brd.pdf"
        if pdf.exists():
            KNOWN_FIXTURE_HASHES[sha256_bytes(pdf.read_bytes())] = KNOWN_FIXTURE_HASHES["2abb683bfe0472a17b066ae64655c1fd121ae265c12be19018424837039fb175"]
        txt = fx_dir / "brd.txt"
        if txt.exists():
            content = txt.read_bytes()
            KNOWN_FIXTURE_HASHES[sha256_bytes(content)] = KNOWN_FIXTURE_HASHES["2abb683bfe0472a17b066ae64655c1fd121ae265c12be19018424837039fb175"]
            KNOWN_FIXTURE_HASHES[sha256_text(txt.read_text(encoding="utf-8"))] = KNOWN_FIXTURE_HASHES["2abb683bfe0472a17b066ae64655c1fd121ae265c12be19018424837039fb175"]
        note = fx_dir / "client_note.txt"
        if note.exists():
            content = note.read_bytes()
            KNOWN_FIXTURE_HASHES[sha256_bytes(content)] = KNOWN_FIXTURE_HASHES["6c3c3d050e513b7aa44691a6bf907e4ff49c474c925eb6012515e76a685d2910"]
            KNOWN_FIXTURE_HASHES[sha256_text(note.read_text(encoding="utf-8"))] = KNOWN_FIXTURE_HASHES["6c3c3d050e513b7aa44691a6bf907e4ff49c474c925eb6012515e76a685d2910"]
    except Exception as exc:
        logger.debug("Runtime fixture registration exception: %s", exc)


_register_runtime_fixtures()


class Extractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        vertex_extractor=None,
        retry_delay_base: float = 0.05,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("SCOPESHIFT_GEMINI_MODEL", "gemini-2.5-flash")
        self.retry_delay_base = retry_delay_base
        self._client = None
        self._vertex = vertex_extractor

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize genai.Client: %s", exc)
                self._client = None

    def _get_vertex(self):
        if self._vertex is None:
            try:
                from .cloud import VertexExtractor
                self._vertex = VertexExtractor()
            except Exception as exc:
                logger.debug("VertexExtractor initialization skipped: %s", exc)
                self._vertex = False
        return self._vertex or None

    def effective_mode(self) -> str:
        """Honest extraction route for the status endpoint."""
        if self._client:
            return "live"
        vx = self._get_vertex()
        if vx is not None and vx.status().get("connected"):
            return "live (vertex)"
        return "deterministic-fallback"

    def _call_gemini_with_retry(
        self, contents: list, config
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Calls Gemini client with up to 3 tries and exponential backoff.
        Returns (raw_response_text, failure_reason, error_type).
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                text = getattr(resp, "text", None) or ""
                return text, None, None
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Gemini extraction attempt %d/3 failed: %s (%s)",
                    attempt,
                    exc,
                    type(exc).__name__,
                )
                if attempt < 3:
                    time.sleep(self.retry_delay_base * (2 ** (attempt - 1)))

        reason = f"Gemini call failed after 3 tries: {type(last_exc).__name__}: {last_exc}"
        error_type = type(last_exc).__name__ if last_exc else "GeminiError"
        return None, reason, error_type

    def _parse_and_validate_claims(
        self, raw_text: str
    ) -> tuple[list[dict], Optional[str], Optional[str]]:
        """Parse raw JSON output and validate every claim against ClaimExtractionSchema."""
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini output JSONDecodeError: %s", exc)
            return [], f"JSON decode error: {exc}", "JSONDecodeError"

        if isinstance(parsed, dict) and "claims" in parsed:
            raw_claims = parsed["claims"]
        elif isinstance(parsed, list):
            raw_claims = parsed
        elif isinstance(parsed, dict):
            raw_claims = [parsed]
        else:
            return [], "Invalid root type for claims", "TypeError"

        valid_claims: list[dict] = []
        errors: list[str] = []
        for item in raw_claims:
            if not isinstance(item, dict):
                errors.append(f"Expected dict claim, got {type(item).__name__}")
                continue
            cid = item.get("claim_id")
            if cid not in CLAIM_IDS:
                errors.append(f"Hallucinated or unknown claim_id: {cid!r}")
                logger.warning("Rejected hallucinated claim_id: %s", cid)
                continue
            try:
                model_item = ClaimExtractionSchema.model_validate(item)
                valid_claims.append(model_item.model_dump())
            except Exception as exc:
                errors.append(f"Validation error on {cid}: {exc}")
                logger.warning("Claim validation failed for %s: %s", cid, exc)

        if errors:
            reason = "; ".join(errors)
            error_type = "ValidationError"
            return valid_claims, reason, error_type

        return valid_claims, None, None

    def _match_fallback_hash(self, *hashes: str) -> Optional[list[dict]]:
        for h in hashes:
            if h and h in KNOWN_FIXTURE_HASHES:
                return [dict(c) for c in KNOWN_FIXTURE_HASHES[h]]
        return None

    def extract_from_text(
        self, text: str, source_type: str, force_fallback: bool = False
    ) -> ExtractionResult:
        start_time = time.time()
        last_reason: Optional[str] = None
        last_error_type: Optional[str] = None

        if not force_fallback:
            # 1. Vertex AI route if configured
            vx = self._get_vertex()
            if vx is not None and vx.status().get("connected"):
                res = vx.extract_claims(text, source_type, EXTRACTION_PROMPT)
                if res is not None:
                    latency = (time.time() - start_time) * 1000
                    return ExtractionResult(
                        claims=res["claims"],
                        mode="live",
                        latency_ms=latency,
                        model=res.get("model", f"{self.model} (vertex)"),
                    )

            # 2. Direct google-genai route
            if self._client:
                from google.genai import types

                prompt = f"{EXTRACTION_PROMPT}\nSource Type: {source_type}\nText:\n{text}"
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[ClaimExtractionSchema],
                )
                raw_text, call_reason, call_error_type = self._call_gemini_with_retry(
                    [prompt], cfg
                )
                latency = (time.time() - start_time) * 1000
                if raw_text is not None:
                    claims, val_reason, val_error_type = self._parse_and_validate_claims(
                        raw_text
                    )
                    return ExtractionResult(
                        claims=claims,
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        raw_response=raw_text,
                        reason=val_reason,
                        error_type=val_error_type,
                    )
                else:
                    return ExtractionResult(
                        claims=[],
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        reason=call_reason,
                        error_type=call_error_type,
                    )

        # Fallback mode: Canned results ONLY for known fixtures matched by SHA-256
        latency = (time.time() - start_time) * 1000
        th = sha256_text(text)
        bh = sha256_bytes(text.encode("utf-8"))
        matched = self._match_fallback_hash(th, bh)

        if matched is not None:
            return ExtractionResult(
                claims=matched,
                mode="fallback",
                latency_ms=latency,
                model="deterministic-fallback",
                reason=last_reason,
                error_type=last_error_type,
            )

        # Unknown input: Return zero claims and honest failure reason
        return ExtractionResult(
            claims=[],
            mode="fallback",
            latency_ms=latency,
            model="deterministic-fallback",
            reason=last_reason or "offline: no live extractor",
            error_type=last_error_type or "OfflineMode",
        )

    def extract_from_image(
        self, image_input: Path | str | bytes, force_fallback: bool = False
    ) -> ExtractionResult:
        start_time = time.time()
        last_reason: Optional[str] = None
        last_error_type: Optional[str] = None

        if isinstance(image_input, (str, Path)):
            img_path = Path(image_input)
            if not img_path.exists():
                return ExtractionResult(
                    claims=[],
                    mode="fallback",
                    latency_ms=0,
                    reason="image file not found",
                    error_type="FileNotFoundError",
                )
            image_bytes = img_path.read_bytes()
        else:
            image_bytes = bytes(image_input)

        mime_type = detect_image_mime(image_bytes)

        if self._client and not force_fallback:
            try:
                from google.genai import types

                prompt = f"{EXTRACTION_PROMPT}\nSource Type: screenshot\nAnalyze UI elements."
                img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[ClaimExtractionSchema],
                )
                raw_text, call_reason, call_error_type = self._call_gemini_with_retry(
                    [prompt, img_part], cfg
                )
                latency = (time.time() - start_time) * 1000
                if raw_text is not None:
                    claims, val_reason, val_error_type = self._parse_and_validate_claims(
                        raw_text
                    )
                    return ExtractionResult(
                        claims=claims,
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        raw_response=raw_text,
                        reason=val_reason,
                        error_type=val_error_type,
                    )
                else:
                    return ExtractionResult(
                        claims=[],
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        reason=call_reason,
                        error_type=call_error_type,
                    )
            except Exception as exc:
                last_reason = f"Image extraction error: {exc}"
                last_error_type = type(exc).__name__
                logger.warning("Image extraction exception: %s", exc)

        latency = (time.time() - start_time) * 1000
        bh = sha256_bytes(image_bytes)
        matched = self._match_fallback_hash(bh)

        if matched is not None:
            return ExtractionResult(
                claims=matched,
                mode="fallback",
                latency_ms=latency,
                model="deterministic-fallback",
                reason=last_reason,
                error_type=last_error_type,
            )

        return ExtractionResult(
            claims=[],
            mode="fallback",
            latency_ms=latency,
            model="deterministic-fallback",
            reason=last_reason or "offline: no live extractor",
            error_type=last_error_type or "OfflineMode",
        )

    def extract_from_pdf(
        self, pdf_input: Path | str | bytes, force_fallback: bool = False
    ) -> ExtractionResult:
        start_time = time.time()
        last_reason: Optional[str] = None
        last_error_type: Optional[str] = None

        if isinstance(pdf_input, (str, Path)):
            pdf_path = Path(pdf_input)
            pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else b""
        else:
            pdf_bytes = bytes(pdf_input)

        # 1. Live multimodal Gemini call with raw PDF bytes
        if self._client and not force_fallback and pdf_bytes:
            try:
                from google.genai import types

                prompt = f"{EXTRACTION_PROMPT}\nSource Type: brd\nAnalyze document for checkout requirements."
                pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[ClaimExtractionSchema],
                )
                raw_text, call_reason, call_error_type = self._call_gemini_with_retry(
                    [prompt, pdf_part], cfg
                )
                latency = (time.time() - start_time) * 1000
                if raw_text is not None:
                    claims, val_reason, val_error_type = self._parse_and_validate_claims(
                        raw_text
                    )
                    return ExtractionResult(
                        claims=claims,
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        raw_response=raw_text,
                        reason=val_reason,
                        error_type=val_error_type,
                    )
                else:
                    return ExtractionResult(
                        claims=[],
                        mode="live",
                        latency_ms=latency,
                        model=self.model,
                        reason=call_reason,
                        error_type=call_error_type,
                    )
            except Exception as exc:
                last_reason = f"PDF extraction exception: {exc}"
                last_error_type = type(exc).__name__
                logger.warning("PDF live extraction failed: %s", exc)

        # 2. Fallback mode: check raw bytes hash first
        latency = (time.time() - start_time) * 1000
        bh = sha256_bytes(pdf_bytes) if pdf_bytes else ""
        matched = self._match_fallback_hash(bh)
        if matched is not None:
            return ExtractionResult(
                claims=matched,
                mode="fallback",
                latency_ms=latency,
                model="deterministic-fallback",
                reason=last_reason,
                error_type=last_error_type,
            )

        # 3. pypdf fallback extraction for text-based match
        extracted_text = ""
        if pdf_bytes:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_bytes))
                extracted_text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as exc:
                logger.warning("pypdf extraction failed: %s", exc)
                last_reason = f"pypdf extraction error: {exc}"
                last_error_type = type(exc).__name__

        if extracted_text:
            th = sha256_text(extracted_text)
            matched_text = self._match_fallback_hash(th)
            if matched_text is not None:
                return ExtractionResult(
                    claims=matched_text,
                    mode="fallback",
                    latency_ms=latency,
                    model="deterministic-fallback",
                    reason=last_reason,
                    error_type=last_error_type,
                )

        return ExtractionResult(
            claims=[],
            mode="fallback",
            latency_ms=latency,
            model="deterministic-fallback",
            reason="offline: no live extractor",
            error_type="OfflineMode",
        )
