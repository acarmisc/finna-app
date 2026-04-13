variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run Services"
  type        = string
}

variable "grafana_image" {
  description = "Docker image for Grafana"
  type        = string
}

variable "bifrost_image" {
  description = "Docker image for Bifrost"
  type        = string
}

variable "vpc_connector_id" {
  description = "ID of the VPC connector for private Cloud SQL access"
  type        = string
}

variable "db_private_ip" {
  description = "Private IP of the Cloud SQL instance"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_user" {
  description = "Database username"
  type        = string
}

variable "secret_names" {
  description = "Map of secret keys to their Secret Manager secret_id values"
  type        = map(string)
}

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

variable "bifrost_min_instances" {
  description = "Minimum number of Bifrost instances"
  type        = number
  default     = 1
}

variable "bifrost_max_instances" {
  description = "Maximum number of Bifrost instances"
  type        = number
  default     = 5
}