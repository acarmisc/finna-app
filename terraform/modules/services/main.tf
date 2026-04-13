# Service account for Cloud Run Services
resource "google_service_account" "services_sa" {
  account_id   = "${var.name}-services-sa"
  display_name = "FinOps Services Service Account"
}

# Grant minimal permissions
resource "google_project_iam_member" "services_sql_client" {
  role   = "roles/cloudsql.client"
  member = "serviceAccount:${google_service_account.services_sa.email}"
}

resource "google_project_iam_member" "services_secret_accessor" {
  role   = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${google_service_account.services_sa.email}"
}

resource "google_project_iam_member" "services_log_writer" {
  role   = "roles/logging.logWriter"
  member = "serviceAccount:${google_service_account.services_sa.email}"
}

resource "google_project_iam_member" "services_metric_writer" {
  role   = "roles/monitoring.metricWriter"
  member = "serviceAccount:${google_service_account.services_sa.email}"
}

resource "google_project_iam_member" "services_artifact_reader" {
  role   = "roles/artifactregistry.reader"
  member = "serviceAccount:${google_service_account.services_sa.email}"
}

# Cloud Run Service: Grafana
resource "google_cloud_run_v2_service" "grafana" {
  name     = "${var.name}-grafana"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.services_sa.email

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = var.grafana_min_instances
      max_instance_count = var.grafana_max_instances
    }

    containers {
      image = var.grafana_image
      port {
        container_port = 3000
      }

      env {
        name  = "GF_DATABASE_TYPE"
        value = "postgres"
      }

      env {
        name  = "GF_DATABASE_HOST"
        value = var.db_private_ip
      }

      env {
        name  = "GF_DATABASE_NAME"
        value = var.db_name
      }

      env {
        name  = "GF_DATABASE_USER"
        value = var.db_user
      }

      env {
        name  = "GF_DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.secret_names["grafana_db_password"]
            version = "latest"
          }
        }
      }

      env {
        name  = "GF_DATABASE_SSL_MODE"
        value = "disable"
      }

      env {
        name  = "GF_SECURITY_ADMIN_USER"
        value = "admin"
      }

      env {
        name  = "GF_SECURITY_ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.secret_names["grafana_admin_password"]
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.services_sql_client,
    google_project_iam_member.services_secret_accessor,
  ]
}

# Allow unauthenticated access to Grafana (adjust for production)
resource "google_cloud_run_v2_service_iam_member" "grafana_invoker" {
  project  = google_cloud_run_v2_service.grafana.project
  location = google_cloud_run_v2_service.grafana.location
  name     = google_cloud_run_v2_service.grafana.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Run Service: Bifrost
resource "google_cloud_run_v2_service" "bifrost" {
  name     = "${var.name}-bifrost"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.services_sa.email

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = var.bifrost_min_instances
      max_instance_count = var.bifrost_max_instances
    }

    containers {
      image = var.bifrost_image
      port {
        container_port = 8080
      }

      env {
        name  = "PG_DSN"
        value_source {
          secret_key_ref {
            secret  = var.secret_names["pg_dsn"]
            version = "latest"
          }
        }
      }

      env {
        name  = "BIFROST_API_KEYS"
        value_source {
          secret_key_ref {
            secret  = var.secret_names["bifrost_api_keys"]
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.services_sql_client,
    google_project_iam_member.services_secret_accessor,
  ]
}

# Allow unauthenticated access to Bifrost API
resource "google_cloud_run_v2_service_iam_member" "bifrost_invoker" {
  project  = google_cloud_run_v2_service.bifrost.project
  location = google_cloud_run_v2_service.bifrost.location
  name     = google_cloud_run_v2_service.bifrost.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}