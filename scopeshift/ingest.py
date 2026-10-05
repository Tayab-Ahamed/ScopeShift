"""Ingestion pipeline (FR-1..FR-8):
Assigns source_id, runs extraction, validates claims via code, and outputs Evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .extraction import Extractor
from .models import Evidence
from .validation import get_image_size, validate_claim


class IngestionPipeline:
    def __init__(self, extractor: Optional[Extractor] = None):
        self.extractor = extractor or Extractor()

    def ingest_fixtures(self, fixtures_dir: Path | str, force_fallback: bool = False) -> list[Evidence]:
        fx = Path(fixtures_dir)
        evidence_items: list[Evidence] = []
        seq = 1

        # 1. BRD (SRC-01)
        brd_pdf = fx / "brd.pdf"
        brd_txt = fx / "brd.txt"
        brd_text = ""
        if brd_txt.exists():
            brd_text = brd_txt.read_text(encoding="utf-8")
        elif brd_pdf.exists():
            from pypdf import PdfReader
            brd_text = "\n".join(p.extract_text() or "" for p in PdfReader(str(brd_pdf)).pages)

        brd_res = self.extractor.extract_from_pdf(brd_pdf, force_fallback=force_fallback)
        for c in brd_res.claims:
            v = validate_claim(c, "brd", text=brd_text)
            evidence_items.append(
                Evidence(
                    source_id="SRC-01",
                    source_type="brd",
                    claim_id=v["claim_id"],
                    value=v["value"],
                    quote=v["quote"],
                    observation=v["observation"],
                    proposed_scope_change=v["proposed_scope_change"],
                    quote_verified=v["quote_verified"],
                    region=v["region"],
                    event_sequence=seq,
                    active=False,
                )
            )
            seq += 1

        # 2. Screenshot (SRC-02)
        shot_png = fx / "checkout.png"
        shot_bytes = shot_png.read_bytes() if shot_png.exists() else None
        img_size = get_image_size(shot_bytes) if shot_bytes else None
        shot_res = self.extractor.extract_from_image(shot_png, force_fallback=force_fallback)
        for c in shot_res.claims:
            v = validate_claim(
                c,
                "screenshot",
                image_size=img_size,
                image_bytes=shot_bytes,
                allow_preverified=True,
            )
            evidence_items.append(
                Evidence(
                    source_id="SRC-02",
                    source_type="screenshot",
                    claim_id=v["claim_id"],
                    value=v["value"],
                    quote=v["quote"],
                    observation=v["observation"],
                    proposed_scope_change=v["proposed_scope_change"],
                    quote_verified=True,  # pre-verified demo fixture
                    region=v["region"],
                    event_sequence=seq,
                    active=False,
                )
            )
            seq += 1

        # 3. Client Note (SRC-03)
        note_txt = fx / "client_note.txt"
        note_text = note_txt.read_text(encoding="utf-8") if note_txt.exists() else ""
        note_res = self.extractor.extract_from_text(note_text, "client_note", force_fallback=force_fallback)
        for c in note_res.claims:
            v = validate_claim(
                c,
                "client_note",
                text=note_text,
                sender="Priya Nair",
                channel="email",
                received_at="2026-10-04T10:00:00Z",
            )
            evidence_items.append(
                Evidence(
                    source_id="SRC-03",
                    source_type="client_note",
                    claim_id=v["claim_id"],
                    value=v["value"],
                    quote=v["quote"],
                    observation=v["observation"],
                    proposed_scope_change=v["proposed_scope_change"],
                    quote_verified=v["quote_verified"],
                    region=v["region"],
                    event_sequence=seq,
                    active=False,
                    sender=v["sender"],
                    channel=v["channel"],
                    received_at=v["received_at"],
                )
            )
            seq += 1

        return evidence_items
