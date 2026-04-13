variable "name" {
  description = "Prefix for all resources in this module"
  type        = string
}

variable "region" {
  description = "GCP region for the VPC and subnets"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR range for the primary subnet"
  type        = string
  default     = "10.8.0.0/20"
}