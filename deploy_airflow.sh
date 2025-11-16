#!/usr/bin/env bash
set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ Missing $1"; return 1; }; }

need kubectl || { echo "Install kubectl first (e.g., 'brew install kubectl')"; exit 1; }
need helm    || { echo "Install helm first (e.g., 'brew install helm')"; exit 1; }

NAMESPACE="airflow"

echo "🚀 Creating namespace: ${NAMESPACE}"
kubectl create namespace "${NAMESPACE}" 2>/dev/null || echo "✅ Namespace already exists."

echo "📦 Adding Apache Airflow Helm repo..."
helm repo add apache-airflow https://airflow.apache.org || true
helm repo update

# NOTE:
# - We use KubernetesExecutor -> no Celery workers section in this chart.
# - statsd.enabled is valid; workers.enabled is NOT for this executor.
# - You can pin a chart version if you want with: --version 1.18.0
echo "⚙️  Installing / Upgrading Airflow in namespace ${NAMESPACE}..."
helm upgrade --install airflow apache-airflow/airflow -n "${NAMESPACE}" \
  --set executor=KubernetesExecutor \
  --set web.resources.limits.cpu=500m \
  --set web.resources.limits.memory=1Gi \
  --set statsd.enabled=false \
  --wait

echo "✅ Airflow deployed!"
echo "-------------------------------------------------------------------"
echo "Pods:"
echo "  kubectl get pods -n ${NAMESPACE}"
echo ""
echo "Port-forward UI:"
echo "  kubectl -n ${NAMESPACE} port-forward svc/airflow-webserver 8080:8080"
echo "Open: http://localhost:8080"
echo "-------------------------------------------------------------------"
