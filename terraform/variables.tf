variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "VPC Network Name"
  type        = string
  default     = "finna-network"
}

variable "database_name" {
  description = "Cloud SQL Database Name"
  type        = string
  default     = "finops"
}

variable "database_user" {
  description = "Cloud SQL Database User"
  type        = string
  default     = "finops"
}

variable "database_password" {
  description = "Cloud SQL Database Password (use secrets in production)"
  type        = string
  sensitive   = true
}

variable "registry_repository" {
  description = "Artifact Registry Repository Name"
  type        = string
  default     = "finna"
}

variable "secrets" {
  description = "Secrets to create in Secret Manager"
  type = map(object({
    description = string
    replication_type = string
  }))
  default = {
    "api-key" = {
      description      = "API Key for FinOps platform"
      replication_type = "automatic"
    }
    "jwt-secret" = {
      description      = "JWT Secret for authentication"
      replication_type = "automatic"
    }
    "encryption-key" = {
      description      = "Encryption key for sensitive data"
      replication_type = "automatic"
    }
  }
}

variable "extractor_iam_roles" {
  description = "IAM roles for extractor service account"
  type        = list(string)
  default = [
    "roles/bigquery.dataViewer",
    "roles/storage.objectViewer",
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/logging.viewer",
  ]
}

variable "scheduler_topic_id" {
  description = "Pub/Sub topic ID for scheduler"
  type        = string
  default     = "finna-scheduler"
}
