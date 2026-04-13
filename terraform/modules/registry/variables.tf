variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "region" {
  description = "GCP region for the Artifact Registry repository"
  type        = string
}