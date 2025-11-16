#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="airflow"
RELEASE_NAME="airflow"

echo ">>> Uninstalling Helm release '$RELEASE_NAME' in namespace '$NAMESPACE'..."
helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || echo "Helm release not found, skipping."

echo ">>> Deleting MySQL deployment and service (if they exist)..."
kubectl delete -f "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mysql/mysql-deployment.yaml" \
  -n "$NAMESPACE" --ignore-not-found

echo ">>> Remaining pods in namespace '$NAMESPACE':"
kubectl get pods -n "$NAMESPACE" || echo "Namespace may be gone."

echo ">>> If you want to delete the namespace completely, run:"
echo "    kubectl delete namespace $NAMESPACE"
