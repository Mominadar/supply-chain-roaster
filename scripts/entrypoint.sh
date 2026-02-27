#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"
DATA_DIR="${APP_DIR}/data"

echo "[startup] Working dir: ${APP_DIR}"
mkdir -p "${DATA_DIR}"

# Detect Cloud Run via K_SERVICE and log only
if [[ -n "${K_SERVICE:-}" ]]; then
  echo "[startup] Detected Cloud Run (K_SERVICE=${K_SERVICE}); using baked-in ${DATA_DIR}"
else
  echo "[startup] Non-Cloud Run environment; using local mounts if provided (e.g., ./data:/app/data)"
fi

# Start Streamlit
PORT_ARG="${PORT:-8501}"
echo "[startup] Starting Streamlit on port ${PORT_ARG}"
exec streamlit run ui/app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT_ARG}" \
  --server.headless true
