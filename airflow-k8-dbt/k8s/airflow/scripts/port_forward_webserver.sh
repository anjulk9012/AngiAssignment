#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="airflow"
LOCAL_PORT=8080
TARGET_PORT=8080

echo ">>> Looking for webserver service in namespace '$NAMESPACE'..."
SVC_NAME=$(kubectl get svc -n "$NAMESPACE" \
  --no-headers \
  | awk '/webserver/ {print $1}' \
  | head -n 1 \
  || true)

if [[ -n "${SVC_NAME:-}" ]]; then
  echo ">>> Found service: $SVC_NAME"
  echo ">>> Port-forwarding svc/$SVC_NAME:$TARGET_PORT -> localhost:$LOCAL_PORT ..."
  kubectl port-forward "svc/$SVC_NAME" "$LOCAL_PORT:$TARGET_PORT" -n "$NAMESPACE"
  exit 0
fi

echo ">>> No webserver service found, trying webserver pod..."
POD_NAME=$(kubectl get pods -n "$NAMESPACE" \
  --no-headers \
  | awk '/webserver/ && $3=="Running" {print $1}' \
  | head -n 1 \
  || true)

if [[ -n "${POD_NAME:-}" ]]; then
  echo ">>> Found pod: $POD_NAME"
  echo ">>> Port-forwarding pod/$POD_NAME:$TARGET_PORT -> localhost:$LOCAL_PORT ..."
  kubectl port-forward "pod/$POD_NAME" "$LOCAL_PORT:$TARGET_PORT" -n "$NAMESPACE"
  exit 0
fi

echo "!!! No webserver service or running pod found in namespace '$NAMESPACE'."
kubectl get pods -n "$NAMESPACE"
exit 1
