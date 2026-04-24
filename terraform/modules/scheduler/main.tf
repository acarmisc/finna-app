variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "topic_id" {
  description = "Pub/Sub topic ID"
  type        = string
  default     = "finna-scheduler"
}

# Pub/Sub Topic
resource "google_pubsub_topic" "scheduler" {
  project = var.project_id
  name    = var.topic_id
}

# Scheduled Job: Daily Cost Extraction
resource "google_scheduler_job" "daily_cost_extraction" {
  project  = var.project_id
  name     = "daily-cost-extraction"
  region   = var.region
  schedule  = "0 6 * * *"  # Every day at 6:00 AM
  time_zone = "UTC"

  http_target {
    uri         = "https://finna-api.example.com/api/v1/costs/extract"
    http_method = "POST"
    body        = base64encode(jsonencode({
      providers = ["gcp", "azure", "aws", "llm"]
    }))
    headers = {
      "Content-Type" = "application/json"
    }
  }

  retry_config {
    retry_count = 3
  }
}

# Scheduled Job: Weekly Report
resource "google_scheduler_job" "weekly_report" {
  project  = var.project_id
  name     = "weekly-report"
  region   = var.region
  schedule  = "0 9 * * 1"  # Every Monday at 9:00 AM
  time_zone = "UTC"

  http_target {
    uri         = "https://finna-api.example.com/api/v1/reports/weekly"
    http_method = "POST"
  }

  retry_config {
    retry_count = 3
  }
}

# Output
output "topic_name" {
  description = "Scheduler Pub/Sub topic name"
  value       = google_pubsub_topic.scheduler.name
}

output "daily_job_name" {
  description = "Daily extraction job name"
  value       = google_scheduler_job.daily_cost_extraction.name
}

output "weekly_job_name" {
  description = "Weekly report job name"
  value       = google_scheduler_job.weekly_report.name
}
