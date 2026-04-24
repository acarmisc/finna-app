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
  description = "Cloud SQL Database Password"
  type        = string
  sensitive   = true
  default     = ""
}

local{
  database_id = "finops-sql-instance"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  project = var.project_id
  name    = local.database_id
  region  = var.region
  database_version = "POSTGRES_16"

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = true
      private_network = "projects/${var.project_id}/global/networks/${var.network_name}"
    }

    backup_configuration {
      enabled = true
      startTime = "02:00"
    }

    maintenance_window {
      day  = 7
      hour = 3
    }
  }

  deletion_protection = false
}

# Cloud SQL Database
resource "google_sql_database" "finops" {
  project  = var.project_id
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

# Cloud SQL User
resource "google_sql_user" "finops" {
  project  = var.project_id
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = var.database_password
}

# Output
output "connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.name
}

output "instance_name" {
  description = "Instance name"
  value       = google_sql_database_instance.main.name
}
