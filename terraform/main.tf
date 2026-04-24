# FinOps Multi-cloud Cost Platform - GCP Infrastructure
# Main Terraform configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "finna-terraform-state"
    prefix = "state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ──────────────────────────────────────────────────────────────────────────────
# Resources
# ──────────────────────────────────────────────────────────────────────────────

# VPC Network
module "network" {
  source = "./modules/network"

  project_id = var.project_id
  region     = var.region
  network_name = var.network_name
}

# Cloud SQL (PostgreSQL)
module "database" {
  source = "./modules/database"

  project_id     = var.project_id
  region         = var.region
  network_name   = module.network.network_name
  database_name  = var.database_name
  database_user  = var.database_user
  database_password = var.database_password
}

# Artifact Registry (Docker)
module "registry" {
  source = "./modules/registry"

  project_id = var.project_id
  region     = var.region
  repository = var.registry_repository
}

# Secret Manager
module "secrets" {
  source = "./modules/secrets"

  project_id = var.project_id
  secrets    = var.secrets
}

# Cloud Run Jobs (Extractors)
module "jobs" {
  source = "./modules/jobs"

  project_id       = var.project_id
  region           = var.region
  network_name     = module.network.network_name
  subnet_name      = module.network.subnet_name
  service_account  = google_service_account.extractor_services.email
}

# Cloud Scheduler (Cron jobs)
module "scheduler" {
  source = "./modules/scheduler"

  project_id    = var.project_id
  region        = var.region
  topic_id      = var.scheduler_topic_id
  topic_region  = var.region
}

# ──────────────────────────────────────────────────────────────────────────────
# Service Accounts
# ──────────────────────────────────────────────────────────────────────────────

resource "google_service_account" "extractor_services" {
  project      = var.project_id
  account_id   = "finna-extractor-sa"
  display_name = "FinOps Extractor Service Account"
}

resource "google_project_iam_member" "extractor_service_account_roles" {
  count = length(var.extractor_iam_roles)

  project = var.project_id
  role    = var.extractor_iam_roles[count.index]
  member  = "serviceAccount:${google_service_account.extractor_services.email}"
}

# ──────────────────────────────────────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────────────────────────────────────

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.database.connection_name
}

output "service_account_email" {
  description = "Extractor service account email"
  value       = google_service_account.extractor_services.email
}

output "network_name" {
  description = "VPC network name"
  value       = module.network.network_name
}
