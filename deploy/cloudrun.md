# Deploy ScopeShift to Google Cloud Run

This guide describes how to deploy ScopeShift to **Google Cloud Run** with production container configuration, service account IAM authentication, and health checks.

---

## 1. Prerequisites

- Google Cloud SDK (`gcloud`) installed and authorized.
- Docker or Cloud Build enabled.
- GCP Project with Cloud Run API enabled:
  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

Set your configuration variables:
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export SERVICE_NAME="scopeshift"
export ARTIFACT_REPO="scopeshift-repo"
export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/scopeshift:latest"
```

---

## 2. Create Artifact Registry Repository (Optional / Recommended)

```bash
gcloud artifacts repositories create "${ARTIFACT_REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="ScopeShift Docker images"
```

---

## 3. Build Container Image

Build the container image using Google Cloud Build:
```bash
gcloud builds submit --tag "${IMAGE_TAG}" .
```

---

## 4. Required Environment Variables

When deploying to Cloud Run, configure the following environment variables:

| Variable | Description | Example / Default |
|:---|:---|:---|
| `HOST` | Bind address inside container | `0.0.0.0` |
| `PORT` | Listening port (injected by Cloud Run) | `8080` |
| `SCOPESHIFT_DB` | SQLite DB path (ephemeral or persistent volume) | `/app/events.db` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID for Vertex AI and BigQuery | `${PROJECT_ID}` |
| `GOOGLE_CLOUD_LOCATION` | Region for Vertex AI extraction endpoint | `us-central1` |
| `SCOPESHIFT_BQ_DATASET` | BigQuery dataset ID for event ledger mirroring | `scopeshift_events` |
| `SCOPESHIFT_GCS_BUCKET` | Cloud Storage bucket for evidence artifacts | `${PROJECT_ID}-scopeshift-artifacts` |
| `SCOPESHIFT_APPROVERS` | Path to approver allowlist JSON | `./approvers.json` |
| `GEMINI_API_KEY` | (Optional) Direct Gemini API key if not using Vertex AI | `AIza...` |

---

## 5. Deploy to Cloud Run

Run `gcloud run deploy`:

```bash
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_TAG}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8765 \
  --memory 1Gi \
  --cpu 1 \
  --service-account "scopeshift-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "\
HOST=0.0.0.0,\
PORT=8765,\
GOOGLE_CLOUD_PROJECT=${PROJECT_ID},\
GOOGLE_CLOUD_LOCATION=${REGION},\
SCOPESHIFT_BQ_DATASET=scopeshift_events,\
SCOPESHIFT_GCS_BUCKET=${PROJECT_ID}-scopeshift-artifacts,\
SCOPESHIFT_APPROVERS=./approvers.json,\
SCOPESHIFT_DB=/app/events.db"
```

*(Note: Cloud Run injects `PORT=8080` by default; omitting `--port 8765` will let ScopeShift bind automatically to whatever port Cloud Run provides via the `PORT` env var).*

---

## 6. Verify Deployment

1. Check health endpoint:
   ```bash
   SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')
   curl -s "${SERVICE_URL}/api/health" | jq .
   ```
   Expected response:
   ```json
   {
     "status": "ok",
     "persisted": true,
     "events": 2,
     "db_path": "/app/events.db",
     "uptime_seconds": 12.3
   }
   ```

2. Check Cloud status endpoint:
   ```bash
   curl -s "${SERVICE_URL}/api/cloud/status" | jq .
   ```
   Reports the live status of BigQuery, Cloud Storage, Vertex AI, and extraction route.
