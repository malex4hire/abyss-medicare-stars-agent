#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
DATASET="medicare_stars_demo"
TABLE="member_experience"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "No active Google Cloud project." >&2
  exit 1
fi

gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com \
  --project="$PROJECT_ID" --quiet

if ! bq show --project_id="$PROJECT_ID" "$DATASET" >/dev/null 2>&1; then
  bq --location=US mk --dataset \
    --description="Synthetic aggregate Medicare Stars demo data" \
    "${PROJECT_ID}:${DATASET}"
fi

bq --location=US load --replace \
  --source_format=CSV \
  --skip_leading_rows=1 \
  "${PROJECT_ID}:${DATASET}.${TABLE}" \
  "$ROOT_DIR/data/member_experience.csv" \
  'contract_id:STRING,year:INT64,measure_code:STRING,measure_name:STRING,score:FLOAT64,denominator:INT64'

echo "Ready: ${PROJECT_ID}.${DATASET}.${TABLE}"

