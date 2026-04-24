# TODO: Restore GCP Terraform deployment

## Changes

- Added Terraform module structure from scratch
- Implemented modules: network, database, registry, secrets, jobs, scheduler
- Created main.tf, variables.tf, and terraform.tfvars.example
- Added comprehensive documentation in terraform/README.md

## Resources Created

| Module | Resources |
|--------|-----------|
| network | VPC, Subnet, Router, NAT Gateway |
| database | Cloud SQL Instance, Database, User |
| registry | Artifact Registry (Docker) |
| secrets | Secret Manager (API keys, JWT, encryption) |
| jobs | Cloud Run Jobs (GCP, Azure, AWS extractors) |
| scheduler | Cloud Scheduler, Pub/Sub Topic |

## Next Steps

1. Update `provider "google"` block with correct project ID
2. Configure backend for remote state (GCS bucket)
3. Generate secure passwords for `terraform.tfvars`
4. Review and adjust IAM roles as needed
5. Integrate with existing Kubernetes deployment in `k8s/`
6. Update CI/CD pipeline to run `terraform apply` on merge

## Notes

- The Terraform module is separate from the existing Kubernetes manifests
- Consider consolidating infrastructure management (K8s vs Terraform) in the future
- All secrets should be managed through Secret Manager, not in terraform.tfvars
- Cloud SQL password is set to empty by default - use Secret Manager in production
