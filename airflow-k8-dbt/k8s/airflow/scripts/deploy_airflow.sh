#!/usr/bin/env bash
set -euo pipefail

# Config
NAMESPACE="airflow"
RELEASE_NAME="airflow"
HELM_REPO_NAME="apache-airflow"
HELM_REPO_URL="https://airflow.apache.org"
VALUES_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/helm/values-mysql.yaml"
MYSQL_MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mysql/mysql-deployment.yaml"

echo ">>> Using namespace: $NAMESPACE"
echo ">>> Using Helm values: $VALUES_FILE"
echo ">>> Using MySQL manifest: $MYSQL_MANIFEST"

# 1. Namespace (idempotent)
echo ">>> Creating namespace (if not exists)..."
kubectl get ns "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"

# 2. Apply MySQL deployment
echo ">>> Applying MySQL deployment..."
kubectl apply -f "$MYSQL_MANIFEST"

echo ">>> Waiting for MySQL pod to be ready..."
kubectl wait --namespace "$NAMESPACE" \
  --for=condition=ready pod \
  -l app=airflow-mysql \
  --timeout=120s

# 3. Helm repo setup
echo ">>> Adding/updating Helm repo $HELM_REPO_NAME..."
helm repo add "$HELM_REPO_NAME" "$HELM_REPO_URL" >/dev/null 2>&1 || true
helm repo update "$HELM_REPO_NAME"

# 4. Install / upgrade Airflow
echo ">>> Installing / upgrading Airflow release '$RELEASE_NAME'..."
helm upgrade --install "$RELEASE_NAME" "$HELM_REPO_NAME/airflow" \
  --namespace "$NAMESPACE" \
  -f "$VALUES_FILE" \
  --create-namespace \
  --debug

# 5. Wait for webserver + scheduler + worker to be ready-ish
echo ">>> Waiting for core Airflow components to become ready..."

kubectl wait --namespace "$NAMESPACE" \
  --for=condition=ready pod \
  -l component=scheduler \
  --timeout=300s || echo "Scheduler readiness wait timed out (check pods manually)"

kubectl wait --namespace "$NAMESPACE" \
  --for=condition=ready pod \
  -l component=webserver \
  --timeout=300s || echo "Webserver readiness wait timed out (check pods manually)"

kubectl wait --namespace "$NAMESPACE" \
  --for=condition=ready pod \
  -l component=worker \
  --timeout=300s || echo "Worker readiness wait timed out (check pods manually)"

echo ">>> Current pods in namespace '$NAMESPACE':"
kubectl get pods -n "$NAMESPACE"

echo ">>> Done. Use port_forward_webserver.sh to open the UI."
