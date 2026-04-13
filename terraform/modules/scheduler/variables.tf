variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Scheduler jobs"
  type        = string
}

variable "gcp_billing_job_name" {
  description = "Name of the GCP Billing Cloud Run Job"
  type        = string
}

variable "azure_cost_job_name" {
  description = "Name of the Azure Cost Cloud Run Job"
  type        = string
}

variable "bifrost_llm_job_name" {
  description = "Name of the Bifrost LLM Cloud Run Job"
  type        = string
}

variable "exchange_rates_job_name" {
  description = "Name of the Exchange Rates Cloud Run Job"
  type        = string
}

variable "gcp_billing_schedule" {
  description = "Cron schedule for GCP Billing extractor (default: every 6 hours)"
  type        = string
  default     = "0 */6 * * *"
}

variable "azure_cost_schedule" {
  description = "Cron schedule for Azure Cost extractor (default: every 6 hours)"
  type        = string
  default     = "30 */6 * * *"
}

variable "bifrost_llm_schedule" {
  description = "Cron schedule for Bifrost LLM extractor (default: every hour)"
  type        = string
  default     = "0 * * * *"
}

variable "exchange_rates_schedule" {
  description = "Cron schedule for Exchange Rates extractor (default: every 24 hours)"
  type        = string
  default     = "0 6 * * *"
}