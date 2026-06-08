#!/usr/bin/env bash
# Copy master-key from litellm/litellm-secrets into finna-app-staging/litellm-master-key.
# Idempotent. Re-run after rotation.

set -euo pipefail

SRC_NS="litellm"
SRC_SECRET="litellm-secrets"
SRC_KEY="master-key"

DST_NS="finna-app-staging"
DST_SECRET="litellm-master-key"
DST_KEY="master-key"

key=$(kubectl -n "$SRC_NS" get secret "$SRC_SECRET" -o jsonpath="{.data.${SRC_KEY}}" | base64 -d)
if [[ -z "$key" ]]; then
  echo "ERROR: empty master-key from ${SRC_NS}/${SRC_SECRET}" >&2
  exit 1
fi

kubectl -n "$DST_NS" create secret generic "$DST_SECRET" \
  --from-literal="${DST_KEY}=${key}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "synced ${SRC_NS}/${SRC_SECRET}.${SRC_KEY} -> ${DST_NS}/${DST_SECRET}.${DST_KEY}"
