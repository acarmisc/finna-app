# ──────────────────────────────────────────────────────────────────────────────
# VPC Network Module
# ──────────────────────────────────────────────────────────────────────────────

resource "google_compute_network" "main" {
  project = var.project_id
  name    = var.network_name

  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  project       = var.project_id
  name          = "${var.network_name}-subnet"
  region        = var.region
  network       = google_compute_network.main.name
  ip_cidr_range = "10.0.0.0/24"
}

resource "google_compute_router" "main" {
  project = var.project_id
  name    = "${var.network_name}-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  project               = var.project_id
  name                  = "${var.network_name}-nat"
  router                = google_compute_router.main.name
  region                = var.region
  nat_ip_allocate_option = "AUTO_ONLY"

  source_subnetwork_network_interfaces {
    network = google_compute_network.main.self_link
  }
}

# Output
output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.main.name
}

output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.main.id
}

output "subnet_name" {
  description = "Subnetwork name"
  value       = google_compute_subnetwork.main.name
}

output "subnet_id" {
  description = "Subnetwork ID"
  value       = google_compute_subnetwork.main.id
}
