variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run Jobs"
  type        = string
}

variable "extractor_image" {
  description = "Docker image for the extractor jobs"
  type        = string
}

variable "vpc_connector_id" {
  description = "ID of the VPC connector for private Cloud SQL access"
  type        = string
}

variable "secret_names" {
  description = "Map of secret keys to their Secret Manager secret_id values"
  type        = map(string)
}