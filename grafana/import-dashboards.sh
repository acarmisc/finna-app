#!/bin/bash
# Import FinOps dashboards into Grafana
# Usage: ./import-dashboards.sh <grafana-url> <username> <password>
# Or: ./import-dashboards.sh <grafana-url> <base64-auth-token>

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <grafana-url> <api-key or username:password>"
    echo "Example: $0 http://localhost:3000 admin:Grafana2026!"
    exit 1
fi

GRAFANA_URL="$1"
AUTH="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="${SCRIPT_DIR}"

# Validate URL
if [[ ! "$GRAFANA_URL" =~ ^https?:// ]]; then
    echo "Error: Invalid URL format (must start with http:// or https://)"
    exit 1
fi

# Check if dashboards exist
shopt -s nullglob
dashboards=("$DASHBOARD_DIR"/*.json)
shopt -u nullglob

if [[ ${#dashboards[@]} -eq 0 ]]; then
    echo "Error: No JSON dashboard files found in $DASHBOARD_DIR"
    exit 1
fi

echo "Importing dashboards to ${GRAFANA_URL}..."
echo "Found ${#dashboards[@]} dashboard(s) to import"
echo

imported=0
failed=0

for dashboard_file in "${dashboards[@]}"; do
    dashboard_name=$(basename "$dashboard_file" .json)
    
    # Read and validate JSON
    if ! jq . "$dashboard_file" > /dev/null 2>&1; then
        echo "✗ $dashboard_name: Invalid JSON"
        ((failed++))
        continue
    fi
    
    # Create import payload (files may already be in wrapped {dashboard, overwrite} format)
    if jq -e '.dashboard' "$dashboard_file" > /dev/null 2>&1; then
        payload=$(jq -c '.message = "Imported from finna-app Grafana dashboards"' "$dashboard_file")
    else
        payload=$(jq -c '{
            dashboard: .,
            overwrite: true,
            message: "Imported from finna-app Grafana dashboards"
        }' "$dashboard_file")
    fi
    
    # Make API call with basic auth support
    # Note: Grafana 13+ uses /api/dashboards/db, not /api/dashboard/import
    if [[ "$AUTH" == *":"* ]]; then
        # Basic auth (username:password)
        response=$(curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
            -u "$AUTH" \
            -H "Content-Type: application/json" \
            -d "$payload")
    else
        # Bearer token
        response=$(curl -s -X POST "${GRAFANA_URL}/api/dashboards/db" \
            -H "Authorization: Bearer ${AUTH}" \
            -H "Content-Type: application/json" \
            -d "$payload")
    fi
    
    # Check response
    import_status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "error")
    
    if [[ "$import_status" == "success" ]]; then
        echo "✓ Imported: $dashboard_name"
        ((imported++))
    else
        error_msg=$(echo "$response" | jq -r '.message // "Unknown error"' 2>/dev/null || echo "$response")
        echo "✗ Failed: $dashboard_name - $error_msg"
        ((failed++))
    fi
done

echo
echo "==================================="
echo "Summary: ${imported} imported, ${failed} failed"
echo "==================================="

if [[ $failed -gt 0 ]]; then
    exit 1
fi
