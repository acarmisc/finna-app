variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "region" {
  description = "GCP region for the Cloud SQL instance"
  type        = string
}

variable "db_tier" {
  description = "Machine tier for the Cloud SQL instance (e.g. db-f1-micro, db-custom-2-7680)"
  type        = string
  default     = "db-f1-micro"
}

variable "availability_type" {
  description = "Availability type: REGIONAL for HA, ZONAL for dev"
  type        = string
  default     = "ZONAL"
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Name of the application database"
  type        = string
  default     = "finops"
}

variable "db_user" {
  description = "Username for the application database user"
  type        = string
  default     = "finops_app"
}

variable "db_password" {
  description = "Password for the application database user"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "Self-link of the VPC for private IP"
  type        = string
}

variable "private_service_connection" {
  description = "Reference to the private service connection dependency"
  type        = string
}