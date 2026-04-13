# Service account for Cloud Scheduler to invoke Cloud Run Jobs
resource "google_service_account" "scheduler_sa" {
  account_id   = "${var.name}-scheduler-sa"
  display_name = "FinOps Scheduler Service Account"
}

# Grant Cloud Run invoker permission
resource "google_cloud_run_v2_job_iam_member" "gcp_billing_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.gcp_billing_job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_cloud_run_v2_job_iam_member" "azure_cost_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.azure_cost_job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_cloud_run_v2_job_iam_member" "bifrost_llm_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.bifrost_llm_job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_cloud_run_v2_job_iam_member" "exchange_rates_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.exchange_rates_job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# Cloud Scheduler: GCP Billing - every 6 hours
resource "google_cloud_scheduler_job" "gcp_billing" {
  name             = "${var.name}-gcp-billing-schedule"
  region           = var.region
  description      = "Trigger GCP Billing extractor every 6 hours"
  schedule         = var.gcp_billing_schedule
  time_zone        = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.gcp_billing_job_name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.gcp_billing_invoker]
}

# Cloud Scheduler: Azure Cost - every 6 hours
resource "google_cloud_scheduler_job" "azure_cost" {
  name             = "${var.name}-azure-cost-schedule"
  region           = var.region
  description      = "Trigger Azure Cost extractor every 6 hours"
  schedule         = var.azure_cost_schedule
  time_zone        = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.azure_cost_job_name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.azure_cost_invoker]
}

# Cloud Scheduler: Bifrost LLM - every 1 hour
resource "google_cloud_scheduler_job" "bifrost_llm" {
  name             = "${var.name}-bifrost-llm-schedule"
  region           = var.region
  description      = "Trigger Bifrost LLM extractor every hour"
  schedule         = var.bifrost_llm_schedule
  time_zone        = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.bifrost_llm_job_name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.bifrost_llm_invoker]
}

# Cloud Scheduler: Exchange Rates - every 24 hours
resource "google_cloud_scheduler_job" "exchange_rates" {
  name             = "${var.name}-exchange-rates-schedule"
  region           = var.region
  description      = "Trigger Exchange Rates extractor every 24 hours"
  schedule         = var.exchange_rates_schedule
  time_zone        = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.exchange_rates_job_name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.exchange_rates_invoker]
}