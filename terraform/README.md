# ──────────────────────────────────────────────────────────────────────────────
# Terraform Configuration for FinOps Platform
# ──────────────────────────────────────────────────────────────────────────────

# Initialize Terraform
terraform init

# Apply with variables
terraform apply \
  -var="project_id=your-gcp-project-id" \
  -var="region=us-central1" \
  -var="database_password=generate-a-secure-password"

# Destroy (careful!)
terraform destroy
