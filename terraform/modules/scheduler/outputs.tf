output "service_account_email" {
  description = "Email of the scheduler service account"
  value       = google_service_account.scheduler_sa.email
}

output "gcp_billing_schedule_name" {
  description = "Name of the GCP Billing scheduler job"
  value       = google_cloud_scheduler_job.gcp_billing.name
}

output "azure_cost_schedule_name" {
  description = "Name of the Azure Cost scheduler job"
  value       = google_cloud_scheduler_job.azure_cost.name
}

output "bifrost_llm_schedule_name" {
  description = "Name of the Bifrost LLM scheduler job"
  value       = google_cloud_scheduler_job.bifrost_llm.name
}

output "exchange_rates_schedule_name" {
  description = "Name of the Exchange Rates scheduler job"
  value       = google_cloud_scheduler_job.exchange_rates.name
}