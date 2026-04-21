# GCP Cost Optimization Audit — abs-digital-playground

## Executive Summary

| Category | Issue | Monthly Est. Waste |
|----------|-------|-------------------|
| Orphaned disks | 645GB unattached PDs | ~$13-26/mo |
| Snapshot bloat | 14 snapshots/disk, no retention | ~$30-50/mo |
| pd-ssd overuse | 2x 32GB pd-ssd (need pd-balanced) | ~$5/mo |
| Reserved IP unused | sftp-server-ip (no sftp-server instance) | ~$3.60/mo |
| No GCS lifecycle | No lifecycle policies on 6 buckets | TBD |
| Over-provisioned nodes | GKE spec: e2-standard-2, nodes: e2-standard-4 | ~$30/mo |

**Total estimated monthly waste: $80-120+/mo**

---

## 1. CRITICAL: Orphaned Disks (645GB total)

### europe-west1-b — 243GB orphaned

| Disk | Size | Type | Age | Notes |
|------|------|------|-----|-------|
| `gke-abs-ces-n8n-workload-pool-01-f8f07e0d-6g7p` | 100GB | pd-balanced | Apr 2026 | GKE node disk, node deleted but disk remains |
| `unica-nfs` | 30GB | pd-balanced | Mar 2026 | NFS server disk |
| `unica-superset` | 40GB | pd-balanced | Apr 2026 | Superset server disk |
| `pvc-d14c1473` | 40GB | pd-balanced | Feb 2026 | PVC from deleted pod |
| `pvc-8eca889b` | 8GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-a4334a1a` | 8GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-c85b87dd` | 8GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-f762b37d` | 5GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-35702984` | 2GB | pd-balanced | Feb 2026 | Orphaned PVC |
| `pvc-07633d48` | 1GB | pd-balanced | **Jun 2025** | ⚠️ 10 months old! |
| `pvc-5a1455e7` | 1GB | pd-standard | Apr 2026 | Orphaned PVC |

### europe-west1-c — 172GB orphaned

| Disk | Size | Type | Age | Notes |
|------|------|------|-----|-------|
| `bf-dashboard-data` | 60GB | pd-balanced | Sep 2025 | ⚠️ 7 months old |
| `disk-20251029-173520` | 40GB | pd-balanced | Oct 2025 | ⚠️ 6 months old |
| `pvc-0fe8e82e` | 32GB | **pd-ssd** | Mar 2026 | ⚠️ Most expensive type! |
| `pvc-737f04a4` | 32GB | **pd-ssd** | Mar 2026 | ⚠️ Most expensive type! |
| `pvc-273dde04` | 8GB | pd-balanced | Mar 2026 | Orphaned PVC |

### europe-west1-d — 230GB orphaned

| Disk | Size | Type | Age | Notes |
|------|------|------|-----|-------|
| `ces-vm-appscan-01-data` | 100GB | pd-balanced | Feb 2026 | ⚠️ 2+ months old |
| `disk-20250923-073419` | 100GB | pd-balanced | Sep 2025 | ⚠️ 7 months old |
| `pvc-c4dd2771` | 10GB | pd-balanced | Oct 2025 | ⚠️ 6 months old |
| `pvc-acc21167` | 10GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-fffd101a` | 8GB | pd-balanced | Mar 2026 | Orphaned PVC |
| `pvc-fc849650` | 2GB | pd-balanced | Jan 2026 | ⚠️ 3+ months old |

---

## 2. CRITICAL: Snapshot Bloat

### Current state
- **14 snapshots per disk** with **zero retention policy**
- **43+ snapshots older than 7 days** (should be max 3-7)
- Snapshot storage growing daily for disks that may be deleted

### Snapshots by source disk

| Source Disk | Snapshots | Age Range | Disk Size | Est. Snapshot Storage |
|-------------|-----------|-----------|-----------|----------------------|
| `disk-20250923-073419` | 14 | Apr 7-20, 2026 | 100GB | ~100GB |
| `sftp-server` | 14 | (deleted instance) | — | ~wasted |
| `disk-20251029-173520` | 14 | (old disk) | 40GB | ~40GB |
| `bf-dashboard-data` | 14 | Daily (Apr 7-20) | 60GB | ~60GB |
| `unica-nfs` | 14 | (running) | 30GB | ~30GB |
| `ces-vm-appscan-01` | 4 | Feb 6-9, 2026 | 100GB | ~400GB |
| `abs-ces-n8n-01` | 1 | Jun 2025 | 20GB | ~20GB |

### Recommendation
- Set retention to **max 7 days** for daily snapshots
- Delete snapshots for **deleted instances** (sftp-server, old disks)
- Configure **snapshot schedule with retention** going forward

---

## 3. HIGH: Over-Provisioned GKE Nodes

### Mismatch detected
| Setting | Value |
|---------|-------|
| Cluster spec (`machineType`) | `e2-standard-2` (2 vCPU, 8GB) |
| Actual node pools | `e2-standard-4` (4 vCPU, 16GB) |

**3x over-provisioned** — each node is 2x the specified machine type.

### Affected nodes (3 running)
| Node | Zone | Machine | vCPU | RAM |
|------|------|---------|------|-----|
| `gke-abs-ces-n8n-workload-pool-01-...6g7p` | europe-west1-b | e2-standard-4 | 4 | 16GB |
| `gke-abs-ces-n8n-workload-pool-01-...hdrk` | europe-west1-c | e2-standard-4 | 4 | 16GB |
| `gke-abs-ces-n8n-workload-pool-01-...6z5r` | europe-west1-d | e2-standard-4 | 4 | 16GB |

**Total**: 12 vCPU, 48GB RAM — could be 6 vCPU, 24GB (e2-standard-2)

---

## 4. MEDIUM: pd-ssd Overuse

| Disk | Size | Current Type | Recommended | Savings |
|------|------|-------------|-------------|---------|
| `pvc-0fe8e82e` | 32GB | pd-ssd ($0.17/GB) | pd-balanced ($0.10/GB) | ~$2.24/mo |
| `pvc-737f04a4` | 32GB | pd-ssd ($0.17/GB) | pd-balanced ($0.10/GB) | ~$2.24/mo |

**Only use pd-ssd if IOPS/throughput is proven necessary.**

---

## 5. MEDIUM: Unused Reserved IP

| Name | IP | Status | Issue |
|------|-----|--------|-------|
| `sftp-server-ip` | (reserved) | RESERVED | No `sftp-server` instance exists |

**Cost**: ~$3.60/mo per static IP. Delete if not needed.

---

## 6. LOW: No GCS Lifecycle Policies

| Bucket | Size | Lifecycle? | Recommendation |
|--------|------|------------|---------------|
| `abs-ces-storage` | 0 B | ❌ | N/A (empty) |
| `abs-digital-playground-bifrost-config` | 941 B | ❌ | N/A (tiny) |
| `ces-dev-storage-01` | **30.33 GB** | ❌ | Add lifecycle: transition to Coldline after 30 days |
| `qa-testflow-artifacts-prod` | 5.16 MB | ❌ | Add lifecycle: delete after 90 days |
| `run-sources-abs-digital-playground-europe-west1` | — | ❌ | Review contents |
| `run-sources-abs-digital-playground-us-central1` | — | ❌ | Review contents |

---

## 7. LOW: No Committed Use Discounts / Sustained Use

- No evidence of **Committed Use Discounts (CUDs)** for steady workloads
- **Sustained Use Discounts** are automatic for Compute Engine but not optimized
- No **Savings Plans** or **Reservations** configured

---

## Priority Action Plan

### 🔴 Immediate (do this week)
1. **Delete orphaned snapshots** for deleted instances:
   ```bash
   gcloud compute snapshots delete $(gcloud compute snapshots list --filter="sourceDisk:sftp-server" --format="value(name)" --project=abs-digital-playground)
   gcloud compute snapshots delete $(gcloud compute snapshots list --filter="sourceDisk:disk-20251029" --format="value(name)" --project=abs-digital-playground)
   ```
2. **Delete confirmed orphaned disks** (after verifying no data needed):
   ```bash
   gcloud compute disks delete pvc-07633d48 pvc-8eca889b pvc-a4334a1a pvc-c85b87dd pvc-f762b37d pvc-35702984 pvc-5a1455e7 pvc-273dde04 pvc-acc21167 pvc-fffd101a pvc-fc849650 --zone=europe-west1-b --zone=europe-west1-c --zone=europe-west1-d
   ```
3. **Delete unused reserved IP**:
   ```bash
   gcloud compute addresses delete sftp-server-ip --region=europe-west1
   ```

### 🟡 This sprint
4. **Set snapshot retention policies** (max 7 days)
5. **Downsize GKE nodes** from e2-standard-4 to e2-standard-2
6. **Convert pd-ssd to pd-balanced** where IOPS not critical
7. **Add GCS lifecycle policies** to buckets with data

### 🟢 Next sprint
8. **Evaluate committed use discounts** for steady workloads
9. **Implement disk tagging** for cost allocation
10. **Set up budget alerts**

---

## Estimated Savings

| Action | Monthly Savings |
|--------|----------------|
| Delete orphaned disks (645GB) | $13-26 |
| Snapshot retention (remove ~80%) | $25-40 |
| pd-ssd → pd-balanced | $4.50 |
| Delete unused reserved IP | $3.60 |
| GKE node right-sizing (e2-4 → e2-2) | ~$30 |
| **Total estimated** | **$75-125/mo** |
