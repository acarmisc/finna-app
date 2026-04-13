output "service_account_email" {
  description = "Email of the extractor service account"
  value       = google_service_account.extractor_sa.email
}

output "gcp_billing_job_name" {
  description = "Name of the GCP Billing extractor Cloud Run Job"
  value       = google_cloud_run_v2_job.gcp_billing.name
}

output "azure_cost_job_name" {
  description = "Name of the Azure Cost extractor Cloud Run Job"
  value       = google_cloud_run_v2_job.azure_cost.name
}

output "bifrost_llm_job_name" {
  description = "Name of the Bifrost LLM extractor Cloud Run Job"
  value       = google_cloud_run_v2_job.bifrost_llm.name
}

output "exchange_rates_job_name" {
  description = "Name of the Exchange Rates extractor Cloud Run Job"
  value       = google_cloud_run_v2_job.exchange_rates.name
}

output "gcp_billing_job_id" {
  description = "ID of the GCP Billing Cloud Run Job for scheduler targeting"
  value       = google_cloud_run_v2_job.gcp_billing.id
}

output "azure_cost_job_id" {
  description = "ID of the Azure Cost Cloud Run Job for scheduler targeting"
  value       = google_cloud_run_v2_job.azure_cost.id
}

output "bifrost_llm_job_id" {
  description = "ID of the Bifrost LLM Cloud Run Job for scheduler targeting"
  value       = google_cloud_run_v2_job.bifrost_llm.id
}

output "exchange_rates_job_id" {
  description = "ID of the Exchange Rates Cloud Run Job for scheduler targeting"
  value       = google_cloud_run_v2_job.exchange_rates.id
}