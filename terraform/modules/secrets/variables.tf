variable "secrets" {
  description = "Map of secret names to their initial values (null/empty to skip version creation)"
  type        = map(string)
  default     = {}
}