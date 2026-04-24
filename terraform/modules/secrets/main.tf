variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "secrets" {
  description = "Secrets to create in Secret Manager"
  type = map(object({
    description      = string
    replication_type = string
  }))
  default = {}
}

# Secrets
resource "google_secret_manager_secret" "api_key" {
  for_each = var.secrets

  project = var.project_id
  secret_id = each.key

  replication {
    automatic = true
  }

  labels = {
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_version" "api_key_version" {
  for_each = var.secrets

  secret = google_secret_manager_secret.api_key[each.key].id

  secret_data = "placeholder-data-${each.key}"
}

# Secret IAM binding (example for extractor service)
resource "google_secret_manager_secret_iam_member" "extractor_access" {
  for_each = var.secrets

  project    = var.project_id
  secret_id  = google_secret_manager_secret.api_key[each.key].id
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:finna-extractor-sa@${var.project_id}.iam.gserviceaccount.com"
}

# Output
output "secret_names" {
  description = "List of secret names"
  value       = [for s in google_secret_manager_secret.api_key : s.secret_id]
}
