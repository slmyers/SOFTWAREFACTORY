# Terraform config for local Postgres development (Docker-based)
# Issue #5: AgentState + checkpointing

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# Variables
variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "softwarefactory"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  default     = "devpassword"
  sensitive   = true
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "softwarefactory_dev"
}

variable "postgres_port" {
  description = "Host port to expose PostgreSQL"
  type        = number
  default     = 5432
}

# Optional test-database/user created after the container starts. These
# are used by CI/dev tests and mirror the `.env.test` entry.
variable "postgres_test_user" {
  description = "Optional test DB username"
  type        = string
  default     = "softwarefactorytest"
}

variable "postgres_test_password" {
  description = "Optional test DB password"
  type        = string
  default     = "testpassword"
  sensitive   = true
}

variable "postgres_test_db" {
  description = "Optional test database name"
  type        = string
  default     = "softwarefactory_test"
}

# After the Postgres container is up, create the test role and DB if they
# do not already exist. This runs a small `docker exec` idempotent script.
resource "null_resource" "create_test_db" {
  depends_on = [docker_container.postgres]

  triggers = {
    container = docker_container.postgres.id
    test_user = var.postgres_test_user
    test_db   = var.postgres_test_db
  }

  provisioner "local-exec" {
    command = <<EOT
# wait for Postgres to be ready
until docker exec softwarefactory_postgres pg_isready -U ${var.postgres_user} -d ${var.postgres_db}; do sleep 1; done

# create test role if missing
docker exec softwarefactory_postgres bash -lc "psql -U ${var.postgres_user} -d ${var.postgres_db} -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${var.postgres_test_user}'\" | grep -q 1 || psql -U ${var.postgres_user} -d ${var.postgres_db} -c \"CREATE ROLE ${var.postgres_test_user} LOGIN PASSWORD '${var.postgres_test_password}';\""

# create test database if missing and set owner
docker exec softwarefactory_postgres bash -lc "psql -U ${var.postgres_user} -d ${var.postgres_db} -tAc \"SELECT 1 FROM pg_database WHERE datname='${var.postgres_test_db}'\" | grep -q 1 || psql -U ${var.postgres_user} -d ${var.postgres_db} -c \"CREATE DATABASE ${var.postgres_test_db} OWNER ${var.postgres_test_user};\""
EOT
  }
}

# Pull the official Postgres image
resource "docker_image" "postgres" {
  name         = "postgres:15-alpine"
  keep_locally = true
}

# Create a Docker volume for data persistence
resource "docker_volume" "postgres_data" {
  name = "softwarefactory_postgres_data"
}

# Run the Postgres container
resource "docker_container" "postgres" {
  name  = "softwarefactory_postgres"
  image = docker_image.postgres.image_id

  ports {
    internal = 5432
    external = var.postgres_port
  }

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}",
  ]

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.postgres_user} -d ${var.postgres_db}"]
    interval = "5s"
    timeout  = "5s"
    retries  = 5
  }

  restart = "unless-stopped"
}
