# TODO: Restore GCP Terraform deployment

This is a placeholder for issue #1.

## Implementation Plan

1. Recovery original `terraform/` from git history (commit dd3b081 or 5325cbf)
2. Remove Grafana Cloud Run service
3. Add `roles/bigquery.dataViewer` to extractor SA
4. Fix Azure credentials to use 4 separate env vars
5. Update to external Superset architecture
6. Add `terraform.tfvars.example` for deployment guide

## Files to restore

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── terraform.tfvars.example
└── modules/
    ├── database/
    ├── jobs/
    ├── network/
    ├── registry/
    ├── scheduler/
    └── secrets/
```

## Notes

- The Terraform was removed to reduce scope
- Grafana has been replaced by Superset (external)
- Need to handle Azure credentials mismatch (JSON vs separate env vars)
- Terraform should only manage: VPC, Cloud SQL, Artifact Registry, Secrets, Cloud Run Jobs (extractors), Cloud Scheduler, and IAM
