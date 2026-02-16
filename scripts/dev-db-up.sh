#!/usr/bin/env bash
# Development database startup script
# Issue #5: AgentState + checkpointing
#
# Usage: ./scripts/dev-db-up.sh [--destroy]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra/postgres"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prereqs() {
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
}

# Destroy database
destroy_db() {
    log_info "Destroying development database..."
    cd "$INFRA_DIR"
    terraform destroy -auto-approve
    log_info "Database destroyed."
}

# Start database
start_db() {
    log_info "Starting development database..."
    cd "$INFRA_DIR"

    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        log_info "Initializing Terraform..."
        terraform init
    fi

    # Apply configuration
    log_info "Applying Terraform configuration..."
    terraform apply -auto-approve

    # Wait for container to be healthy
    log_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker exec softwarefactory_postgres pg_isready -U softwarefactory -d softwarefactory_dev &> /dev/null; then
            break
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""

    if [ $attempt -gt $max_attempts ]; then
        log_error "PostgreSQL failed to start within ${max_attempts} seconds"
        exit 1
    fi

    log_info "PostgreSQL is ready!"

    # Print connection info
    echo ""
    echo "=========================================="
    echo "Development Database Ready"
    echo "=========================================="
    echo ""
    echo "Async DATABASE_URL (for app):"
    terraform output -raw database_url
    echo ""
    echo ""
    echo "Sync DATABASE_URL (for Alembic):"
    terraform output -raw database_url_sync
    echo ""
    echo ""
    echo "To run migrations:"
    echo "  export DATABASE_URL=\$(cd infra/postgres && terraform output -raw database_url_sync)"
    echo "  alembic upgrade head"
    echo ""
}

# Main
main() {
    check_prereqs

    if [ "${1:-}" = "--destroy" ]; then
        destroy_db
    else
        start_db
    fi
}

main "$@"
