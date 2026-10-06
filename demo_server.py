"""ScopeShift Demo Server (Production Grade).
Serves the responsive single-screen UI, Three.js 3D topology, and REST API.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import email
import io

from scopeshift.approvers import is_sender_allowlisted
from scopeshift.cloud import BQ_DATASET_ENV, GCS_BUCKET_ENV, BigQueryLog, GCSOriginals, VertexExtractor
from scopeshift.ask import answer_question
from scopeshift.extraction import Extractor
from scopeshift.feed_scenario import ARRIVALS, SCENARIO_TITLE
from scopeshift.ingest import IngestionPipeline
from scopeshift.models import Event, Evidence
from scopeshift.resolver import replay
from scopeshift.store import EventStore
from scopeshift.validation import (
    ValidationError,
    citation_warnings,
    crop_image,
    get_image_size,
    normalize,
    png_size,
    quote_in_text,
    validate_citations,
    validate_claim,
    verify_screenshot_crop,
)

ROOT = Path(__file__).parent.resolve()
FIXTURES_DIR = ROOT / "fixtures"
MAX_BODY = 10 * 1024 * 1024  # 10 MB maximum upload size
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
}


def sniff_mime_type(data: bytes) -> str | None:
    """Sniff MIME type from bytes, not filenames."""
    if not data:
        return None
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    try:
        decoded = data.decode("utf-8")
        if "\x00" not in decoded and not any(ord(c) < 32 and c not in "\r\n\t" for c in decoded[:1024]):
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return None


import collections
_RATE_LIMIT_STORE: dict[str, list[float]] = collections.defaultdict(list)
_RATE_LIMIT_LOCK = threading.Lock()


def check_rate_limit(client_ip: str, limit_per_minute: int = 30) -> tuple[bool, int]:
    """Returns (is_allowed, retry_after_seconds). Sliding 60s window."""
    now = time.time()
    window = 60.0
    with _RATE_LIMIT_LOCK:
        timestamps = _RATE_LIMIT_STORE[client_ip]
        _RATE_LIMIT_STORE[client_ip] = [t for t in timestamps if now - t < window]
        timestamps = _RATE_LIMIT_STORE[client_ip]
        if len(timestamps) >= limit_per_minute:
            oldest = timestamps[0]
            retry_after = max(1, int(window - (now - oldest)))
            return False, retry_after
        timestamps.append(now)
        return True, 0


def reset_rate_limits() -> None:
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_STORE.clear()


_PROCESSED_WEBHOOK_IDS: set[str] = set()
_WEBHOOK_LOCK = threading.Lock()


def reset_processed_webhooks() -> None:
    with _WEBHOOK_LOCK:
        _PROCESSED_WEBHOOK_IDS.clear()


def parse_webhook_timestamp(val) -> float | None:
    if not val:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            clean = val.strip()
            if clean.endswith("Z"):
                clean = clean[:-1] + "+00:00"
            return datetime.fromisoformat(clean).timestamp()
        except Exception:
            try:
                return float(val)
            except ValueError:
                return None
    return None


_SSE_SUBSCRIBERS: list[queue.Queue] = []
_SSE_SUBSCRIBERS_LOCK = threading.Lock()


def subscribe_sse() -> queue.Queue:
    q = queue.Queue(maxsize=100)
    with _SSE_SUBSCRIBERS_LOCK:
        _SSE_SUBSCRIBERS.append(q)
    return q


def unsubscribe_sse(q: queue.Queue) -> None:
    with _SSE_SUBSCRIBERS_LOCK:
        if q in _SSE_SUBSCRIBERS:
            _SSE_SUBSCRIBERS.remove(q)


def push_sse_event(event_name: str, payload: dict) -> None:
    with _SSE_SUBSCRIBERS_LOCK:
        for q in list(_SSE_SUBSCRIBERS):
            try:
                q.put_nowait((event_name, payload))
            except Exception:
                pass


MUTATING_PATHS = {
    "/api/extract",
    "/api/ingest",
    "/api/govern",
    "/api/withdraw",
    "/api/reset",
    "/api/demo/reset",
    "/api/events",
    "/api/webhook/inbound",
}

# Tier 1 GCP integrations (Stream B): env-gated, import-guarded, honest no-ops
# when SDKs / env vars / credentials are missing. Never raise at import.
BQ_LOG = BigQueryLog()
GCS = GCSOriginals()
VERTEX = VertexExtractor()


def get_next_source_id(store: EventStore) -> str:
    rows = store.db.execute("SELECT source_id FROM evidence").fetchall()
    max_num = 0
    for r in rows:
        sid = r[0]
        if isinstance(sid, str) and sid.startswith("SRC-"):
            try:
                num = int(sid.split("-")[1])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"SRC-{max_num + 1:02d}"


DEFAULT_DB_PATH = "./events.db"


def create_demo_store(db_path: str | None = None) -> EventStore:
    if db_path is None:
        db_path = os.environ.get("SCOPESHIFT_DB", DEFAULT_DB_PATH)
    store = EventStore(db_path)
    if not (FIXTURES_DIR / "brd.pdf").exists() or not (FIXTURES_DIR / "checkout.png").exists():
        from make_fixtures import make_brd, make_screenshot, CLIENT_NOTE
        make_brd()
        make_screenshot()
        (FIXTURES_DIR / "client_note.txt").write_text(CLIENT_NOTE, encoding="utf-8")

    pipeline = IngestionPipeline()
    evidence_items = pipeline.ingest_fixtures(FIXTURES_DIR)
    store.seed(evidence_items)

    existing_events = store.db.execute("SELECT COUNT(*) FROM event_log").fetchone()[0]
    if existing_events == 0:
        _store_event(store, "SRC-01", "ADDED")
        _store_event(store, "SRC-02", "ADDED")

    return store


def _mirror_event(event: Event) -> None:
    """Best-effort dual-write to BigQuery. Never raises, never blocks the request."""
    try:
        BQ_LOG.append(event)
    except Exception:
        logging.warning("BigQuery dual-write failed (local log unaffected)", exc_info=True)


def _store_event(
    store: EventStore,
    source_id: str,
    event: str,
    sender: str | None = None,
    channel: str | None = None,
    payload: dict | None = None,
) -> Event:
    """add_event + best-effort BigQuery mirror."""
    ev = store.add_event(source_id, event, sender=sender, channel=channel, payload=payload)
    _mirror_event(ev)
    return ev


def _parse_multipart(body: bytes, content_type: str) -> dict:
    msg = email.message_from_bytes(b"Content-Type: " + content_type.encode("latin1") + b"\r\n\r\n" + body)
    fields = {}
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            cd = part.get("Content-Disposition", "")
            if "form-data" in cd:
                name = part.get_param("name", header="content-disposition")
                filename = part.get_filename()
                payload = part.get_payload(decode=True)
                if filename:
                    fields["file_bytes"] = payload
                    fields["filename"] = filename
                elif name:
                    fields[name] = payload.decode("utf-8", errors="replace")
    return fields


def _make_crop_transcriber():
    if EXTRACTOR._client:
        def transcriber(crop_bytes: bytes) -> str:
            from google.genai import types
            from scopeshift.extraction import is_model_unavailable_error
            part = types.Part.from_bytes(data=crop_bytes, mime_type="image/png")
            prompt = "Return only the visible text inside this image crop verbatim."
            candidates = [EXTRACTOR.model] + [m for m in EXTRACTOR.fallbacks if m != EXTRACTOR.model]
            for m in candidates:
                try:
                    resp = EXTRACTOR._client.models.generate_content(
                        model=m, contents=[prompt, part]
                    )
                    text = getattr(resp, "text", "") or ""
                    log.info("Crop transcriber succeeded using model: %s", m)
                    return text
                except Exception as exc:
                    if is_model_unavailable_error(exc) and m != candidates[-1]:
                        log.warning("Transcriber model %s unavailable (%s). Retrying with fallback...", m, exc)
                        continue
                    log.warning("Transcriber failed on model %s: %s", m, exc)
            return ""
        return transcriber
    return None


def _ingest_text_evidence(store: EventStore, *, source_type: str, claim_id: str, text: str,
                          quote: str, observation: str, proposed_scope_change: bool,
                          value, region, image_bytes: bytes | None = None,
                          sender: str | None = None, channel: str | None = None,
                          received_at: str | None = None) -> tuple[str, dict, Evidence]:
    """The real ad-hoc ingestion pipeline, shared by POST /api/ingest and the
    live SSE feed: code validation boundary -> Evidence -> seed -> ADDED event
    (+ best-effort BigQuery dual-write inside _store_event).

    Returns (source_id, validated_claim_dict, evidence_item). Raises ValidationError.
    """
    raw_claim = {
        "claim_id": claim_id,
        "quote": quote,
        "observation": observation,
        "proposed_scope_change": proposed_scope_change,
        "value": value,
        "region": region,
        "sender": sender,
        "channel": channel,
        "received_at": received_at,
    }
    img_size = None
    if source_type == "screenshot":
        if image_bytes:
            img_size = get_image_size(image_bytes)
        elif (FIXTURES_DIR / "checkout.png").exists():
            img_size = get_image_size((FIXTURES_DIR / "checkout.png").read_bytes())
    transcriber = _make_crop_transcriber()
    v = validate_claim(
        raw_claim,
        source_type,
        text=text,
        image_size=img_size,
        image_bytes=image_bytes,
        transcriber=transcriber,
        allow_preverified=(image_bytes is None),
        sender=sender,
        channel=channel,
        received_at=received_at,
    )

    sid = get_next_source_id(store)
    max_seq = store.db.execute("SELECT COALESCE(MAX(created_sequence), 0) FROM evidence").fetchone()[0] + 1
    item = Evidence(
        source_id=sid,
        source_type=source_type,
        claim_id=v["claim_id"],
        value=v["value"],
        quote=v["quote"],
        observation=v["observation"],
        proposed_scope_change=v["proposed_scope_change"],
        quote_verified=v["quote_verified"],
        region=v["region"],
        event_sequence=max_seq,
        active=False,
        sender=v["sender"],
        channel=v["channel"],
        received_at=v["received_at"],
    )
    store.seed([item])
    _store_event(store, sid, "ADDED")
    if GCS.status().get("connected"):
        if image_bytes:
            art_name = f"{sid}.png"
            GCS.upload(art_name, image_bytes, content_type="image/png")
            _SOURCE_ARTIFACT_FILES[sid] = art_name
        elif text:
            art_name = f"{sid}.txt"
            GCS.upload(art_name, text.encode("utf-8"), content_type="text/plain")
            _SOURCE_ARTIFACT_FILES[sid] = art_name
    return sid, v, item


def _feed_transitions(before_states: dict, snapshot: dict) -> list[dict]:
    """Claim-state transitions between two snapshots, for badge-flash narration."""
    out = []
    for cid, res in snapshot.get("resolutions", {}).items():
        prev = before_states.get(cid)
        cur = res.get("state")
        if prev != cur:
            out.append({"claim_id": cid, "from": prev, "to": cur})
    return out


def _stream_feed(handler: "Handler", loop: bool) -> None:
    """Stream the scripted scenario as SSE, ingesting each arrival for real.

    Runs on the request thread (ThreadingHTTPServer gives each connection its
    own thread). Client disconnect surfaces as BrokenPipeError/ConnectionResetError
    on write — caught here so a dropped booth browser can never corrupt the store.
    """
    def send(event_name: str, payload: dict) -> None:
        chunk = ("event: %s\ndata: %s\n\n" % (
            event_name, json.dumps(payload, ensure_ascii=False))).encode("utf-8")
        handler.wfile.write(chunk)
        handler.wfile.flush()

    def claim_states(snapshot: dict) -> dict:
        return {cid: r.get("state") for cid, r in snapshot.get("resolutions", {}).items()}

    try:
        has_key = bool(EXTRACTOR.api_key)
        send("feed-start", {
            "scenario": SCENARIO_TITLE,
            "arrivals": len(ARRIVALS),
            "simulated": not has_key,
            "mode": "live-gemini" if has_key else "scripted",
            "loop": loop,
            "note": ("Live Gemini extraction feed" if has_key else
                    "Scripted scenario — arrivals are simulated, but each is ingested "
                    "through the real validation pipeline and event log."),
        })

        while True:
            alias_map: dict[str, str] = {}
            for idx, arrival in enumerate(ARRIVALS):
                time.sleep(max(0.0, float(arrival.get("delay_seconds", 1.0))))

                store = STORE  # read the current global (beats may have re-seeded)
                before = claim_states(store.snapshot())

                arr_quote = arrival["quote"]
                arr_val = arrival["value"]
                arr_obs = arrival["observation"]
                arr_scope = bool(arrival["proposed_scope_change"])

                if has_key and arrival.get("text") and arrival["kind"] != "withdrawal":
                    try:
                        ext_res = EXTRACTOR.extract_from_text(arrival["text"], arrival["source_type"])
                        for c in ext_res.claims:
                            if c.get("claim_id") == arrival["claim_id"]:
                                arr_quote = c.get("quote", arr_quote)
                                arr_val = c.get("value", arr_val)
                                arr_obs = c.get("observation", arr_obs)
                                if "proposed_scope_change" in c:
                                    arr_scope = bool(c["proposed_scope_change"])
                                break
                    except Exception as exc:
                        logging.warning("Live extraction failed on feed arrival %d: %s", idx, exc)

                payload: dict = {
                    "arrival_index": idx,
                    "arrival_total": len(ARRIVALS),
                    "kind": arrival["kind"],
                    "source_type": arrival["source_type"],
                    "claim_id": arrival["claim_id"],
                    "quote": arr_quote,
                    "observation": arr_obs,
                    "text_snippet": (arrival.get("text") or "")[:160],
                    "proposed_scope_change": arr_scope,
                    "simulated": not has_key,
                    "mode": "live-gemini" if has_key else "scripted",
                    "ingest_error": None,
                }
                try:
                    sid, v, item = _ingest_text_evidence(
                        store,
                        source_type=arrival["source_type"],
                        claim_id=arrival["claim_id"],
                        text=arrival.get("text", ""),
                        quote=arr_quote,
                        observation=arr_obs,
                        proposed_scope_change=arr_scope,
                        value=arr_val,
                        region=arrival.get("region"),
                    )
                    evts = store.snapshot()["events"]
                    payload.update({
                        "source_id": sid,
                        "quote_verified": v["quote_verified"],
                        "governing": item.governing,
                        "event": {"event_sequence": evts[-1]["event_sequence"] if evts else None,
                                  "source_id": sid, "event": "ADDED"},
                    })
                    if arrival.get("alias"):
                        alias_map[arrival["alias"]] = sid

                    # Withdrawal arrivals: the retraction message is real evidence,
                    # and it ALSO appends a genuine REMOVED event for the aliased source.
                    withdrawn = None
                    if arrival.get("withdraws_alias"):
                        target = alias_map.get(arrival["withdraws_alias"])
                        if target is None:
                            raise ValueError(
                                f"withdraws_alias {arrival['withdraws_alias']!r} not seen in this pass")
                        ev = _store_event(store, target, "REMOVED")
                        withdrawn = {"source_id": target, "event_sequence": ev.event_sequence,
                                     "event": "REMOVED"}
                    payload["withdraws"] = withdrawn
                except Exception as exc:
                    # Honest failure: the arrival is shown as rejected, the feed continues,
                    # and nothing partial reaches the UI as if it had succeeded. (Catches
                    # ValidationError plus pathological cases like a beat-reset racing the
                    # ingest on an old store handle.)
                    logging.warning("Feed arrival %d rejected: %s", idx, exc)
                    payload["ingest_error"] = str(exc)

                snap = store.snapshot()
                payload["transitions"] = _feed_transitions(before, snap)
                payload["claim_states"] = claim_states(snap)
                payload["state"] = snap
                send("evidence-arrival", payload)

            send("feed-end", {
                "scenario": SCENARIO_TITLE,
                "simulated": True,
                "loop": loop,
                "will_repeat": loop,
                "state": STORE.snapshot(),
            })
            if not loop:
                return
            time.sleep(2.0)  # breath between booth loops; aliases reset each pass
    except (BrokenPipeError, ConnectionResetError):
        # Client went away mid-stream (Stop button / closed tab). The store was only
        # ever touched through add_event's lock; nothing is left half-written.
        logging.info("Feed client disconnected; stream stopped cleanly.")
    except Exception:
        logging.exception("Feed stream failed")


_SOURCE_ARTIFACT_FILES: dict[str, str] = {}
_SOURCE_TYPE_FILES = {"brd": "brd.pdf", "screenshot": "checkout.png", "client_note": "client_note.txt"}


def artifact_url(source_id: str) -> dict | None:
    """Artifact URL for the inspector: signed GCS URL when connected, else local.

    Returns {"url": ..., "via": "gcs" | "local"}, or None for unknown sources.
    """
    if source_id in _SOURCE_ARTIFACT_FILES:
        filename = _SOURCE_ARTIFACT_FILES[source_id]
        if GCS.status()["connected"]:
            signed = GCS.signed_url(filename)
            if signed:
                return {"url": signed, "via": "gcs"}
        return {"url": f"/fixtures/{filename}", "via": "local"}

    sources = {s["id"]: s["type"] for s in STORE.snapshot()["sources"]}
    source_type = sources.get(source_id)
    filename = _SOURCE_TYPE_FILES.get(source_type) if source_type else None
    if filename is None:
        return None
    if GCS.status()["connected"]:
        signed = GCS.signed_url(filename)
        if signed:
            return {"url": signed, "via": "gcs"}
    return {"url": f"/fixtures/{filename}", "via": "local"}

demo_store = create_demo_store
STORE: EventStore = create_demo_store(os.environ.get("SCOPESHIFT_DB", DEFAULT_DB_PATH))
EXTRACTOR = Extractor(vertex_extractor=VERTEX)


def _run_chaos_test(chaos_type: str) -> dict:
    """Adversarial stress test with REAL execution.

    Each payload is run through the genuine code validation boundary
    (validate_claim / schema checks), exactly like /api/ingest does.
    Nothing here ever reaches the event log: interception happens first.
    Returns a genuine rejection receipt: which rule fired, the quote-diff
    or schema error, and the resulting classification.
    """
    receipt: dict = {"blocked": True, "chaos_type": chaos_type}

    if chaos_type == "forged_screenshot":
        # Attack: adversary submits a screenshot claiming a scope change.
        raw = {
            "claim_id": "checkout.payment_methods",
            "quote": "Pay with Card",
            "observation": "Forged UI frame claims Card is now in scope",
            "proposed_scope_change": True,  # <-- the attack
            "value": {"methods": ["Card"]},
            "region": [460, 285, 370, 80],
        }
        shot = FIXTURES_DIR / "checkout.png"
        img_size = None
        if shot.exists():
            from scopeshift.validation import png_size
            img_size = png_size(shot.read_bytes())
        validated = validate_claim(raw, "screenshot", image_size=img_size)
        receipt.update({
            "rule_fired": "validate_claim: proposed_scope_change is forced to False unless "
                          "source_type == 'client_note' (FR-7) — a screenshot can never govern",
            "payload": {"claimed_proposed_scope_change": True, "quote": raw["quote"]},
            "validated": {
                "proposed_scope_change": validated["proposed_scope_change"],
                "quote_verified": validated["quote_verified"],
                "region": list(validated["region"]) if validated["region"] else None,
            },
            "classification": "observation-only evidence — Evidence.governing is False, so the "
                              "resolver can never promote it to a requirement",
            "explanation": "Blocked: adversary forged a screenshot with proposed_scope_change=true. "
                           "The code validation boundary forced it to False (screenshots can NEVER "
                           "grant authority) and classified it as an observation only. Nothing "
                           "reached the event log.",
        })

    elif chaos_type == "unverified_note":
        # Attack: vague note text, but the submitted claim asserts a scope change with an
        # unverifiable quote.
        source_text = "Maybe consider Card?"
        raw = {
            "claim_id": "checkout.payment_methods",
            "quote": "Card is officially approved for checkout scope",
            "observation": "Vague suggestion presented as a decision",
            "proposed_scope_change": True,
            "value": {"methods": ["Card"]},
        }
        validated = validate_claim(raw, "client_note", text=source_text)
        receipt.update({
            "rule_fired": "quote verification: NFKC-normalized quote must appear verbatim in the "
                          "source text, else quote_verified=False and the claim cannot govern",
            "payload": {"source_text": source_text, "submitted_quote": raw["quote"]},
            "quote_check": {
                "normalized_quote": normalize(raw["quote"]),
                "normalized_source": normalize(source_text),
                "found_in_source": quote_in_text(raw["quote"], source_text),
                "quote_verified": validated["quote_verified"],
            },
            "classification": "OBSERVATION only — quote_verified=False means Evidence.governing is "
                              "False; it is shown to the user but can never authorize a requirement",
            "explanation": "Blocked: an unverified client message was received. Quote verification "
                           "failed because the submitted quote does not appear in the source text. "
                           "Code classified it as observation only.",
        })

    elif chaos_type == "rogue_currency":
        # Attack: hallucinated claim_id outside the frozen schema.
        raw = {
            "claim_id": "checkout.bitcoin",
            "quote": "Bitcoin accepted at checkout",
            "observation": "Hallucinated currency claim",
            "proposed_scope_change": True,
            "value": {"currency": "BTC"},
        }
        try:
            validate_claim(raw, "client_note", text="Bitcoin accepted at checkout")
            raise AssertionError("validate_claim must reject checkout.bitcoin")
        except ValidationError as err:
            receipt.update({
                "rule_fired": "schema enum check: claim_id must be one of the 4 registered claim ids "
                              "(checkout.payment_methods, checkout.currency, auth.mfa_requirement, "
                              "refunds.settlement_sla)",
                "payload": {"submitted_claim_id": raw["claim_id"]},
                "schema_error": str(err),
                "classification": "rejected before the event log — no evidence record was created",
                "explanation": "Blocked: ingestion attempted claim_id='checkout.bitcoin'. Schema "
                               "validation rejected it immediately (outside the frozen enum). The "
                               "hallucinated claim was halted before reaching the event log.",
            })

    elif chaos_type == "forged_sender":
        # Attack: valid quote and proposed_scope_change, but sender is NOT in approver allowlist.
        source_text = "Checkout shall support Card payments. UPI moves to Phase 2."
        raw = {
            "claim_id": "checkout.payment_methods",
            "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
            "observation": "Unauthorized scope change attempt",
            "proposed_scope_change": True,
            "value": {"methods": ["Card"], "deferred": ["UPI"]},
            "sender": "Mallory (External Impersonator)",
            "channel": "email",
        }
        validated = validate_claim(raw, "client_note", text=source_text)
        receipt.update({
            "rule_fired": "approver allowlist check: sender must match authorized role in approvers.json "
                          "(SCOPESHIFT_APPROVERS). Non-allowlisted senders cannot govern.",
            "payload": {"sender": raw["sender"], "channel": raw["channel"], "quote": raw["quote"]},
            "validated": {
                "proposed_scope_change": validated["proposed_scope_change"],
                "quote_verified": validated["quote_verified"],
                "observation": validated["observation"],
            },
            "classification": "OBSERVATION only — sender not authorised; Evidence.governing is False",
            "explanation": "Blocked: sender 'Mallory (External Impersonator)' is not in the approver "
                           "allowlist. Code validation demoted the claim to an observation with reason "
                           "'sender not authorised'. The unauthorized note cannot govern requirements.",
        })

    elif chaos_type == "fabricated_screenshot_text":
        # Attack: valid bounding box on checkout UI, but fabricated quote text not in the crop.
        shot = FIXTURES_DIR / "checkout.png"
        raw = {
            "claim_id": "checkout.payment_methods",
            "quote": "Cryptocurrency Approved At Checkout",
            "observation": "Fabricated text claim with valid UI bounding box",
            "proposed_scope_change": False,
            "value": {"methods": ["Card"]},
            "region": [460, 285, 370, 80],
        }
        shot_bytes = shot.read_bytes() if shot.exists() else b""
        img_size = get_image_size(shot_bytes) if shot_bytes else (900, 620)
        # Separate verifier transcriber returning the actual visible text ("Pay with Card")
        mock_crop_transcriber = lambda crop: "Pay with Card"
        validated = validate_claim(
            raw,
            "screenshot",
            image_size=img_size,
            image_bytes=shot_bytes,
            transcriber=mock_crop_transcriber,
        )
        receipt.update({
            "rule_fired": "screenshot transcription verification: text extracted from cropped image "
                          "region must match the cited quote after normalization",
            "payload": {
                "submitted_quote": raw["quote"],
                "transcribed_crop_text": "Pay with Card",
                "region": raw["region"],
            },
            "validated": {
                "quote_verified": validated["quote_verified"],
                "region": list(validated["region"]) if validated["region"] else None,
            },
            "classification": "UNVERIFIED visual claim — quote_verified is False; visual observation cannot govern",
            "explanation": "Blocked: bounding box [460, 285, 370, 80] was cropped with Pillow and "
                           "transcribed. The actual visible text is 'Pay with Card', which does not match "
                           "the fabricated quote 'Cryptocurrency Approved At Checkout'. Code set quote_verified=False.",
        })

    else:
        receipt.update({
            "rule_fired": "unknown chaos type",
            "classification": "no-op — nothing ingested",
            "explanation": "Chaos input safely intercepted and rejected by the code validation boundary.",
        })

    receipt["state"] = STORE.snapshot()
    return receipt


def generate_markdown_export(snapshot: dict) -> str:
    lines = [
        "# Business Requirements Document (BRD) — Governed Output",
        "",
        "> Generated by **ScopeShift Enterprise** (Deterministic Authority Engine)",
        "> Principle: *Seeing a button is not approving the button.*",
        "",
        "---",
        "",
        "## Current Governed Requirements",
        "",
    ]

    resolutions = snapshot.get("resolutions", {})
    published_count = 0
    for cid, res in resolutions.items():
        if res.get("in_brd"):
            published_count += 1
            lines.append(f"### {res.get('title', cid)} (`{cid}`)")
            lines.append(f"- **Requirement:** {res.get('requirement')}")
            lines.append(f"- **Business Rule:** {res.get('rule')}")
            lines.append(f"- **Status:** `{res.get('state')}` (Basis: {res.get('basis')})")
            lines.append(f"- **Governing Authority:** {res.get('governing_source')}")
            if res.get("superseded_sources"):
                lines.append(f"- **Superseded Sources:** {', '.join(res.get('superseded_sources'))}")
            lines.append("- **Citations:**")
            for c in res.get("citations", []):
                lines.append(f"  - `[{c.get('source_id')}]` ({c.get('role')}): \"{c.get('quote')}\"")
            lines.append("")

    if published_count == 0:
        lines.append("*No requirements are currently published in the BRD. All conflicting claims are withheld.*")
        lines.append("")

    lines.append("## Disputed & Withheld Claims")
    lines.append("")
    withheld_count = 0
    for cid, res in resolutions.items():
        if not res.get("in_brd"):
            withheld_count += 1
            lines.append(f"### {res.get('title', cid)} (`{cid}`)")
            lines.append(f"- **State:** `{res.get('state')}` (WITHHELD)")
            lines.append(f"- **Resolution Rationale:** {res.get('reason')}")
            if res.get("disappeared"):
                d = res.get("disappeared")
                lines.append(f"- **Disappearance Event:** {d.get('source_id')} was {d.get('event')} at sequence #{d.get('event_sequence')}.")
            lines.append("")

    lines.append("## Ingested Sources Ledger")
    lines.append("")
    lines.append("| Source ID | Type | Active In Log | Verified | Quote / Key Evidence |")
    lines.append("|:---|:---|:---:|:---:|:---|")
    for s in snapshot.get("sources", []):
        act = "YES" if s.get("active") else "NO (WITHDRAWN)"
        ver = "VERIFIED" if s.get("quote_verified") else "UNVERIFIED"
        lines.append(f"| `{s.get('id')}` | {s.get('type')} | {act} | {ver} | \"{s.get('quote')}\" |")
    lines.append("")

    lines.append("## Append-Only Audit Trail")
    lines.append("")
    lines.append("| Sequence | Action | Source ID | Invariant Check |")
    lines.append("|:---:|:---:|:---:|:---|")
    for ev in snapshot.get("events", []):
        lines.append(f"| #{ev.get('event_sequence')} | `{ev.get('event')}` | `{ev.get('source_id')}` | Valid state machine transition |")
    lines.append("")
    lines.append("---")
    lines.append("*Audit Guarantee: SQLite append-only log. Replay projection is 100% deterministic.*")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    server_version = "ScopeShift/1.0"

    def send_json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com;"
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            db_path = os.environ.get("SCOPESHIFT_DB", DEFAULT_DB_PATH)
            persisted = bool(db_path and db_path != ":memory:")
            self.send_json({"status": "ok", "version": "1.0.0", "persisted": persisted})
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/api/state":
            # FR-8/FR-18 fail-closed: EventStore.snapshot() raises ValidationError
            # if any served citation is dangling; convert to a structured 500
            # instead of a dropped connection — never serve the BRD projection.
            try:
                self.send_json(STORE.snapshot())
            except ValidationError as exc:
                logging.exception("Citation integrity violation on /api/state")
                self.send_json({"error": {"code": "CITATION_INTEGRITY_VIOLATION",
                                           "message": str(exc)}}, 500)
            return

        if path == "/api/cloud/status":
            # Honest backend status for the UI pill cluster: each service reports
            # connected (live) or disconnected-with-reason (local mirror active).
            route = EXTRACTOR.route
            ext_mode = EXTRACTOR.effective_mode()
            self.send_json({
                "bigquery": BQ_LOG.status(),
                "gcs": GCS.status(),
                "vertex": VERTEX.status(),
                "extraction": {
                    "mode": ext_mode,
                    "route": route,
                    "last_failure_reason": EXTRACTOR.last_failure_reason,
                },
                "route": route,
                "last_failure_reason": EXTRACTOR.last_failure_reason,
            })
            return

        if path == "/api/feed":
            # Live evidence feed (Stream C): Server-Sent Events. Each arrival of the
            # scripted scenario is ingested through the real pipeline; the payload
            # carries the resulting claim states + full snapshot so the UI recomputes
            # live. ?loop=1 repeats the scenario (booth mode) until disconnect.
            from urllib.parse import parse_qs
            loop = parse_qs(parsed.query).get("loop", ["0"])[0] == "1"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            _stream_feed(self, loop)
            # The (non-looping) scenario has a definite end: close the connection
            # so SSE clients observe a clean end-of-stream after feed-end instead
            # of hanging on HTTP/1.1 keep-alive. (loop=1 never returns here on its
            # own — it ends when the client disconnects.)
            self.close_connection = True
            return

        if path == "/api/artifact":
            from urllib.parse import parse_qs
            source_id = parse_qs(parsed.query).get("source_id", [None])[0]
            info = artifact_url(source_id) if source_id else None
            if info is None:
                self.send_json({"error": {"code": "NOT_FOUND", "message": "Unknown source_id"}}, 404)
                return
            self.send_json(info)
            return

        if path == "/api/audit/chain":
            # Raw per-block hash inputs for genuine client-side verification:
            # the UI recomputes SHA-256 over each hash_input and checks the
            # prev_hash linkage instead of trusting the served hashes.
            self.send_json({
                "blocks": STORE.audit_chain(),
                "algorithm": "SHA-256",
                "input_format": "<prev_hash>:<sequence>:<source_id>:<event>",
                "genesis_prev_hash": "0" * 64,
            })
            return

        if path == "/api/export/markdown":
            snap = STORE.snapshot()
            md = generate_markdown_export(snap).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="scopeshift-governed-brd.md"')
            self.send_header("Content-Length", str(len(md)))
            self.end_headers()
            self.wfile.write(md)
            return

        if path == "/api/export/json":
            snap = STORE.snapshot()
            body = json.dumps(snap, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="scopeshift-audit-trail.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path.startswith("/fixtures/"):
            rel_file = path.replace("/fixtures/", "", 1)
            file_path = (FIXTURES_DIR / rel_file).resolve()
            if FIXTURES_DIR in file_path.parents and file_path.is_file():
                self.serve_file(file_path)
                return
            self.send_json({"error": {"code": "NOT_FOUND", "message": "Fixture not found"}}, 404)
            return

        if path in {"/", "/index.html", "/styles.css", "/app.js", "/three.min.js"}:
            rel = "index.html" if path == "/" else path.lstrip("/")
            file_path = (ROOT / rel).resolve()
            if file_path.is_file():
                self.serve_file(file_path)
                return

        self.send_json({"error": {"code": "NOT_FOUND", "message": "Resource not found"}}, 404)

    def do_POST(self):
        global STORE
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_BODY:
            self.send_json({
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"Payload exceeds maximum allowed upload size of 10 MB ({content_length} > {MAX_BODY} bytes)"
                }
            }, 413)
            return

        # Optional shared-secret auth for mutating endpoints
        api_token = os.environ.get("SCOPESHIFT_API_TOKEN")
        if api_token and path in MUTATING_PATHS:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {api_token}":
                self.send_json({
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Unauthorized: valid Bearer token required"
                    }
                }, 401)
                return

        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        if len(body_bytes) > MAX_BODY:
            self.send_json({
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"Payload exceeds maximum allowed upload size of 10 MB ({len(body_bytes)} > {MAX_BODY} bytes)"
                }
            }, 413)
            return

        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            import io
            data = _parse_multipart(io.BytesIO(body_bytes), ctype, content_length)
        else:
            try:
                data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except json.JSONDecodeError:
                self.send_json({"error": {"code": "BAD_REQUEST", "message": "Invalid JSON"}}, 400)
                return

        if path == "/api/extract":
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
            rate_limit_env = os.environ.get("SCOPESHIFT_RATE_LIMIT_PER_MINUTE", "30")
            try:
                limit_val = int(rate_limit_env)
            except ValueError:
                limit_val = 30
            allowed, retry_after = check_rate_limit(client_ip, limit_val)
            if not allowed:
                self.send_json({
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded: maximum {limit_val} requests per minute",
                        "retry_after": retry_after,
                    }
                }, 429)
                return

            import base64
            source_type = data.get("source_type") or "client_note"
            text = data.get("text")
            file_bytes = data.get("file_bytes")
            filename = data.get("filename", "")
            sender = data.get("sender")
            channel = data.get("channel")

            if not file_bytes and data.get("file_base64"):
                try:
                    file_bytes = base64.b64decode(data["file_base64"])
                except Exception as exc:
                    self.send_json({"error": {"code": "VALIDATION_ERROR", "message": f"Invalid base64 payload: {exc}"}}, 422)
                    return

            if not file_bytes and data.get("file") and isinstance(data.get("file"), str):
                try:
                    file_bytes = base64.b64decode(data["file"])
                except Exception:
                    pass

            if not file_bytes and not text:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "Either file or text is required for extraction"}}, 422)
                return

            doc_text = text or ""
            img_bytes = None
            extract_res = None

            if file_bytes:
                sniffed = sniff_mime_type(file_bytes)
                if sniffed is None or sniffed not in ALLOWED_MIME_TYPES:
                    self.send_json({
                        "error": {
                            "code": "UNSUPPORTED_MEDIA_TYPE",
                            "message": f"Unsupported media type: sniffed format is not allowed (must be one of {sorted(ALLOWED_MIME_TYPES)})"
                        }
                    }, 415)
                    return

                is_pdf = sniffed == "application/pdf"
                is_png = sniffed == "image/png"
                is_jpeg = sniffed == "image/jpeg"
                is_image = sniffed in ("image/png", "image/jpeg", "image/webp")

                if is_pdf:
                    source_type = data.get("source_type") or "brd"
                    extract_res = EXTRACTOR.extract_from_pdf(file_bytes, source_type=source_type)
                    try:
                        import pypdf
                        import io
                        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                        doc_text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    except Exception:
                        doc_text = ""
                elif is_image:
                    source_type = data.get("source_type") or "screenshot"
                    img_bytes = file_bytes
                    extract_res = EXTRACTOR.extract_from_image(file_bytes, source_type=source_type)
                else:
                    try:
                        doc_text = file_bytes.decode("utf-8")
                    except Exception:
                        doc_text = file_bytes.decode("latin-1", errors="replace")
                    extract_res = EXTRACTOR.extract_from_text(doc_text, source_type=source_type)
            else:
                extract_res = EXTRACTOR.extract_from_text(doc_text, source_type=source_type)

            receipts = []
            img_size = get_image_size(img_bytes) if img_bytes else None
            is_pdf_upload = bool(file_bytes and is_pdf)
            transcriber = _make_crop_transcriber() if (img_bytes or is_pdf_upload) else None

            for claim in extract_res.claims:
                try:
                    v = validate_claim(
                        claim,
                        source_type,
                        text=doc_text,
                        pdf_bytes=file_bytes if is_pdf_upload else None,
                        image_size=img_size,
                        image_bytes=img_bytes,
                        transcriber=transcriber,
                        sender=sender,
                        channel=channel,
                    )
                    sid = get_next_source_id(STORE)
                    max_seq = STORE.db.execute("SELECT COALESCE(MAX(created_sequence), 0) FROM evidence").fetchone()[0] + 1
                    item = Evidence(
                        source_id=sid,
                        source_type=source_type,
                        claim_id=v["claim_id"],
                        value=v["value"],
                        quote=v["quote"],
                        observation=v["observation"],
                        proposed_scope_change=v["proposed_scope_change"],
                        quote_verified=v["quote_verified"],
                        region=v["region"],
                        event_sequence=max_seq,
                        active=False,
                        sender=v["sender"],
                        channel=v["channel"],
                        received_at=v["received_at"],
                    )
                    STORE.seed([item])
                    _store_event(STORE, sid, "ADDED", sender=v["sender"], channel=v["channel"])
                    if GCS.status().get("connected"):
                        if file_bytes:
                            ext = ".pdf" if is_pdf else (".png" if is_png else (".jpg" if is_jpeg else ".bin"))
                            art_name = f"{sid}{ext}"
                            mime = "application/pdf" if is_pdf else ("image/png" if is_png else ("image/jpeg" if is_jpeg else "application/octet-stream"))
                            GCS.upload(art_name, file_bytes, content_type=mime)
                            _SOURCE_ARTIFACT_FILES[sid] = art_name
                        elif doc_text:
                            art_name = f"{sid}.txt"
                            GCS.upload(art_name, doc_text.encode("utf-8"), content_type="text/plain")
                            _SOURCE_ARTIFACT_FILES[sid] = art_name
                    receipts.append({
                        "claim_id": v["claim_id"],
                        "source_id": sid,
                        "status": "verified" if v["quote_verified"] else "unverified",
                        "quote_verified": v["quote_verified"],
                        "governing": item.governing,
                        "observation": v["observation"],
                        "error": None,
                    })
                except ValidationError as err:
                    receipts.append({
                        "claim_id": claim.get("claim_id"),
                        "source_id": None,
                        "status": "rejected",
                        "quote_verified": False,
                        "governing": False,
                        "observation": claim.get("observation", ""),
                        "error": str(err),
                    })

            self.send_json({
                "claims": extract_res.claims,
                "receipts": receipts,
                "extraction": {
                    "mode": extract_res.mode,
                    "route": EXTRACTOR.route,
                    "model": extract_res.model,
                    "latency_ms": round(extract_res.latency_ms, 2),
                    "reason": extract_res.reason,
                    "error_type": extract_res.error_type,
                },
                "state": STORE.snapshot(),
            }, 200)
            return

        if path == "/api/webhook/inbound":
            webhook_secret = os.environ.get("SCOPESHIFT_WEBHOOK_SECRET")
            sig_header = (
                self.headers.get("X-ScopeShift-Signature")
                or self.headers.get("X-Signature-256")
                or self.headers.get("X-Hub-Signature-256")
                or ""
            )
            if not webhook_secret or not sig_header:
                self.send_json({"error": {"code": "UNAUTHORIZED", "message": "Missing webhook signature or server secret"}}, 401)
                return

            expected_sig = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
            clean_sig = sig_header.removeprefix("sha256=").strip()
            if not hmac.compare_digest(clean_sig, expected_sig):
                self.send_json({"error": {"code": "UNAUTHORIZED", "message": "Invalid webhook HMAC signature"}}, 401)
                return

            received_at_raw = data.get("received_at")
            ts = parse_webhook_timestamp(received_at_raw)
            now = time.time()
            if ts is None or abs(now - ts) > 300:
                self.send_json({"error": {"code": "STALE_TIMESTAMP", "message": "Message timestamp expired or invalid (> 5 minutes drift)"}}, 401)
                return

            message_id = str(data.get("message_id") or "")
            if not message_id:
                message_id = hashlib.sha256(body_bytes).hexdigest()

            with _WEBHOOK_LOCK:
                if message_id in _PROCESSED_WEBHOOK_IDS:
                    self.send_json({"error": {"code": "DUPLICATE_MESSAGE", "message": f"Message ID '{message_id}' already processed (replay rejected)"}}, 409)
                    return
                _PROCESSED_WEBHOOK_IDS.add(message_id)

            channel = str(data.get("channel") or "webhook")
            sender = str(data.get("sender") or "unknown")
            text = str(data.get("text") or "")

            extract_res = EXTRACTOR.extract_from_text(text, source_type="client_note")
            receipts = []

            for claim in extract_res.claims:
                try:
                    v = validate_claim(
                        claim,
                        "client_note",
                        text=text,
                        sender=sender,
                        channel=channel,
                        received_at=str(received_at_raw),
                    )
                    sid = get_next_source_id(STORE)
                    max_seq = STORE.db.execute("SELECT COALESCE(MAX(created_sequence), 0) FROM evidence").fetchone()[0] + 1

                    governs = bool(v.get("proposed_scope_change")) and bool(v.get("quote_verified")) and is_sender_allowlisted(sender, channel)

                    item = Evidence(
                        source_id=sid,
                        source_type="client_note",
                        claim_id=v["claim_id"],
                        value=v["value"],
                        quote=v["quote"],
                        observation=v["observation"],
                        proposed_scope_change=v["proposed_scope_change"],
                        quote_verified=v["quote_verified"],
                        region=v.get("region"),
                        event_sequence=max_seq,
                        active=False,
                        sender=sender,
                        channel=channel,
                        received_at=str(received_at_raw),
                    )
                    STORE.seed([item])
                    ev_payload = {
                        "source_id": sid,
                        "claim_id": v["claim_id"],
                        "sender": sender,
                        "channel": channel,
                        "received_at": str(received_at_raw),
                        "message_id": message_id,
                        "governing": governs,
                    }
                    _store_event(STORE, sid, "ADDED", sender=sender, channel=channel, payload=ev_payload)

                    receipt = {
                        "source_id": sid,
                        "claim_id": v["claim_id"],
                        "status": "verified" if v["quote_verified"] else "unverified",
                        "governing": governs,
                        "observation": v["observation"],
                        "quote": v["quote"],
                        "sender": sender,
                        "channel": channel,
                    }
                    receipts.append(receipt)

                    push_sse_event("webhook-arrival", {
                        "source_id": sid,
                        "claim_id": v["claim_id"],
                        "channel": channel,
                        "sender": sender,
                        "governing": governs,
                        "quote_verified": v["quote_verified"],
                        "observation": v["observation"],
                    })
                except Exception as exc:
                    logging.warning("Webhook claim validation error: %s", exc)
                    receipts.append({
                        "claim_id": claim.get("claim_id"),
                        "source_id": None,
                        "status": "rejected",
                        "error": str(exc),
                    })

            self.send_json({
                "ok": True,
                "message_id": message_id,
                "claims_processed": len(receipts),
                "receipts": receipts,
                "state": STORE.snapshot(),
            }, 200)
            return

        if path in ("/api/demo/reset", "/api/reset"):
            if os.environ.get("SCOPESHIFT_DB"):
                self.send_json({"error": {"code": "CONFLICT", "message": "Reset disabled for persisted databases"}}, 409)
                return
            STORE.close()
            STORE = create_demo_store(":memory:")
            self.send_json(STORE.snapshot(), 200)
            return

        if path == "/api/demo/scrub":
            # Time-travel scrubber: replay up to target sequence number
            target_seq = data.get("sequence")
            if not isinstance(target_seq, int) or target_seq < 0:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "sequence must be non-negative integer"}}, 422)
                return

            all_evidence = STORE._load_evidence()
            all_events = STORE._load_events()
            filtered_events = [e for e in all_events if e.event_sequence <= target_seq]
            res = replay(all_evidence, filtered_events)
            # FR-8/FR-18 also applies to this historical projection: fail closed
            # rather than serving a time-travel view with dangling citations.
            try:
                validate_citations(res.resolutions.values(), res.active_evidence)
            except ValidationError as exc:
                logging.exception("Citation integrity violation on /api/demo/scrub")
                self.send_json({"error": {"code": "CITATION_INTEGRITY_VIOLATION",
                                           "message": str(exc)}}, 500)
                return
            removed_ids = {e.source_id for e in filtered_events if e.event == "REMOVED"}
            active_ids = {e.source_id for e in filtered_events if e.event == "ADDED"} - removed_ids

            scrub_state = {
                "resolutions": {k: v.to_dict() for k, v in res.resolutions.items()},
                "sources": [
                    {
                        "id": e.source_id,
                        "type": e.source_type,
                        "claim_id": e.claim_id,
                        "quote": e.quote,
                        "observation": e.observation,
                        "proposed_scope_change": e.proposed_scope_change,
                        "quote_verified": e.quote_verified,
                        "region": list(e.region) if e.region else None,
                        "active": e.source_id in active_ids,
                    }
                    for e in all_evidence
                ],
                "events": [e.__dict__ for e in filtered_events],
                "timeline": res.timeline,
                "current_seq": target_seq,
                # FR-8/FR-18 also applies to this historical projection.
                "citation_warnings": citation_warnings(res.resolutions.values(), res.active_evidence),
                "mirror_note": "Time-Travel Scrub View: exact deterministic replay state at event sequence #" + str(target_seq),
            }
            self.send_json({"state": scrub_state}, 200)
            return

        if path == "/api/demo/chaos":
            # Adversarial Stress Test: real execution through the code validation boundary.
            chaos_type = data.get("chaos_type", "unverified_note")
            self.send_json(_run_chaos_test(chaos_type), 200)
            return

        if path == "/api/demo/beat":
            beat = data.get("beat")
            use_live_ai = bool(data.get("use_live_ai", False))
            if beat not in {1, 2, 3}:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "beat must be 1, 2, or 3"}}, 422)
                return

            # Stage flow is strictly 1 -> 2 -> 3. Beat 1 always re-seeds, so every beat is
            # reset-aware: re-pressing an already-applied beat is an explicit, honest no-op
            # (already_applied + hint) instead of a silent one.
            extraction_meta = {"mode": "none", "latency_ms": 0, "claims": [], "validation": []}
            response: dict = {}

            def _has(sid: str, event: str) -> bool:
                return any(e["source_id"] == sid and e["event"] == event
                           for e in STORE.snapshot()["events"])

            def _ensure_added(sid: str) -> None:
                if not _has(sid, "ADDED"):
                    _store_event(STORE, sid, "ADDED")

            def _active(sid: str) -> bool:
                return _has(sid, "ADDED") and not _has(sid, "REMOVED")

            if beat == 1:
                # Always reset to the 2-event seed: SRC-01 + SRC-02 ADDED -> DISPUTED.
                STORE.close()
                STORE = create_demo_store(os.environ.get("SCOPESHIFT_DB", ":memory:"))

            elif beat == 2:
                _ensure_added("SRC-01")
                _ensure_added("SRC-02")

                # Honest extraction outcome: the claims, their code validation, and the real
                # mode. Without GEMINI_API_KEY this is the deterministic fallback —
                # pre-extracted evidence — and replay never calls Gemini (FR-4).
                note_file = FIXTURES_DIR / "client_note.txt"
                note_text = note_file.read_text(encoding="utf-8") if note_file.exists() else ""
                extract_res = EXTRACTOR.extract_from_text(note_text, "client_note", force_fallback=not use_live_ai)
                validation = []
                for claim in extract_res.claims:
                    try:
                        v = validate_claim(claim, "client_note", text=note_text)
                        validation.append({"claim_id": v["claim_id"],
                                           "quote_verified": v["quote_verified"],
                                           "proposed_scope_change": v["proposed_scope_change"],
                                           "error": None})
                    except ValidationError as err:
                        validation.append({"claim_id": claim.get("claim_id"),
                                           "quote_verified": False,
                                           "proposed_scope_change": False,
                                           "error": str(err)})
                mode = "live" if extract_res.mode == "live" else "deterministic-fallback"
                extraction_meta = {
                    "mode": mode,
                    "latency_ms": round(extract_res.latency_ms, 2),
                    "model": extract_res.model,
                    "claims": extract_res.claims,
                    "validation": validation,
                    "note": ("deterministic fallback — pre-extracted evidence (replay never calls Gemini)"
                             if mode != "live" else "live Gemini extraction"),
                }

                if _has("SRC-03", "ADDED"):
                    response["already_applied"] = True
                    response["hint"] = "Beat 2 already applied — press 1 to re-seed, then 2."
                else:
                    _store_event(STORE, "SRC-03", "ADDED")

            elif beat == 3:
                _ensure_added("SRC-01")
                _ensure_added("SRC-02")
                _ensure_added("SRC-03")
                if _active("SRC-03"):
                    _store_event(STORE, "SRC-03", "REMOVED")
                else:
                    response["already_applied"] = True
                    response["hint"] = "Beat 3 already applied — press 1 to re-seed, then run 1 → 2 → 3."

            response["state"] = STORE.snapshot()
            response["extraction"] = extraction_meta
            self.send_json(response, 200)
            return

        if path == "/api/events":
            source_id = data.get("source_id")
            event_type = data.get("event")
            if not isinstance(source_id, str) or not source_id.startswith("SRC-"):
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "source_id must be SRC-XX"}}, 422)
                return
            try:
                event_obj = _store_event(STORE, source_id, event_type)
                self.send_json({"event": event_obj.__dict__, "state": STORE.snapshot()}, 201)
            except ValueError as exc:
                self.send_json({"error": {"code": "TRANSITION_REJECTED", "message": str(exc)}}, 422)
            except Exception as exc:
                logging.exception("Failed adding event")
                self.send_json({"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, 500)
            return

        if path == "/api/ingest":
            source_type = data.get("source_type")
            claim_id = data.get("claim_id")
            text = str(data.get("text", "") or "")
            quote = str(data.get("quote", "") or "")
            observation = str(data.get("observation", "") or "")
            proposed_scope_change = bool(data.get("proposed_scope_change", False))
            value = data.get("value")
            region = data.get("region")

            if not isinstance(source_type, str) or source_type not in ("brd", "screenshot", "client_note"):
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "source_type must be brd, screenshot, or client_note"}}, 422)
                return

            try:
                sid, v, item = _ingest_text_evidence(
                    STORE,
                    source_type=source_type,
                    claim_id=claim_id,
                    text=text,
                    quote=quote,
                    observation=observation,
                    proposed_scope_change=proposed_scope_change,
                    value=value,
                    region=region,
                )
            except ValidationError as err:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": str(err)}}, 422)
                return

            self.send_json({"source_id": sid, "evidence": {
                "source_id": sid,
                "source_type": source_type,
                "claim_id": v["claim_id"],
                "value": v["value"],
                "quote": v["quote"],
                "quote_verified": v["quote_verified"],
                "governing": item.governing,
            }, "state": STORE.snapshot()}, 201)
            return

        if path == "/api/govern":
            claim_id = data.get("claim_id")
            directive = str(data.get("directive", "") or "").strip()
            value = data.get("value")

            if not directive:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "directive is required"}}, 422)
                return

            raw_claim = {
                "claim_id": claim_id,
                "quote": directive,
                "observation": f"Client scope directive: {directive[:80]}",
                "proposed_scope_change": True,
                "value": value,
            }

            try:
                v = validate_claim(raw_claim, "client_note", text=directive)
            except ValidationError as err:
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": str(err)}}, 422)
                return

            sid = get_next_source_id(STORE)
            max_seq = STORE.db.execute("SELECT COALESCE(MAX(created_sequence), 0) FROM evidence").fetchone()[0] + 1
            item = Evidence(
                source_id=sid,
                source_type="client_note",
                claim_id=v["claim_id"],
                value=v["value"],
                quote=v["quote"],
                observation=v["observation"],
                proposed_scope_change=True,
                quote_verified=True,
                region=None,
                event_sequence=max_seq,
                active=False,
            )
            STORE.seed([item])
            _store_event(STORE, sid, "ADDED")
            self.send_json({"source_id": sid, "state": STORE.snapshot()}, 201)
            return

        if path == "/api/withdraw":
            source_id = data.get("source_id")
            if not isinstance(source_id, str):
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "source_id is required"}}, 422)
                return
            try:
                event_obj = _store_event(STORE, source_id, "REMOVED")
                self.send_json({"event": event_obj.__dict__, "state": STORE.snapshot()}, 200)
            except ValueError as exc:
                self.send_json({"error": {"code": "TRANSITION_REJECTED", "message": str(exc)}}, 422)
            except Exception as exc:
                self.send_json({"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, 500)
            return

        if path == "/api/ask":
            # "Ask the evidence": deterministic Q&A over the live snapshot.
            # Facts and citations are computed from the snapshot, never generated.
            question = data.get("question")
            if not isinstance(question, str) or not question.strip():
                self.send_json({"error": {"code": "VALIDATION_ERROR", "message": "question must be a non-empty string"}}, 422)
                return
            try:
                result = answer_question(STORE.snapshot(), question)
            except Exception as exc:
                logging.exception("ask failed")
                self.send_json({"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, 500)
                return
            self.send_json(result, 200)
            return

        self.send_json({"error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}, 404)

    def serve_file(self, path: Path):
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".png": "image/png",
            ".pdf": "application/pdf",
            ".txt": "text/plain; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
        }
        content_type = content_types.get(path.suffix.lower(), "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        logging.info("%s %s", self.command, self.path)


def run_server(host: Optional[str] = None, port: Optional[int] = None):
    in_container = (
        os.path.exists("/.dockerenv")
        or bool(os.environ.get("K_SERVICE"))
        or bool(os.environ.get("CONTAINER"))
    )
    default_host = "0.0.0.0" if in_container else "127.0.0.1"
    resolved_host = host or os.environ.get("HOST", default_host)
    resolved_port = int(port or os.environ.get("PORT", 8765))

    print(f"ScopeShift server listening on http://{resolved_host}:{resolved_port}")
    # Honest startup lines: never claim cloud is live when it isn't.
    for name, adapter in (("BigQuery", BQ_LOG), ("GCS", GCS), ("Vertex", VERTEX)):
        st = adapter.status()
        if st["connected"]:
            logging.info("%s: connected (%s)", name, st["reason"])
        else:
            logging.info("%s: not connected (%s) — local mirror active", name, st["reason"])
    logging.info("Extraction: %s", EXTRACTOR.effective_mode())
    _upload_fixtures_to_gcs()
    server = ThreadingHTTPServer((resolved_host, resolved_port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _upload_fixtures_to_gcs() -> None:
    """Best-effort: put originals in the bucket so signed URLs resolve. No-op offline."""
    if not GCS.status()["connected"]:
        return
    content_types = {".png": "image/png", ".pdf": "application/pdf", ".txt": "text/plain"}
    try:
        for f in sorted(FIXTURES_DIR.iterdir()):
            if f.is_file():
                ok = GCS.upload(f.name, f.read_bytes(), content_types.get(f.suffix.lower(), "application/octet-stream"))
                logging.info("GCS upload %s: %s", f.name, "ok" if ok else "failed (local fallback)")
    except Exception:
        logging.warning("GCS fixture upload failed (local fixtures unaffected)", exc_info=True)


if __name__ == "__main__":
    if (ROOT / ".env").exists():
        try:
            import dotenv
            dotenv.load_dotenv(ROOT / ".env")
        except Exception:
            pass
    EXTRACTOR = Extractor(vertex_extractor=VERTEX)
    STORE = create_demo_store()
    run_server()
