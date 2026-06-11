#!/bin/bash
# Deploy Grafana to GKE cluster with finna-app data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRAFANA_DIR="${SCRIPT_DIR}/grafana"

# Default values
NAMESPACE="${NAMESPACE:-finna-app}"
CLUSTER_NAME="${CLUSTER_NAME:-gke_abs-digital-playground_europe-west1_abs-ces-n8n}"
CONTEXT_NAME="${CONTEXT_NAME:-grafana}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${YELLOW}>> $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

echo_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace=*)
            NAMESPACE="${1#*=}"
            shift
            ;;
        --cluster=*)
            CLUSTER_NAME="${1#*=}"
            shift
            ;;
        --context=*)
            CONTEXT_NAME="${1#*=}"
            shift
            ;;
        *)
            echo "Usage: $0 [--namespace=ns] [--cluster=name] [--context=name]"
            exit 1
            ;;
    esac
done

echo "Deploying Grafana to cluster: ${CLUSTER_NAME}"
echo "Namespace: ${NAMESPACE}"
echo

# Step 1: Set up cluster context
echo_step "Setting up cluster context..."
gcloud container clusters get-credentials "$CLUSTER_NAME" --region europe-west1 --project elc-cdpacc-prj-dev-387709

# Step 2: Create namespace if it doesn't exist (skip if already created)
echo_step "Creating namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace ${NAMESPACE} app.kubernetes.io/name=grafana 2>/dev/null || true

# Step 3: Create Grafana deployment
echo_step "Deploying Grafana..."
kubectl apply -n ${NAMESPACE} -f "$GRAFANA_DIR/grafana-deployment.yaml"

# Step 4: Wait for deployment to be ready
echo_step "Waiting for Grafana deployment to be ready..."
kubectl -n ${NAMESPACE} wait deployment/grafana --for=condition=Available --timeout=300s
echo_success "Grafana deployment is ready"

# Step 5: Port-forward to localhost
echo_step "Port-forwarding Grafana to localhost:3000..."
kubectl -n ${NAMESPACE} port-forward service/grafana 3000:3000 &

# Wait a moment for port-forward to establish
sleep 3

# Check if Grafana is accessible
if curl -s http://localhost:3000/api/health | grep -q "ok"; then
    echo_success "Grafana is accessible at http://localhost:3000"
else
    echo_error "Failed to connect to Grafana"
fi

# Get admin credentials
echo
echo "=========================================="
echo "Grafana is running!"
echo "=========================================="
echo "URL: http://localhost:3000"
echo "Username: admin"
echo "Password: (stored in secret grafana-secret in namespace ${NAMESPACE})"
echo
echo "To view the password:"
echo "  kubectl -n ${NAMESPACE} get secret grafana-secret -o jsonpath='{.data.admin-password}' | base64 -d"
echo
echo "To access Grafana in your browser:"
echo "  open http://localhost:3000"
echo
echo "To stop port-forwarding, press Ctrl+C"
echo "=========================================="

# Keep port-forward running
wait
