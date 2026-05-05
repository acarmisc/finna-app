# Terraform Configuration for FinOps Platform

## Quick Start

```bash
# Initialize
terraform init

# Plan
terraform plan -var="project_id=your-gcp-project-id" \
               -var="region=us-central1" \
               -var="database_password=your-secure-password"

# Apply
terraform apply -var="project_id=your-gcp-project-id" \
                -var="region=us-central1" \
                -var="database_password=your-secure-password"

# Destroy (careful!)
terraform destroy
```

## Required Variables

| Variable | Description |
|----------|-------------|
| `project_id` | GCP project ID |
| `region` | Deployment region |
| `database_password` | PostgreSQL password |
