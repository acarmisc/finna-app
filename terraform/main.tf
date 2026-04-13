terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# ---- Network ----

module "network" {
  source = "./modules/network"

  name        = var.name
  region      = var.region
  subnet_cidr = var.subnet_cidr

  depends_on = [google_project_service.apis]
}

# ---- Database ----

module "database" {
  source = "./modules/database"

  name                     = var.name
  region                   = var.region
  db_tier                  = var.db_tier
  availability_type        = var.availability_type
  disk_size                = var.db_disk_size
  db_name                  = var.db_name
  db_user                  = var.db_user
  db_password              = var.db_password
  vpc_id                   = module.network.vpc_id
  private_service_connection = module.network.private_service_connection

  depends_on = [module.network, google_project_service.apis]
}

# ---- Artifact Registry ----

module "registry" {
  source = "./modules/registry"

  name   = var.name
  region = var.region

  depends_on = [google_project_service.apis]
}

# ---- Secrets ----

module "secrets" {
  source = "./modules/secrets"

  secrets = {
    pg_dsn               = var.pg_dsn_value
    gcp_sa_key           = var.gcp_sa_key_value
    azure_credentials    = var.azure_credentials_value
    bifrost_api_keys     = var.bifrost_api_keys_value
    aws_credentials      = ""  # Future: placeholder
    grafana_db_password  = var.db_password
    grafana_admin_password = var.grafana_admin_password
  }

  depends_on = [google_project_service.apis]
}

# ---- Cloud Run Jobs (Extractors) ----

module "jobs" {
  source = "./modules/jobs"

  name            = var.name
  region          = var.region
  extractor_image = var.extractor_image
  vpc_connector_id = module.network.vpc_connector_id
  secret_names    = module.secrets.secret_names

  depends_on = [module.network, module.secrets, google_project_service.apis]
}

# ---- Cloud Run Services ----

module "services" {
  source = "./modules/services"

  name              = var.name
  region            = var.region
  grafana_image     = var.grafana_image
  vpc_connector_id  = module.network.vpc_connector_id
  db_private_ip     = module.database.private_ip
  db_name           = module.database.database_name
  db_user           = module.database.user_name
  secret_names      = module.secrets.secret_names
  grafana_min_instances = var.grafana_min_instances
  grafana_max_instances = var.grafana_max_instances

  depends_on = [module.network, module.database, module.secrets, google_project_service.apis]
}

# ---- Cloud Scheduler ----

module "scheduler" {
  source = "./modules/scheduler"

  name                    = var.name
  project_id              = var.project_id
  region                  = var.region
  gcp_billing_job_name    = module.jobs.gcp_billing_job_name
  azure_cost_job_name     = module.jobs.azure_cost_job_name
  bifrost_llm_job_name    = module.jobs.bifrost_llm_job_name
  exchange_rates_job_name = module.jobs.exchange_rates_job_name
  gcp_billing_schedule    = var.gcp_billing_schedule
  azure_cost_schedule     = var.azure_cost_schedule
  bifrost_llm_schedule    = var.bifrost_llm_schedule
  exchange_rates_schedule = var.exchange_rates_schedule

  depends_on = [module.jobs, google_project_service.apis]
}