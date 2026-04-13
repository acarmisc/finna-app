output "vpc_id" {
  description = "Self-link of the VPC network"
  value       = google_compute_network.vpc.id
}

output "vpc_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "Self-link of the subnet"
  value       = google_compute_subnetwork.subnet.id
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "vpc_connector_id" {
  description = "ID of the serverless VPC connector"
  value       = google_vpc_access_connector.serverless_connector.id
}

output "private_service_connection" {
  description = "Whether the private service connection has been established"
  value       = google_service_networking_connection.private_service_connection.state
}