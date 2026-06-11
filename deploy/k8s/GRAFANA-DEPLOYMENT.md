# Grafana Deployment for FinOps

This document describes how to deploy a lightweight Grafana instance to monitor FinOps data in your GKE cluster.

## Overview

Grafana provides visualization for all finna-app data:
- **Cost monitoring** (GCP, Azure, LLM)
- **Alerts & budgets**
- **Resource wastage**
- **Extractor health**

## Prerequisites

- GKE cluster access
- kubectl configured
- finna-app PostgreSQL database running in `finna-app` namespace

## Deployment

### Quick Deploy (Single Command)

```bash
./deploy-grafana.sh --namespace=finna-app --cluster=<cluster-name>
```

### Manual Deployment Steps

1. **Set up cluster context:**
   ```bash
   gcloud container clusters get-credentials <cluster-name> --region europe-west1
   kubectl config use-context <context-name>
   ```

2. **Apply the deployment:**
   ```bash
   kubectl apply -f deploy/k8s/grafana-deployment.yaml
   ```

3. **Verify installation:**
   ```bash
   kubectl -n finna-app get pods
   kubectl -n finna-app svc grafana
   ```

4. **Port-forward to access:**
   ```bash
   kubectl -n finna-app port-forward service/grafana 3000:3000
   ```

## Configuration

### Environment Variables

The deployment uses these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GF_SECURITY_ADMIN_USER` | Grafana admin username | `admin` |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password | auto-generated |
| `GF_DATABASE_TYPE` | Database type | `postgres` |
| `GF_DATABASE_HOST` | PostgreSQL host | `postgres.finna-app-staging.svc.cluster.local` |
| `GF_DATABASE_NAME` | Database name | `finops` |
| `GF_DATABASE_USER` | Database user | `finops` |
| `GF_DATABASE_PASSWORD` | Database password (from secret) | - |

### Customizing Configuration

Edit `grafana-deployment.yaml` to modify:
- Password (from `grafana-secret`)
- Database connection settings
- Resource limits
- Ingress configuration

## Access

### Local Access (Port-forward)

```bash
kubectl -n finna-app port-forward service/grafana 3000:3000
```

Then open: http://localhost:3000

### Cluster-Internal Access

Grafana is accessible within the cluster at:
```
http://grafana.finna-app.svc.cluster.local:3000
```

## Post-Deployment Setup

### 1. Configure Data Source

1. Login to Grafana (admin/secret password)
2. Go to **Settings** → **Data Sources** → **Add data source**
3. Select **PostgreSQL**
4. Configure:
    - Host: `postgres.finna-app.svc.cluster.local:5432`
   - Database: `finops`
   - User: `finops`
   - Password: (from finops-secret)

### 2. Import Dashboards

**Option A: Via Grafana UI**
- Go to **Dashboards** → **Import**
- Upload `grafana/*.json` files

**Option B: Via API**
```bash
for dashboard in grafana/*.json; do
  curl -X POST http://localhost:3000/api/dashboard/import \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d @($dashboard | jq -c '{dashboard: ., overwrite: true}')
done
```

**Option C: Using the Import Script**
```bash
cd grafana
./import-dashboards.sh http://localhost:3000 <api-token>
```

## Monitoring Tips

### Access Logs

```bash
kubectl -n finna-app logs -l app.kubernetes.io/name=grafana
```

### Check Health

```bash
kubectl -n finna-app get deployments
kubectl -n finna-app get services
```

### Reset Password

```bash
kubectl -n finna-app delete secret grafana-secret
kubectl -n finna-app create secret generic grafana-secret \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=<new-password>
```

## Cost Estimation

- **Pod resources**: 100m CPU / 128Mi memory (min), 250m CPU / 256Mi memory (max)
- **Storage**: ~200MB for dashboards/configs
- **Monthly cost**: ~$10-15 (GCP standard pricing)

## Troubleshooting

### Pod Not Starting

```bash
kubectl -n finna-app describe pod <pod-name>
kubectl -n finna-app logs <pod-name>
```

### Database Connection Issues

Verify PostgreSQL service exists:
```bash
kubectl -n finna-app get svc postgres
```

Check database credentials:
```bash
kubectl -n finna-app get secret finops-secret -o yaml
```

### Dashboard Import Issues

Check Grafana logs for import errors:
```bash
kubectl -n finna-app logs -l app.kubernetes.io/name=grafana | grep -i dashboard
```

## Maintenance

### Update Grafana Version

Edit `deploy/k8s/grafana-deployment.yaml`:
```yaml
image: grafana/grafana:11.2.0  # or latest
```

### Backup Dashboards

```bash
kubectl -n finna-app get configmap grafana-dashboards -o yaml > grafana-dashboards-backup.yaml
```

### Scale Up/Down

```bash
kubectl -n finna-app scale deployment grafana --replicas=<N>
```

## Clean Up

```bash
kubectl delete namespace grafana
```

## Files

- `deploy/k8s/grafana-deployment.yaml` - Kubernetes manifests
- `deploy/k8s/deploy-grafana.sh` - Automated deployment script
- `grafana/*.json` - Dashboard definitions
- `grafana/import-dashboards.sh` - Dashboard import script

## Support

For issues:
1. Check Grafana logs
2. Verify PostgreSQL connectivity
3. Review kubectl events: `kubectl -n finna-app get events`
