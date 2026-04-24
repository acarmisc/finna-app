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
}

variable "subnet_name" {
  description = "Subnetwork Name"
  type        = string
}

variable "service_account" {
  description = "Service account email for Cloud Run Jobs"
  type        = string
}

# Pub/Sub Topic for Job Triggers
resource "google_pubsub_topic" "extractor_jobs" {
  project = var.project_id
  name    = "finna-extractor-jobs"
}

# Cloud Run Job for GCP Extractor
resource "google_cloud_run_v2_job" "gcp_extractor" {
  project     = var.project_id
  name        = "gcp-extractor-job"
  location    = var.region

  template {
    execution_namespace = var.project_id
    max_retries       = 3
    timeout           = "3600s"

    template {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project_id}/finna/gcp-extractor:latest"
        resources {
          limits = {
            memory = "2Gi"
            cpu    = "1"
          }
        }
        env = [
          {
            name  = "PROJECT_ID"
            value = var.project_id
          }
        ]
      }
      service_account = var.service_account

      deployment_revision = "latest"
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Cloud Run Job for Azure Extractor
resource "google_cloud_run_v2_job" "azure_extractor" {
  project     = var.project_id
  name        = "azure-extractor-job"
  location    = var.region

  template {
    execution_namespace = var.project_id
    max_retries       = 3
    timeout           = "3600s"

    template {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project_id}/finna/azure-extractor:latest"
        resources {
          limits = {
            memory = "2Gi"
            cpu    = "1"
          }
        }
        env = [
          {
            name  = "TENANT_ID"
            value_from {
              secret_key_ref {
                name = "finna-azure-tenant"
                key  = "tenant_id"
              }
            }
          }
        ]
      }
      service_account = var.service_account
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Cloud Run Job for AWS Extractor
resource "google_cloud_run_v2_job" "aws_extractor" {
  project     = var.project_id
  name        = "aws-extractor-job"
  location    = var.region

  template {
    execution_namespace = var.project_id
    max_retries       = 3
    timeout           = "3600s"

    template {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project_id}/finna/aws-extractor:latest"
        resources {
          limits = {
            memory = "2Gi"
            cpu    = "1"
          }
        }
        env = [
          {
            name  = "AWS_REGION"
            value = var.region
          }
        ]
      }
      service_account = var.service_account
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Output
output "gcp_job_name" {
  description = "GCP Extractor Job name"
  value       = google_cloud_run_v2_job.gcp_extractor.name
}

output "azure_job_name" {
  description = "Azure Extractor Job name"
  value       = google_cloud_run_v2_job.azure_extractor.name
}

output "aws_job_name" {
  description = "AWS Extractor Job name"
  value       = google_cloud_run_v2_job.aws_extractor.name
}

output "topic_name" {
  description = "Pub/Sub topic name"
  value       = google_pubsub_topic.extractor_jobs.name
}
