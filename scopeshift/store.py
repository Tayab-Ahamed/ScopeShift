"""SQLite-backed append-only evidence and event store with replay validation."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Event, Evidence
from .resolver import replay


class EventStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
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
                created_sequence INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS event_log (
                event_sequence INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES evidence(source_id),
                event TEXT NOT NULL CHECK(event IN ('ADDED', 'REMOVED')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS event_no_update BEFORE UPDATE ON event_log BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS event_no_delete BEFORE DELETE ON event_log BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            """
        )

    def seed(self, evidence: Iterable[Evidence]) -> None:
        with self.db:
            for item in evidence:
                region_json = json.dumps(item.region) if item.region else None
                self.db.execute(
                    """
                    INSERT OR IGNORE INTO evidence 
                    (source_id, source_type, claim_id, value_json, quote, observation, 
                     proposed_scope_change, quote_verified, region_json, created_sequence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )

    def _load_evidence(self) -> list[Evidence]:
        rows = self.db.execute("SELECT * FROM evidence ORDER BY created_sequence").fetchall()
        evidence_list = []
        for r in rows:
            region = json.loads(r["region_json"]) if r["region_json"] else None
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
                )
            )
        return evidence_list

    def _load_events(self) -> list[Event]:
        rows = self.db.execute("SELECT event_sequence, source_id, event FROM event_log ORDER BY event_sequence").fetchall()
        return [Event(r["event_sequence"], r["source_id"], r["event"]) for r in rows]

    def add_event(self, source_id: str, event: str) -> Event:
        if event not in {"ADDED", "REMOVED"}:
            raise ValueError(f"event must be ADDED or REMOVED (got {event!r})")
        evidence = self._load_evidence()
        existing = self._load_events()
        next_seq = (existing[-1].event_sequence if existing else 0) + 1
        candidate = list(existing) + [Event(next_seq, source_id, event)]

        # Validate replay state machine invariants before persisting
        replay(evidence, candidate)

        with self.db:
            self.db.execute(
                "INSERT INTO event_log (event_sequence, source_id, event) VALUES (?, ?, ?)",
                (next_seq, source_id, event),
            )
        return candidate[-1]

    def snapshot(self) -> dict:
        evidence = self._load_evidence()
        events = self._load_events()
        res = replay(evidence, events)

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
                "active": e.source_id in active_ids,
            }
            for e in evidence
        ]

        import hashlib
        chain = []
        prev_hash = "0" * 64
        for ev in events:
            h = hashlib.sha256(f"{prev_hash}:{ev.event_sequence}:{ev.source_id}:{ev.event}".encode("utf-8")).hexdigest()
            chain.append({"sequence": ev.event_sequence, "source_id": ev.source_id, "event": ev.event, "hash": h, "prev_hash": prev_hash})
            prev_hash = h

        return {
            "resolutions": {k: v.to_dict() for k, v in res.resolutions.items()},
            "sources": sources_out,
            "events": [e.__dict__ for e in events],
            "timeline": res.timeline,
            "audit_chain": chain,
            "mirror_note": "SQLite is the local persisted append-only log. The UI reads a replayed snapshot of it.",
        }

    def close(self) -> None:
        self.db.close()
