output "secret_ids" {
  description = "Map of secret names to their full resource IDs in Secret Manager"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.id }
}

output "secret_names" {
  description = "Map of secret names to their secret_id values for use in env var references"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}