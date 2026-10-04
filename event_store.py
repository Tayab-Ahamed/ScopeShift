"""SQLite-backed append-only evidence and event store for the demo."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from scopeshift_core import Evidence, Event, replay


class EventStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS evidence (
                source_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                value_json TEXT NOT NULL,
                quote TEXT NOT NULL,
                proposed_scope_change INTEGER NOT NULL,
                quote_verified INTEGER NOT NULL,
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

    def seed(self, evidence: list[Evidence]) -> None:
        with self.db:
            for item in evidence:
                self.db.execute(
                    "INSERT OR IGNORE INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (item.source_id, item.source_type, item.claim_id, json.dumps(item.value), item.quote,
                     int(item.proposed_scope_change), int(item.quote_verified), item.event_sequence),
                )

    def add_event(self, source_id: str, event: str) -> Event:
        if event not in {"ADDED", "REMOVED"}:
            raise ValueError("event must be ADDED or REMOVED")
        rows = self.db.execute("SELECT * FROM evidence ORDER BY created_sequence").fetchall()
        evidence = [self._evidence(row, False) for row in rows]
        existing = self.db.execute("SELECT source_id, event, event_sequence FROM event_log ORDER BY event_sequence").fetchall()
        next_sequence = (existing[-1]["event_sequence"] if existing else 0) + 1
        candidate = [Event(r["event_sequence"], r["source_id"], r["event"]) for r in existing]
        candidate.append(Event(next_sequence, source_id, event))
        replay(evidence, candidate)  # validate before persisting
        with self.db:
            self.db.execute("INSERT INTO event_log(event_sequence, source_id, event) VALUES (?, ?, ?)", (next_sequence, source_id, event))
        return candidate[-1]

    def snapshot(self) -> dict:
        rows = self.db.execute("SELECT * FROM evidence ORDER BY created_sequence").fetchall()
        evidence = [self._evidence(row, False) for row in rows]
        events_rows = self.db.execute("SELECT event_sequence, source_id, event FROM event_log ORDER BY event_sequence").fetchall()
        events = [Event(r["event_sequence"], r["source_id"], r["event"]) for r in events_rows]
        state = replay(evidence, events)
        removed = {e.source_id for e in events if e.event == "REMOVED"}
        active = {e.source_id for e in events if e.event == "ADDED"} - removed
        return {
            "state": state,
            "sources": [{"id": e.source_id, "type": e.source_type, "quote": e.quote, "active": e.source_id in active} for e in evidence],
            "events": [e.__dict__ for e in events],
            "mirror_note": "SQLite is the local persisted append-only log. The UI reads a replayed snapshot of it.",
        }

    @staticmethod
    def _evidence(row: sqlite3.Row, active: bool) -> Evidence:
        return Evidence(row["source_id"], row["source_type"], row["claim_id"], json.loads(row["value_json"]), row["quote"],
                        bool(row["proposed_scope_change"]), bool(row["quote_verified"]), row["created_sequence"], active)

    def close(self) -> None:
        self.db.close()
