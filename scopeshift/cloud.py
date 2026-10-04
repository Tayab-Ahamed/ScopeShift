"""Tier 1 GCP integrations for ScopeShift (env-gated, import-guarded).

Three service adapters — BigQueryLog, GCSOriginals, VertexExtractor — each with
the same contract:

- Importing this module NEVER raises and NEVER needs network/credentials.
- Each adapter probes (SDK installed? env vars set? credentials resolve?) and
  either connects or degrades to an honest no-op.
- ``status()`` always returns ``{"connected": bool, "reason": str}`` where
  ``reason`` is honest ("no credentials", "sdk not installed",
  "env SCOPESHIFT_BQ_DATASET unset", "ok", ...).

The demo server dual-writes events to BigQuery best-effort (never failing the
request) and serves artifacts from GCS signed URLs when connected, otherwise
local /fixtures paths. Everything works fully offline.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any, Optional

log = logging.getLogger("scopeshift.cloud")

BQ_DATASET_ENV = "SCOPESHIFT_BQ_DATASET"
GCS_BUCKET_ENV = "SCOPESHIFT_GCS_BUCKET"
GCP_PROJECT_ENV = "GOOGLE_CLOUD_PROJECT"
GCP_LOCATION_ENV = "GOOGLE_CLOUD_LOCATION"

_NO_CRED_REASON = (
    "no credentials (GOOGLE_APPLICATION_CREDENTIALS unset and no default credentials)"
)


def _sdk_available(dotted: str) -> bool:
    """True if ``import dotted`` works — never raises, never hits network."""
    try:
        __import__(dotted)
        return True
    except Exception:
        return False


def _default_credentials():
    """Resolve Application Default Credentials. Raises when none are available."""
    import google.auth  # part of the google-cloud SDKs; import-guarded by callers
    return google.auth.default()


def _event_fields(event: Any) -> tuple:
    """Accept an Event dataclass or a plain dict."""
    if isinstance(event, dict):
        return event.get("event_sequence"), event.get("source_id"), event.get("event")
    return (
        getattr(event, "event_sequence", None),
        getattr(event, "source_id", None),
        getattr(event, "event", None),
    )


class BigQueryLog:
    """Append-only BigQuery mirror of the event log.

    Table ``<dataset>.scopeshift_events`` with schema
    (event_sequence INT64, source_id STRING, event STRING, payload JSON,
    inserted_at TIMESTAMP). When the SDK, env var, or credentials are missing,
    ``append`` is a no-op returning False.
    """

    TABLE = "scopeshift_events"

    def __init__(self, dataset: Optional[str] = None, table: Optional[str] = None):
        self.dataset_id = dataset or os.environ.get(BQ_DATASET_ENV)
        self.table_id = table or self.TABLE
        self._client = None
        self._connected = False
        self._reason = "not initialized"
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            if not _sdk_available("google.cloud.bigquery"):
                self._reason = "sdk not installed (pip install google-cloud-bigquery)"
                return
            if not self.dataset_id:
                self._reason = f"env {BQ_DATASET_ENV} unset"
                return
            from google.cloud import bigquery

            try:
                creds, adc_project = _default_credentials()
            except Exception:
                self._reason = _NO_CRED_REASON
                return
            project = os.environ.get(GCP_PROJECT_ENV) or adc_project
            self._client = bigquery.Client(project=project, credentials=creds)
            self._ensure_table()
            self._connected = True
            self._reason = "ok"
        except Exception as exc:  # pragma: no cover - connection-time failures
            self._client = None
            self._connected = False
            self._reason = f"connection failed: {type(exc).__name__}"
            log.warning("BigQueryLog unavailable: %s", self._reason)

    def _ensure_table(self) -> None:
        from google.cloud import bigquery

        client = self._client
        ds_ref = client.dataset(self.dataset_id)
        try:
            client.get_dataset(ds_ref)
        except Exception:
            client.create_dataset(ds_ref)
        table_ref = ds_ref.table(self.table_id)
        try:
            client.get_table(table_ref)
        except Exception:
            schema = [
                bigquery.SchemaField("event_sequence", "INT64"),
                bigquery.SchemaField("source_id", "STRING"),
                bigquery.SchemaField("event", "STRING"),
                bigquery.SchemaField("payload", "JSON"),
                bigquery.SchemaField("inserted_at", "TIMESTAMP"),
            ]
            client.create_table(bigquery.Table(table_ref, schema=schema))

    def status(self) -> dict:
        return {"connected": self._connected, "reason": self._reason}

    def append(self, event: Any) -> bool:
        """Stream one event row. Never raises; returns False when disconnected."""
        if not self._connected or self._client is None:
            return False
        try:
            seq, source_id, event_name = _event_fields(event)
            row = {
                "event_sequence": seq,
                "source_id": source_id,
                "event": event_name,
                "payload": json.dumps({"source_id": source_id, "event": event_name}),
                "inserted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            errors = self._client.insert_rows_json(
                f"{self.dataset_id}.{self.table_id}", [row]
            )
            if errors:
                log.warning("BigQuery insert returned errors: %s", errors)
                return False
            return True
        except Exception:
            log.warning("BigQuery append failed (local log unaffected)", exc_info=True)
            return False


class GCSOriginals:
    """Original evidence artifacts in a Cloud Storage bucket.

    Uploads fixtures/ingested originals and mints short-lived signed URLs for the
    artifact inspector. When the SDK, env var, or credentials are missing, every
    method is a no-op and callers serve local /fixtures paths.
    """

    def __init__(self, bucket: Optional[str] = None):
        self.bucket_name = bucket or os.environ.get(GCS_BUCKET_ENV)
        self._client = None
        self._bucket = None
        self._connected = False
        self._reason = "not initialized"
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            if not _sdk_available("google.cloud.storage"):
                self._reason = "sdk not installed (pip install google-cloud-storage)"
                return
            if not self.bucket_name:
                self._reason = f"env {GCS_BUCKET_ENV} unset"
                return
            from google.cloud import storage

            try:
                creds, _ = _default_credentials()
            except Exception:
                self._reason = _NO_CRED_REASON
                return
            self._client = storage.Client(credentials=creds)
            self._bucket = self._client.bucket(self.bucket_name)
            if not self._bucket.exists():
                self._reason = f"bucket {self.bucket_name!r} not found"
                self._bucket = None
                return
            self._connected = True
            self._reason = "ok"
        except Exception as exc:  # pragma: no cover - connection-time failures
            self._client = None
            self._bucket = None
            self._connected = False
            self._reason = f"connection failed: {type(exc).__name__}"
            log.warning("GCSOriginals unavailable: %s", self._reason)

    def status(self) -> dict:
        return {"connected": self._connected, "reason": self._reason}

    def upload(self, name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload one original artifact. Never raises; returns False when disconnected."""
        if not self._connected or self._bucket is None:
            return False
        try:
            blob = self._bucket.blob(name)
            blob.upload_from_string(data, content_type=content_type)
            return True
        except Exception:
            log.warning("GCS upload failed for %s (local fixtures unaffected)", name, exc_info=True)
            return False

    def signed_url(self, name: str, minutes: int = 15) -> Optional[str]:
        """Short-lived signed URL for an artifact, or None when unavailable."""
        if not self._connected or self._bucket is None:
            return None
        try:
            blob = self._bucket.blob(name)
            return blob.generate_signed_url(
                expiration=datetime.timedelta(minutes=minutes)
            )
        except Exception:
            log.warning("GCS signed URL failed for %s", name, exc_info=True)
            return None


class VertexExtractor:
    """Gemini extraction routed through the Vertex AI endpoint.

    Requires the google-cloud-aiplatform SDK plus GOOGLE_CLOUD_PROJECT and
    GOOGLE_CLOUD_LOCATION. Otherwise ``extract_claims`` returns None and the
    caller falls back to the google-genai path / deterministic fallback.
    """

    def __init__(
        self,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ):
        self.project = project or os.environ.get(GCP_PROJECT_ENV)
        self.location = location or os.environ.get(GCP_LOCATION_ENV)
        self.model = model
        self._model = None
        self._connected = False
        self._reason = "not initialized"
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            if not (_sdk_available("vertexai") or _sdk_available("google.cloud.aiplatform")):
                self._reason = "sdk not installed (pip install google-cloud-aiplatform)"
                return
            if not self.project or not self.location:
                missing = [e for e, v in ((GCP_PROJECT_ENV, self.project), (GCP_LOCATION_ENV, self.location)) if not v]
                self._reason = f"env {'/'.join(missing)} unset"
                return
            import vertexai
            from vertexai.generative_models import GenerativeModel

            # Local config only — no network at init.
            vertexai.init(project=self.project, location=self.location)
            self._model = GenerativeModel(self.model)
            self._connected = True
            self._reason = "ok"
        except Exception as exc:  # pragma: no cover - connection-time failures
            self._model = None
            self._connected = False
            self._reason = f"connection failed: {type(exc).__name__}"
            log.warning("VertexExtractor unavailable: %s", self._reason)

    def status(self) -> dict:
        return {"connected": self._connected, "reason": self._reason}

    def extract_claims(self, text: str, source_type: str, prompt: str) -> Optional[dict]:
        """Run extraction via the Vertex endpoint. None on any failure."""
        if not self._connected or self._model is None:
            return None
        import time

        start = time.time()
        try:
            resp = self._model.generate_content(
                f"{prompt}\nSource Type: {source_type}\nText:\n{text}",
                generation_config={"response_mime_type": "application/json"},
            )
            claims = json.loads(resp.text)
            return {
                "claims": claims,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "model": f"{self.model} (vertex)",
            }
        except Exception:
            log.warning("Vertex extraction failed (falling back)", exc_info=True)
            return None


def cloud_status(
    bq: Optional[BigQueryLog] = None,
    gcs: Optional[GCSOriginals] = None,
    vertex: Optional[VertexExtractor] = None,
) -> dict:
    """Honest per-service status snapshot."""
    return {
        "bigquery": (bq or BigQueryLog()).status(),
        "gcs": (gcs or GCSOriginals()).status(),
        "vertex": (vertex or VertexExtractor()).status(),
    }
