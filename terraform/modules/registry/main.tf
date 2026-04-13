resource "google_artifact_registry_repository" "docker" {
  location   = var.region
  repository = "${var.name}-docker"
  format     = "DOCKER"

  cleanup_policies {
    id     = "keep-minimum"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "259200s" # 3 days
    }
  }
}