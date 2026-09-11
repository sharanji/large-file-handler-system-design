#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Environment file '.env' not found"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

PROJECT_ID="${GCP_PROJECT_ID:-largefile-upload-design}"
SERVICE_NAME="${SERVICE_NAME:-largefile-searching-system}"
REGION="${REGION:-us-central1}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

PLATFORM="managed"
PORT="8080"

MEMORY="512Mi"
CPU="1"
MIN_INSTANCES="0"
MAX_INSTANCES="1"
CONCURRENCY="8"

ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" =~ ^[[:space:]]*$ ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  [[ "$key" == "GOOGLE_APPLICATION_CREDENTIALS" ]] && continue
  printf '%s: "%s"\n' "$key" "$value"
done < .env > "$ENV_FILE"

echo "Using environment: .env"
echo "Resources: memory=${MEMORY} cpu=${CPU} min=${MIN_INSTANCES} max=${MAX_INSTANCES} concurrency=${CONCURRENCY}"

echo "Checking gcloud auth..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" || {
  echo "Not logged in to gcloud"
  exit 1
}

echo "Setting project..."
gcloud config set project "${PROJECT_ID}"

echo "Building and pushing Docker image..."
gcloud builds submit --tag "${IMAGE}" "${ROOT}"

echo "Deploying to Cloud Run..."

DEPLOY_CMD=(
  gcloud run deploy "${SERVICE_NAME}"
  --image "${IMAGE}"
  --timeout 120
  --region "${REGION}"
  --platform "${PLATFORM}"
  --memory "${MEMORY}"
  --cpu "${CPU}"
  --min-instances "${MIN_INSTANCES}"
  --max-instances "${MAX_INSTANCES}"
  --concurrency "${CONCURRENCY}"
  --cpu-throttling
  --port "${PORT}"
  --env-vars-file "${ENV_FILE}"
  --allow-unauthenticated
  --tag dev
)

"${DEPLOY_CMD[@]}"

echo "Deployment completed successfully!"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format="value(status.url)"
