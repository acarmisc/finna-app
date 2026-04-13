# Service account for Cloud Run Jobs
resource "google_service_account" "extractor_sa" {
  account_id   = "${var.name}-extractor-sa"
  display_name = "FinOps Extractor Service Account"
}

# Grant minimal permissions to the extractor service account
resource "google_project_iam_member" "extractor_sql_client" {
  role   = "roles/cloudsql.client"
  member = "serviceAccount:${google_service_account.extractor_sa.email}"
}

resource "google_project_iam_member" "extractor_secret_accessor" {
  role   = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${google_service_account.extractor_sa.email}"
}

resource "google_project_iam_member" "extractor_log_writer" {
  role   = "roles/logging.logWriter"
  member = "serviceAccount:${google_service_account.extractor_sa.email}"
}

resource "google_project_iam_member" "extractor_metric_writer" {
  role   = "roles/monitoring.metricWriter"
  member = "serviceAccount:${google_service_account.extractor_sa.email}"
}

resource "google_project_iam_member" "extractor_artifact_reader" {
  role   = "roles/artifactregistry.reader"
  member = "serviceAccount:${google_service_account.extractor_sa.email}"
}

# Cloud Run Job: GCP Billing Extractor
resource "google_cloud_run_v2_job" "gcp_billing" {
  name     = "${var.name}-gcp-billing-extractor"
  location = var.region

  template {
    template {
      service_account = google_service_account.extractor_sa.email
      vpc_access {
        connector = var.vpc_connector_id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image = "${var.extractor_image}"
        command = ["python", "-m", "extractors.gcp_billing"]

        env {
          name  = "PG_DSN"
          value_source {
            secret_key_ref {
              secret = var.secret_names["pg_dsn"]
              version = "latest"
            }
          }
        }

        env {
          name  = "GCP_SA_KEY"
          value_source {
            secret_key_ref {
              secret = var.secret_names["gcp_sa_key"]
              version = "latest"
            }
          }
        }

        env {
          name  = "EXTRACTOR_SCHEDULE"
          value = "6h"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        max_retries = 2
      }

      timeout = "600s"
      task_count = 1
    }
  }

  depends_on = [
    google_project_iam_member.extractor_sql_client,
    google_project_iam_member.extractor_secret_accessor,
  ]
}

# Cloud Run Job: Azure Cost Extractor
resource "google_cloud_run_v2_job" "azure_cost" {
  name     = "${var.name}-azure-cost-extractor"
  location = var.region

  template {
    template {
      service_account = google_service_account.extractor_sa.email
      vpc_access {
        connector = var.vpc_connector_id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image = "${var.extractor_image}"
        command = ["python", "-m", "extractors.azure_cost"]

        env {
          name  = "PG_DSN"
          value_source {
            secret_key_ref {
              secret = var.secret_names["pg_dsn"]
              version = "latest"
            }
          }
        }

        env {
          name  = "AZURE_CREDENTIALS"
          value_source {
            secret_key_ref {
              secret = var.secret_names["azure_credentials"]
              version = "latest"
            }
          }
        }

        env {
          name  = "EXTRACTOR_SCHEDULE"
          value = "6h"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        max_retries = 2
      }

      timeout = "600s"
      task_count = 1
    }
  }

  depends_on = [
    google_project_iam_member.extractor_sql_client,
    google_project_iam_member.extractor_secret_accessor,
  ]
}

# Cloud Run Job: Bifrost LLM Extractor
resource "google_cloud_run_v2_job" "bifrost_llm" {
  name     = "${var.name}-bifrost-llm-extractor"
  location = var.region

  template {
    template {
      service_account = google_service_account.extractor_sa.email
      vpc_access {
        connector = var.vpc_connector_id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image = "${var.extractor_image}"
        command = ["python", "-m", "extractors.bifrost_llm"]

        env {
          name  = "PG_DSN"
          value_source {
            secret_key_ref {
              secret = var.secret_names["pg_dsn"]
              version = "latest"
            }
          }
        }

        env {
          name  = "BIFROST_API_KEYS"
          value_source {
            secret_key_ref {
              secret = var.secret_names["bifrost_api_keys"]
              version = "latest"
            }
          }
        }

        env {
          name  = "EXTRACTOR_SCHEDULE"
          value = "1h"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }

        max_retries = 3
      }

      timeout = "300s"
      task_count = 1
    }
  }

  depends_on = [
    google_project_iam_member.extractor_sql_client,
    google_project_iam_member.extractor_secret_accessor,
  ]
}

# Cloud Run Job: Exchange Rates Extractor
resource "google_cloud_run_v2_job" "exchange_rates" {
  name     = "${var.name}-exchange-rates-extractor"
  location = var.region

  template {
    template {
      service_account = google_service_account.extractor_sa.email
      vpc_access {
        connector = var.vpc_connector_id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image = "${var.extractor_image}"
        command = ["python", "-m", "extractors.exchange_rates"]

        env {
          name  = "PG_DSN"
          value_source {
            secret_key_ref {
              secret = var.secret_names["pg_dsn"]
              version = "latest"
            }
          }
        }

        env {
          name  = "EXTRACTOR_SCHEDULE"
          value = "24h"
        }

        resources {
          limits = {
            cpu    = "0.5"
            memory = "256Mi"
          }
        }

        max_retries = 2
      }

      timeout = "300s"
      task_count = 1
    }
  }

  depends_on = [
    google_project_iam_member.extractor_sql_client,
    google_project_iam_member.extractor_secret_accessor,
  ]
}