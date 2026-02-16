# Output the DATABASE_URL for use by the application
# Issue #5: AgentState + checkpointing

output "database_url" {
  description = "PostgreSQL connection URL for async SQLAlchemy (asyncpg driver)"
  value       = "postgresql+asyncpg://${var.postgres_user}:${var.postgres_password}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive   = true
}

output "database_url_sync" {
  description = "PostgreSQL connection URL for sync tools (psycopg2/alembic)"
  value       = "postgresql://${var.postgres_user}:${var.postgres_password}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive   = true
}

output "database_url_test" {
  description = "Async connection URL for the test database (asyncpg)"
  value       = "postgresql+asyncpg://${var.postgres_test_user}:${var.postgres_test_password}@localhost:${var.postgres_port}/${var.postgres_test_db}"
  sensitive   = true
}

output "database_url_test_sync" {
  description = "Sync connection URL for the test database (psycopg2)"
  value       = "postgresql://${var.postgres_test_user}:${var.postgres_test_password}@localhost:${var.postgres_port}/${var.postgres_test_db}"
  sensitive   = true
}

output "container_name" {
  description = "Name of the running Postgres container"
  value       = docker_container.postgres.name
}

output "postgres_host" {
  description = "Postgres host"
  value       = "localhost"
}

output "postgres_port" {
  description = "Postgres port"
  value       = var.postgres_port
}
