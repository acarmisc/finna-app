# ---- Project Configuration ----

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP zone for zonal resources"
  type        = string
  default     = "europe-west1-b"
}

variable "name" {
  description = "Prefix for all resources (use short, lowercase, hyphen-separated name)"
  type        = string
  default     = "finops"
}

# ---- Network ----

variable "subnet_cidr" {
  description = "CIDR range for the primary VPC subnet"
  type        = string
  default     = "10.8.0.0/20"
}

# ---- Database ----

variable "db_tier" {
  description = "Cloud SQL machine tier (db-f1-micro for dev, db-custom-2-7680 for prod)"
  type        = string
  default     = "db-f1-micro"
}

variable "availability_type" {
  description = "Cloud SQL availability type: ZONAL for dev, REGIONAL for prod HA"
  type        = string
  default     = "ZONAL"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Application database name"
  type        = string
  default     = "finops"
}

variable "db_user" {
  description = "Application database username"
  type        = string
  default     = "finops_app"
}

variable "db_password" {
  description = "Application database password"
  type        = string
  sensitive   = true
}

# ---- Images ----

variable "grafana_image" {
  description = "Docker image for Grafana Cloud Run service"
  type        = string
}

variable "extractor_image" {
  description = "Docker image for all extractor Cloud Run jobs"
  type        = string
}

# ---- Secret Values (initial) ----

variable "pg_dsn_value" {
  description = "PostgreSQL DSN connection string for extractors"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gcp_sa_key_value" {
  description = "GCP service account key JSON for billing extraction"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_credentials_value" {
  description = "Azure credentials JSON for cost extraction"
  type        = string
  sensitive   = true
  default     = ""
}

variable "bifrost_api_keys_value" {
  description = "Bifrost API keys JSON"
  type        = string
  sensitive   = true
  default     = ""
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = ""
}

# ---- Service Scaling ----

variable "grafana_min_instances" {
  description = "Minimum number of Grafana instances"
  type        = number
  default     = 1
}

variable "grafana_max_instances" {
  description = "Maximum number of Grafana instances"
  type        = number
  default     = 3
}

# ---- Schedules ----

variable "gcp_billing_schedule" {
  description = "Cron schedule for GCP Billing extractor (default every 6 hours)"
  type        = string
  default     = "0 */6 * * *"
}

variable "azure_cost_schedule" {
  description = "Cron schedule for Azure Cost extractor (default every 6 hours, offset 30 min)"
  type        = string
  default     = "30 */6 * * *"
}

variable "bifrost_llm_schedule" {
  description = "Cron schedule for Bifrost LLM extractor (default every hour)"
  type        = string
  default     = "0 * * * *"
}

variable "exchange_rates_schedule" {
  description = "Cron schedule for Exchange Rates extractor (default every 24 hours)"
  type        = string
  default     = "0 6 * * *"
}

# ---- Alerts ----

variable "alert_email" {
  description = "Email address for alerting notifications"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerting notifications"
  type        = string
  sensitive   = true
  default     = ""
}