output "instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "connection_name" {
  description = "Connection name for Cloud SQL (project:region:instance)"
  value       = google_sql_database_instance.postgres.connection_name
}

output "private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "database_name" {
  description = "Name of the application database"
  value       = google_sql_database.finops.name
}

output "user_name" {
  description = "Username of the application database user"
  value       = google_sql_user.app_user.name
}

output "instance_self_link" {
  description = "Self-link of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.self_link
}