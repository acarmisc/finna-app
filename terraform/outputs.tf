# ---- Database ----

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name (project:region:instance)"
  value       = module.database.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = module.database.private_ip
}

output "database_name" {
  description = "Application database name"
  value       = module.database.database_name
}

# ---- Services ----

output "grafana_url" {
  description = "URL of the Grafana Cloud Run service"
  value       = module.services.grafana_url
}

output "bifrost_url" {
  description = "URL of the Bifrost Cloud Run service"
  value       = module.services.bifrost_url
}

# ---- Registry ----

output "artifact_registry_url" {
  description = "URL of the Artifact Registry Docker repository"
  value       = module.registry.repository_url
}

# ---- Service Accounts ----

output "extractor_service_account_email" {
  description = "Email of the extractor Cloud Run Jobs service account"
  value       = module.jobs.service_account_email
}

output "services_service_account_email" {
  description = "Email of the Cloud Run Services service account"
  value       = module.services.service_account_email
}

output "scheduler_service_account_email" {
  description = "Email of the Cloud Scheduler service account"
  value       = module.scheduler.service_account_email
}

# ---- VPC ----

output "vpc_connector_id" {
  description = "ID of the VPC connector used by Cloud Run"
  value       = module.network.vpc_connector_id
}

# ---- Scheduler ----

output "scheduler_jobs" {
  description = "Names of all Cloud Scheduler jobs"
  value = {
    gcp_billing    = module.scheduler.gcp_billing_schedule_name
    azure_cost     = module.scheduler.azure_cost_schedule_name
    bifrost_llm    = module.scheduler.bifrost_llm_schedule_name
    exchange_rates = module.scheduler.exchange_rates_schedule_name
  }
}