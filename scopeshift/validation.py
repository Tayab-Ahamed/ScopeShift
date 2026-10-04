"""Code-level validation: schema, quotes, screenshot regions, citations. Gemini output is untrusted input."""
from __future__ import annotations

import struct
import unicodedata

from .claims import SPECS, SOURCE_TYPES, ClaimValueError

_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})
MAX_QUOTE = 600


class ValidationError(ValueError):
    pass


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    return " ".join(text.casefold().split())


def quote_in_text(quote: str, text: str) -> bool:
    q = normalize(quote or "")
    return bool(q) and q in normalize(text or "")


def png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValidationError("screenshot must be a PNG image")
    return struct.unpack(">II", data[16:24])


def _region_ok(region, size) -> tuple | None:
    if size is None or not isinstance(region, (list, tuple)) or len(region) != 4:
        return None
    if not all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in region):
        return None
    x, y, w, h = region
    width, height = size
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
        return None
    return tuple(region)


def validate_claim(raw, source_type: str, *, text: str | None = None, image_size=None) -> dict:
    """Validate one model-proposed claim. Raises ValidationError for unusable claims (hallucinated
    claim_id, malformed value). A claim whose citation cannot be verified is kept but unverified,
    so it is shown to the user and can never govern."""
    if source_type not in SOURCE_TYPES:
        raise ValidationError(f"unknown source_type: {source_type!r}")
    if not isinstance(raw, dict):
        raise ValidationError("claim must be an object")
    spec = SPECS.get(raw.get("claim_id"))
    if spec is None:
        raise ValidationError(f"claim_id outside schema: {raw.get('claim_id')!r}")
    try:
        value = spec.normalize(raw.get("value"))
    except ClaimValueError as exc:
        raise ValidationError(f"{spec.claim_id}: {exc}") from exc
    quote = raw.get("quote")
    if not isinstance(quote, str):
        raise ValidationError("quote must be a string")
    quote = quote.strip()[:MAX_QUOTE]
    observation = str(raw.get("observation") or "")[:300]

    region = None
    if source_type == "screenshot":
        region = _region_ok(raw.get("region"), image_size)
        verified = region is not None and bool(quote)
    else:
        if text is None:
            raise ValidationError("source text is required to verify quotes")
        verified = quote_in_text(quote, text)
    scope = bool(raw.get("proposed_scope_change")) and source_type == "client_note"
    return {"claim_id": spec.claim_id, "value": value, "quote": quote, "observation": observation,
            "proposed_scope_change": scope, "quote_verified": verified, "region": region}


def validate_citations(resolutions, active_evidence) -> None:
    """FR-8/FR-18: every citation of a requirement in the current BRD must reference active evidence."""
    active_ids = {e.source_id for e in active_evidence if e.active}
    for res in resolutions:
        if not res.in_brd:
            continue
        if not res.citations:
            raise ValidationError(f"{res.claim_id}: requirement has no citations")
        for c in res.citations:
            if c.get("source_id") not in active_ids:
                raise ValidationError(f"{res.claim_id}: citation {c.get('source_id')!r} is not active evidence")
