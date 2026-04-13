output "service_account_email" {
  description = "Email of the services service account"
  value       = google_service_account.services_sa.email
}

output "grafana_url" {
  description = "URL of the Grafana Cloud Run Service"
  value       = google_cloud_run_v2_service.grafana.uri
}

output "bifrost_url" {
  description = "URL of the Bifrost Cloud Run Service"
  value       = google_cloud_run_v2_service.bifrost.uri
}

output "grafana_service_name" {
  description = "Name of the Grafana Cloud Run Service"
  value       = google_cloud_run_v2_service.grafana.name
}

output "bifrost_service_name" {
  description = "Name of the Bifrost Cloud Run Service"
  value       = google_cloud_run_v2_service.bifrost.name
}