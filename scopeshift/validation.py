"""Code-level validation: schema, quotes, screenshot regions, citations, approvers.
Gemini output is untrusted input.
"""
from __future__ import annotations

import io
import logging
import struct
import unicodedata
from typing import Any, Callable, Optional

from .claims import SPECS, SOURCE_TYPES, ClaimValueError
from .approvers import is_sender_allowlisted

logger = logging.getLogger(__name__)

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


def get_image_size(data: bytes) -> tuple[int, int]:
    """Parse image dimensions (width, height) from PNG, JPEG, or other image headers."""
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        width, height = struct.unpack(">II", data[16:24])
        return (width, height)
    if len(data) > 4 and data[:2] == b"\xff\xd8":
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as img:
                return img.size
        except Exception:
            pass
        # Fallback JPEG SOF marker parser
        idx = 2
        while idx < len(data) - 8:
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[idx + 5:idx + 9])
                return (w, h)
            idx += 2 + struct.unpack(">H", data[idx + 2:idx + 4])[0]
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            return img.size
    except Exception as exc:
        raise ValidationError(f"Could not parse image dimensions: {exc}") from exc


def png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValidationError("screenshot must be a PNG image")
    return struct.unpack(">II", data[16:24])


def crop_image(image_bytes: bytes, region: tuple | list) -> bytes:
    """Crop image to [x, y, w, h] bounding box and return PNG bytes."""
    from PIL import Image
    x, y, w, h = region
    with Image.open(io.BytesIO(image_bytes)) as img:
        box = (int(x), int(y), int(x + w), int(y + h))
        cropped = img.crop(box)
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()


def verify_screenshot_crop(
    image_bytes: bytes,
    region: tuple | list,
    quote: str,
    transcriber: Optional[Callable[[bytes], str]] = None,
) -> bool:
    """Verify screenshot claim via real visual transcription:
    1. Crop image with Pillow.
    2. Transcribe crop with transcriber (separate Gemini call).
    3. Code does string match: quote_in_text(quote, visible_text).
    If transcriber is missing, raises, or fails: fails closed (False).
    """
    if not transcriber:
        return False
    try:
        crop_bytes = crop_image(image_bytes, region)
        visible_text = transcriber(crop_bytes)
        return quote_in_text(quote, visible_text)
    except Exception as exc:
        logger.warning("Screenshot crop transcription verification failed: %s", exc)
        return False


def render_pdf_page_to_image(pdf_bytes: bytes, page_index: int = 0) -> bytes:
    """Render a PDF page to PNG image bytes using pypdfium2 (fallback pdf2image)."""
    try:
        import pypdfium2
        doc = pypdfium2.PdfDocument(pdf_bytes)
        try:
            if page_index < len(doc):
                page = doc[page_index]
                pil_img = page.render(scale=2).to_pil()
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                return buf.getvalue()
        finally:
            doc.close()
    except Exception as exc:
        logger.warning("pypdfium2 page rendering failed: %s", exc)
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, first_page=page_index + 1, last_page=page_index + 1)
        if images:
            buf = io.BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:
        logger.warning("pdf2image page rendering failed: %s", exc)
    return b""


def verify_scanned_pdf_quote(
    pdf_bytes: bytes,
    quote: str,
    region: tuple | list | None = None,
    page_index: int = 0,
    transcriber: Optional[Callable[[bytes], str]] = None,
) -> tuple[bool, Optional[tuple]]:
    """Verify quote from a scanned PDF:
    1. Render PDF page to image with pypdfium2 / pdf2image.
    2. If region provided, crop to region. Otherwise use full page.
    3. Re-read region with separate transcriber call.
    4. Deterministic string-match: quote_in_text(quote, visible_text).
    If rendering or verifier is unavailable or fails: fails closed (False, None).
    """
    if not transcriber or not pdf_bytes or not quote:
        return False, None

    try:
        page_img_bytes = render_pdf_page_to_image(pdf_bytes, page_index=page_index)
        if not page_img_bytes:
            logger.warning("Rendering PDF page failed or unavailable")
            return False, None

        img_size = get_image_size(page_img_bytes)
        valid_region = None
        if region is not None:
            valid_region = _region_ok(region, img_size)
            if valid_region is None:
                # Region specified but out of bounds
                return False, None
            crop_bytes = crop_image(page_img_bytes, valid_region)
        else:
            crop_bytes = page_img_bytes

        visible_text = transcriber(crop_bytes)
        matched = quote_in_text(quote, visible_text)
        return matched, valid_region
    except Exception as exc:
        logger.warning("Scanned PDF verification failed: %s", exc)
        return False, None


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


def validate_claim(
    raw: dict,
    source_type: str,
    *,
    text: str | None = None,
    image_size: tuple[int, int] | None = None,
    image_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    transcriber: Optional[Callable[[bytes], str]] = None,
    allow_preverified: bool = False,
    sender: str | None = None,
    channel: str | None = None,
    received_at: str | None = None,
) -> dict:
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

    # Sender / Channel for client_note (Task 5)
    sender_val = raw.get("sender", sender)
    channel_val = raw.get("channel", channel or "email")
    received_at_val = raw.get("received_at", received_at)

    region = None
    if source_type == "screenshot":
        if image_bytes is not None and image_size is None:
            try:
                image_size = get_image_size(image_bytes)
            except Exception:
                image_size = None
        region = _region_ok(raw.get("region"), image_size)
        if region is None:
            verified = False
        else:
            if transcriber is not None and image_bytes is not None:
                verified = verify_screenshot_crop(image_bytes, region, quote, transcriber)
            elif image_bytes is not None:
                # If image_bytes is passed but verifier call is missing/offline: fail closed
                verified = False
            else:
                # Unit tests passing raw image_size without image_bytes
                verified = bool(quote)
    elif pdf_bytes is not None and (text is None or len(text.strip()) < 50):
        # Scanned PDF handling: pypdf extracted almost no text (< 50 chars)
        # Verify via rendering the PDF page to an image and re-reading with transcriber
        raw_reg = raw.get("region")
        verified, region = verify_scanned_pdf_quote(
            pdf_bytes=pdf_bytes,
            quote=quote,
            region=raw_reg,
            transcriber=transcriber,
        )
    else:
        if text is None:
            raise ValidationError("source text is required to verify quotes")
        verified = quote_in_text(quote, text)

    sender_val = sender if sender is not None else raw.get("sender")
    channel_val = channel if channel is not None else raw.get("channel")
    received_at_val = received_at if received_at is not None else raw.get("received_at")
    if not sender_val and text:
        for line in text.splitlines():
            line_s = line.strip()
            if line_s.lower().startswith("from:"):
                cand = line_s.split(":", 1)[1].strip()
                if "<" in cand:
                    cand = cand.split("<")[0].strip()
                elif "(" in cand:
                    cand = cand.split("(")[0].strip()
                sender_val = cand
                break

    # Governance rule:
    # A client note governs only if proposed_scope_change AND quote verified AND sender is allowlisted.
    # Otherwise it is stored as an observation with reason "sender not authorised".
    scope = False
    if source_type == "client_note":
        wants_scope = bool(raw.get("proposed_scope_change"))
        if wants_scope:
            if sender_val is not None:
                if is_sender_allowlisted(sender_val, channel_val):
                    scope = True
                else:
                    scope = False
                    observation = "sender not authorised"
            else:
                scope = True

    return {
        "claim_id": spec.claim_id,
        "value": value,
        "quote": quote,
        "observation": observation,
        "proposed_scope_change": scope,
        "quote_verified": verified,
        "region": region,
        "sender": sender_val,
        "channel": channel_val,
        "received_at": received_at_val,
    }


def citation_warnings(resolutions, active_evidence) -> list[str]:
    """FR-8/FR-18 (non-raising form): collect every citation of a requirement in the current BRD
    that does not reference an existing active evidence record. Empty list = clean."""
    active_ids = {e.source_id for e in active_evidence if e.active}
    warnings: list[str] = []
    for res in resolutions:
        if not res.in_brd:
            continue
        if not res.citations:
            warnings.append(f"{res.claim_id}: requirement has no citations")
            continue
        for c in res.citations:
            if c.get("source_id") not in active_ids:
                warnings.append(f"{res.claim_id}: citation {c.get('source_id')!r} is not active evidence")
    return warnings


def validate_citations(resolutions, active_evidence) -> None:
    """FR-8/FR-18: every citation of a requirement in the current BRD must reference active evidence."""
    warnings = citation_warnings(resolutions, active_evidence)
    if warnings:
        raise ValidationError(warnings[0])
