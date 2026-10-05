# Google Cloud Setup & Verification Guide

This guide describes how to configure, provision, and verify the Tier-1 Google Cloud integrations for ScopeShift:
1. **Vertex AI** (`google-genai` SDK with `vertexai=True` for structured claim extraction)
2. **Cloud Storage (GCS)** (Ingested evidence artifact storage and signed URLs)
3. **BigQuery** (Append-only cloud event ledger dual-write)

---

## 1. Prerequisites

- Google Cloud CLI (`gcloud`) installed and updated:
  ```bash
  gcloud components update
  ```
- An active GCP billing project.

Set your project variables:
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export BQ_DATASET="scopeshift_events"
export GCS_BUCKET="${PROJECT_ID}-scopeshift-artifacts"

gcloud config set project "$PROJECT_ID"
```

---

## 2. Enable Required Google Cloud APIs

Enable the Vertex AI, BigQuery, and Google Cloud Storage APIs:
```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com
```

---

## 3. Provision Cloud Storage Bucket

Create a dedicated bucket for evidence originals (PDFs, screenshots, client notes):
```bash
gcloud storage buckets create "gs://${GCS_BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access
```

---

## 4. Provision BigQuery Dataset

Create the append-only BigQuery dataset:
```bash
bq --location="${REGION}" mk \
  --dataset \
  --description="ScopeShift append-only event ledger mirror" \
  "${PROJECT_ID}:${BQ_DATASET}"
```

*(Note: The table `scopeshift_events` with schema `(event_sequence INT64, source_id STRING, event STRING, payload JSON, inserted_at TIMESTAMP)` is auto-provisioned by `scopeshift.cloud.BigQueryLog` on first connection).*

---

## 5. Service Account and IAM Roles

Create a service account for ScopeShift:
```bash
gcloud iam service-accounts create scopeshift-sa \
  --description="ScopeShift Cloud Runner Service Account" \
  --display-name="ScopeShift Service Account"

export SA_EMAIL="scopeshift-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

Grant the required permissions:
```bash
# 1. Vertex AI user
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# 2. BigQuery Data Editor and Job User
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.jobUser"

# 3. Storage Object Admin
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"
```

Generate service account key credentials (or use Workload Identity on Cloud Run / GKE):
```bash
gcloud iam service-accounts keys create ./scopeshift-key.json \
  --iam-account="${SA_EMAIL}"

export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/scopeshift-key.json"
```

Alternatively, for local developer testing, log in with Application Default Credentials:
```bash
gcloud auth application-default login
```

---

## 6. Configure Environment Variables

Create or update your `.env` file with the provisioned resources:
```env
GOOGLE_APPLICATION_CREDENTIALS=./scopeshift-key.json
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
SCOPESHIFT_BQ_DATASET=scopeshift_events
SCOPESHIFT_GCS_BUCKET=your-gcp-project-id-scopeshift-artifacts
```

---

## 7. Verify Cloud Services

Run the automated live verification probe:
```bash
python scripts/verify_cloud.py
```

The script performs:
1. One real Vertex AI extraction using `google-genai` SDK with `vertexai=True` and structured JSON schema.
2. One Cloud Storage artifact upload and signed-URL fetch.
3. One BigQuery row append and select read-back.

### Behavior Guarantee
- If credentials or configuration are missing, `scripts/verify_cloud.py` outputs the exact missing fields and exits with code `1`.
- It **never fakes a PASS**.
