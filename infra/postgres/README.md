# Local Postgres Development Infrastructure

This directory contains Terraform configuration to spin up a local PostgreSQL database using Docker for development purposes.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0.0
- [Docker](https://docs.docker.com/get-docker/) running locally

## Quick Start

```bash
# From repo root, use the helper script:
./scripts/dev-db-up.sh

# Or manually:
cd infra/postgres
terraform init
terraform apply -auto-approve
```

## Outputs

After `terraform apply`, the following outputs are available:

| Output | Description |
|--------|-------------|
| `database_url` | Async connection URL (for asyncpg driver) |
| `database_url_sync` | Sync connection URL (for Alembic/psycopg2) |
| `database_url_test` | Async connection URL for the test database (asyncpg) |
| `database_url_test_sync` | Sync connection URL for the test database (psycopg2) |
| `container_name` | Docker container name |
| `postgres_host` | Database host (localhost) |
| `postgres_port` | Database port (default: 5432) |

To view outputs:
```bash
terraform output database_url
```

## Configuration

Default values (override via `terraform.tfvars`):

| Variable | Default | Description |
|----------|---------|-------------|
| `postgres_user` | `softwarefactory` | Database user |
| `postgres_password` | `devpassword` | Database password |
| `postgres_db` | `softwarefactory_dev` | Database name |
| `postgres_port` | `5432` | Host port |

## Usage with Alembic

After starting the database:

```bash
# Set DATABASE_URL for Alembic (from repo root)
export DATABASE_URL=$(cd infra/postgres && terraform output -raw database_url_sync)

# Run migrations
alembic upgrade head
```

## Teardown

```bash
cd infra/postgres
terraform destroy -auto-approve
```

This removes the container but preserves the Docker volume. To remove the volume:
```bash
docker volume rm softwarefactory_postgres_data
```

## Troubleshooting

**Container not starting:**
```bash
docker logs softwarefactory_postgres
```

**Port already in use:**
Override the port via `terraform.tfvars`:
```hcl
postgres_port = 5433
```

**Reset database:**
```bash
docker stop softwarefactory_postgres
docker rm softwarefactory_postgres
docker volume rm softwarefactory_postgres_data
terraform apply -auto-approve
```
