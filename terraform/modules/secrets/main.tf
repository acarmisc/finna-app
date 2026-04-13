resource "google_secret_manager_secret" "secrets" {
  for_each = var.secrets

  secret_id = each.key

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "versions" {
  for_each = { for k, v in var.secrets : k => v if v != null && v != "" }

  secret_id   = google_secret_manager_secret.secrets[each.key].id
  secret_data = each.value
  enabled     = true
}