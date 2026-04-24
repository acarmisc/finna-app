variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "repository" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "finna"
}

# Artifact Registry Repository
resource "google_artifact_registry_repository" "main" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository
  description   = "Docker repository for FinOps platform"
  format        = "DOCKER"

  labels = {
    environment = "production"
    managed_by  = "terraform"
  }
}

# Output
output "repository_name" {
  description = "Repository name"
  value       = google_artifact_registry_repository.main.name
}

output "endpoint" {
  description = "Registry endpoint"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository}"
}
