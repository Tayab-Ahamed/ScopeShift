#!/usr/bin/env python3
"""Google Cloud live verification probe for ScopeShift.

Performs one real Vertex AI extraction, one GCS upload + signed-URL fetch,
and one BigQuery insert + select read-back.

Without credentials or required env vars, it prints which variables are
missing and exits non-zero. Never fakes a PASS.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scopeshift.cloud import (
    BQ_DATASET_ENV,
    GCS_BUCKET_ENV,
    GCP_LOCATION_ENV,
    GCP_PROJECT_ENV,
    BigQueryLog,
    GCSOriginals,
    VertexExtractor,
)
from scopeshift.extraction import EXTRACTION_PROMPT


def check_prerequisites() -> tuple[bool, list[str]]:
    """Check required environment variables and credentials."""
    missing: list[str] = []

    project = os.environ.get(GCP_PROJECT_ENV)
    location = os.environ.get(GCP_LOCATION_ENV)
    bq_dataset = os.environ.get(BQ_DATASET_ENV)
    gcs_bucket = os.environ.get(GCS_BUCKET_ENV)

    if not project:
        missing.append(f"{GCP_PROJECT_ENV} (Google Cloud Project ID)")
    if not location:
        missing.append(f"{GCP_LOCATION_ENV} (e.g. us-central1)")
    if not bq_dataset:
        missing.append(f"{BQ_DATASET_ENV} (BigQuery dataset ID, e.g. scopeshift_events)")
    if not gcs_bucket:
        missing.append(f"{GCS_BUCKET_ENV} (GCS bucket name)")

    # Check credentials
    creds_ok = False
    try:
        import google.auth

        google.auth.default()
        creds_ok = True
    except Exception as exc:
        creds_ok = False
        missing.append(
            f"Google Cloud Credentials (GOOGLE_APPLICATION_CREDENTIALS or 'gcloud auth application-default login'): {exc}"
        )

    return len(missing) == 0, missing


def verify_vertex(project: str, location: str) -> tuple[bool, str]:
    """Perform one real Vertex AI extraction."""
    print("--> Probing Vertex AI extraction...")
    try:
        extractor = VertexExtractor(project=project, location=location)
        status = extractor.status()
        if not status["connected"]:
            return False, f"VertexExtractor not connected: {status['reason']}"

        test_text = (
            "REQ-PAY-01: Checkout shall support UPI payments only.\n"
            "Business rule: UPI is the exclusive payment method for v1.0."
        )
        res = extractor.extract_claims(test_text, "brd", EXTRACTION_PROMPT)
        if not res or not res.get("claims"):
            return False, "Vertex extraction returned 0 claims or None"

        claims_count = len(res["claims"])
        latency = res.get("latency_ms", 0)
        return True, f"Extracted {claims_count} claim(s) in {latency}ms ({res.get('model')})"
    except Exception as exc:
        return False, f"Vertex exception: {type(exc).__name__}: {exc}"


def verify_gcs(bucket_name: str) -> tuple[bool, str]:
    """Perform one GCS upload and signed-URL fetch."""
    print("--> Probing Google Cloud Storage (upload + signed URL)...")
    try:
        gcs = GCSOriginals(bucket=bucket_name)
        status = gcs.status()
        if not status["connected"]:
            return False, f"GCSOriginals not connected: {status['reason']}"

        timestamp = int(time.time())
        blob_name = f"_scopeshift_verify_{timestamp}.txt"
        test_payload = f"ScopeShift verification probe {timestamp}\n".encode("utf-8")

        # 1. Upload
        if not gcs.upload(blob_name, test_payload, content_type="text/plain"):
            return False, "Failed to upload test blob to GCS"

        # 2. Mint signed URL
        signed = gcs.signed_url(blob_name, minutes=5)
        if not signed:
            return False, "Failed to generate signed URL"

        # 3. Fetch signed URL
        req = urllib.request.Request(signed, headers={"User-Agent": "ScopeShift-Verify/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if content != test_payload:
                return False, f"Signed URL content mismatch (got {len(content)} bytes)"

        return True, f"Uploaded {blob_name} and verified read-back via signed URL"
    except Exception as exc:
        return False, f"GCS exception: {type(exc).__name__}: {exc}"


def verify_bigquery(dataset_id: str) -> tuple[bool, str]:
    """Perform one BigQuery insert and select read-back."""
    print("--> Probing BigQuery (insert + select read-back)...")
    try:
        bq = BigQueryLog(dataset=dataset_id)
        status = bq.status()
        if not status["connected"]:
            return False, f"BigQueryLog not connected: {status['reason']}"

        probe_seq = 999900000 + int(time.time() % 100000)
        probe_event = {
            "event_sequence": probe_seq,
            "source_id": "SRC-PROBE",
            "event": "PROBE",
            "payload": {"verification": True, "timestamp": time.time()},
        }

        # 1. Insert row
        if not bq.append(probe_event):
            return False, "BigQuery append failed"

        # Allow slight eventual consistency buffer if needed
        time.sleep(1.0)

        # 2. Read back
        row = bq.verify_read_back(probe_seq)
        if not row:
            return False, f"BigQuery read-back failed: row with sequence {probe_seq} not found"

        if row.get("source_id") != "SRC-PROBE" or row.get("event") != "PROBE":
            return False, f"BigQuery read-back content mismatch: {row}"

        return True, f"Inserted event sequence {probe_seq} and verified read-back"
    except Exception as exc:
        return False, f"BigQuery exception: {type(exc).__name__}: {exc}"


def main() -> int:
    print("=" * 70)
    print("ScopeShift Google Cloud Verification Suite")
    print("=" * 70)

    ok, missing = check_prerequisites()
    if not ok:
        print("\n[!] MISSING GOOGLE CLOUD CONFIGURATION / CREDENTIALS:")
        for item in missing:
            print(f"    - {item}")
        print("\nCannot verify cloud services without credentials. Exiting with code 1.")
        print("To configure, see docs/GOOGLE_CLOUD_SETUP.md")
        return 1

    project = os.environ[GCP_PROJECT_ENV]
    location = os.environ[GCP_LOCATION_ENV]
    dataset = os.environ[BQ_DATASET_ENV]
    bucket = os.environ[GCS_BUCKET_ENV]

    results: dict[str, tuple[bool, str]] = {}

    results["Vertex AI"] = verify_vertex(project, location)
    results["Cloud Storage"] = verify_gcs(bucket)
    results["BigQuery"] = verify_bigquery(dataset)

    print("\n" + "=" * 70)
    print("Verification Summary:")
    print("=" * 70)
    all_passed = True
    for service, (passed, msg) in results.items():
        status_tag = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_tag:6s} {service:<15s}: {msg}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL CLOUD SERVICES OPERATIONAL (PASS)")
        return 0
    else:
        print("SOME CLOUD SERVICES FAILED VERIFICATION")
        return 1


if __name__ == "__main__":
    sys.exit(main())
