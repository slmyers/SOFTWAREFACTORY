# Terraform config for local Postgres development (Docker-based)
# Issue #5: AgentState + checkpointing

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
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
