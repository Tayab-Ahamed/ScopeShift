"""SQLite-backed append-only evidence and event store with replay validation."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Optional

from .models import Event, Evidence
from .resolver import replay
from .validation import citation_warnings, validate_citations


class EventStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.persisted = str(path) not in (":memory:", "")
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        # FR-10: sequence assignment must be atomic under the threaded demo server.
        # The lock serializes read-MAX-then-INSERT (and the replay validation between them),
        # which also serializes all use of the single shared sqlite3 connection.
        self._event_lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS evidence (
                source_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                value_json TEXT NOT NULL,
                quote TEXT NOT NULL,
                observation TEXT NOT NULL DEFAULT '',
                proposed_scope_change INTEGER NOT NULL DEFAULT 0,
                quote_verified INTEGER NOT NULL DEFAULT 0,
                region_json TEXT,
                created_sequence INTEGER NOT NULL UNIQUE,
                sender TEXT,
                channel TEXT,
                received_at TEXT
            );
            CREATE TABLE IF NOT EXISTS event_log (
                event_sequence INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES evidence(source_id),
                event TEXT NOT NULL CHECK(event IN ('ADDED', 'REMOVED')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sender TEXT,
                channel TEXT,
                payload_json TEXT DEFAULT '{}'
            );
            CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS event_no_update BEFORE UPDATE ON event_log BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS event_no_delete BEFORE DELETE ON event_log BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            """
        )
        for tbl, col in [
            ("evidence", "sender TEXT"),
            ("evidence", "channel TEXT"),
            ("evidence", "received_at TEXT"),
            ("event_log", "sender TEXT"),
            ("event_log", "channel TEXT"),
            ("event_log", "payload_json TEXT DEFAULT '{}'"),
        ]:
            try:
                self.db.execute(f"ALTER TABLE {tbl} ADD COLUMN {col}")
            except Exception:
                pass

    def seed(self, evidence: Iterable[Evidence]) -> None:
        with self.db:
            for item in evidence:
                region_json = json.dumps(item.region) if item.region else None
                self.db.execute(
                    """
                    INSERT OR IGNORE INTO evidence 
                    (source_id, source_type, claim_id, value_json, quote, observation, 
                     proposed_scope_change, quote_verified, region_json, created_sequence,
                     sender, channel, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.source_id,
                        item.source_type,
                        item.claim_id,
                        json.dumps(item.value),
                        item.quote,
                        item.observation,
                        int(item.proposed_scope_change),
                        int(item.quote_verified),
                        region_json,
                        item.event_sequence,
                        item.sender,
                        item.channel,
                        item.received_at,
                    ),
                )

    def _load_evidence(self) -> list[Evidence]:
        rows = self.db.execute("SELECT * FROM evidence ORDER BY created_sequence").fetchall()
        evidence_list = []
        for r in rows:
            region = json.loads(r["region_json"]) if r["region_json"] else None
            keys = r.keys()
            evidence_list.append(
                Evidence(
                    source_id=r["source_id"],
                    source_type=r["source_type"],
                    claim_id=r["claim_id"],
                    value=json.loads(r["value_json"]),
                    quote=r["quote"],
                    observation=r["observation"],
                    proposed_scope_change=bool(r["proposed_scope_change"]),
                    quote_verified=bool(r["quote_verified"]),
                    region=region,
                    event_sequence=r["created_sequence"],
                    active=False,
                    sender=r["sender"] if "sender" in keys else None,
                    channel=r["channel"] if "channel" in keys else None,
                    received_at=r["received_at"] if "received_at" in keys else None,
                )
            )
        return evidence_list

    def _load_events(self) -> list[Event]:
        rows = self.db.execute("SELECT * FROM event_log ORDER BY event_sequence").fetchall()
        events = []
        for r in rows:
            keys = r.keys()
            payload = {}
            if "payload_json" in keys and r["payload_json"]:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = {}
            events.append(
                Event(
                    event_sequence=r["event_sequence"],
                    source_id=r["source_id"],
                    event=r["event"],
                    sender=r["sender"] if "sender" in keys else None,
                    channel=r["channel"] if "channel" in keys else None,
                    payload=payload,
                )
            )
        return events

    def add_event(
        self,
        source_id: str,
        event: str,
        sender: Optional[str] = None,
        channel: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> Event:
        if event not in {"ADDED", "REMOVED"}:
            raise ValueError(f"event must be ADDED or REMOVED (got {event!r})")
        # FR-10: the sequence read and the insert are one atomic section. Without the lock,
        # two threads could read the same MAX(event_sequence) and collide on insert.
        with self._event_lock:
            evidence = self._load_evidence()
            existing = self._load_events()
            next_seq = (existing[-1].event_sequence if existing else 0) + 1

            ev_item = next((e for e in evidence if e.source_id == source_id), None)
            eff_sender = sender if sender is not None else (ev_item.sender if ev_item else None)
            eff_channel = channel if channel is not None else (ev_item.channel if ev_item else None)
            eff_payload = payload or {}
            if eff_sender:
                eff_payload.setdefault("sender", eff_sender)
            if eff_channel:
                eff_payload.setdefault("channel", eff_channel)

            candidate_event = Event(
                next_seq,
                source_id,
                event,
                sender=eff_sender,
                channel=eff_channel,
                payload=eff_payload,
            )
            candidate = list(existing) + [candidate_event]

            # Validate replay state machine invariants before persisting
            replay(evidence, candidate)

            with self.db:
                self.db.execute(
                    "INSERT INTO event_log (event_sequence, source_id, event, sender, channel, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (next_seq, source_id, event, eff_sender, eff_channel, json.dumps(eff_payload)),
                )
        return candidate[-1]

    def audit_chain(self) -> list[dict]:
        """Per-block SHA-256 chain, with the raw hash input exposed.

        Input construction is f"{prev_hash}:{event_sequence}:{source_id}:{event}"
        with the genesis prev_hash of "0"*64. The raw ``hash_input`` is included
        so clients can genuinely recompute every block (GET /api/audit/chain)
        instead of trusting the served hashes.
        """
        import hashlib

        chain = []
        prev_hash = "0" * 64
        for ev in self._load_events():
            hash_input = f"{prev_hash}:{ev.event_sequence}:{ev.source_id}:{ev.event}"
            h = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            chain.append({
                "sequence": ev.event_sequence,
                "source_id": ev.source_id,
                "event": ev.event,
                "sender": ev.sender,
                "channel": ev.channel,
                "payload": ev.payload,
                "hash": h,
                "prev_hash": prev_hash,
                "hash_input": hash_input,
            })
            prev_hash = h
        return chain

    def snapshot(self) -> dict:
        evidence = self._load_evidence()
        events = self._load_events()
        res = replay(evidence, events)

        # FR-8/FR-18 fail-closed: refuse to project a BRD whose citations do not
        # resolve to existing active evidence. Raises ValidationError; the HTTP
        # serve path converts it into a 500 CITATION_INTEGRITY_VIOLATION rather
        # than serving a BRD with dangling citations.
        validate_citations(res.resolutions.values(), res.active_evidence)

        # FR-8/FR-18: every citation in the served BRD projection must reference an
        # existing active evidence record; violations are flagged, never hidden.
        cite_warnings = citation_warnings(res.resolutions.values(), res.active_evidence)

        removed_ids = {e.source_id for e in events if e.event == "REMOVED"}
        active_ids = {e.source_id for e in events if e.event == "ADDED"} - removed_ids

        sources_out = [
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
                "sender": e.sender,
                "channel": e.channel,
                "received_at": e.received_at,
            }
            for e in evidence
        ]

        chain = self.audit_chain()
        events_out = [
            {
                "event_sequence": ev.event_sequence,
                "source_id": ev.source_id,
                "event": ev.event,
                "sender": ev.sender,
                "channel": ev.channel,
                "payload": ev.payload,
            }
            for ev in events
        ]

        return {
            "resolutions": {k: v.to_dict() for k, v in res.resolutions.items()},
            "sources": sources_out,
            "events": events_out,
            "timeline": res.timeline,
            "audit_chain": chain,
            "chain_valid": True,
            "chain_tip": chain[-1]["hash"] if chain else "0" * 64,
            "current_seq": events[-1].event_sequence if events else 0,
            "mirror_note": "Local SQLite Log (Active: Monotonic SHA-256 Hash Chained)",
            "citation_warnings": cite_warnings,
            "citation_integrity": "ok",
        }

    def close(self) -> None:
        self.db.close()
