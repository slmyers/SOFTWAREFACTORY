#!/usr/bin/env bash
# scripts/playwright-mcp.sh — Launch or stop the Playwright MCP server
# Issue #49: Playwright MCP Browser Automation Server
#
# Usage:
#   ./scripts/playwright-mcp.sh           # start (default)
#   ./scripts/playwright-mcp.sh --stop    # stop and remove container
#   ./scripts/playwright-mcp.sh --status  # show health / URL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"
SERVICE="playwright-mcp"
DEFAULT_URL="http://localhost:3000"

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Prerequisite check
# ---------------------------------------------------------------------------
check_prereqs() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed."
        exit 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Start service
# ---------------------------------------------------------------------------
start_service() {
    log_info "Starting $SERVICE …"
    docker compose -f "$COMPOSE_FILE" up -d "$SERVICE"

    # Wait for health check
    log_info "Waiting for $SERVICE to be healthy …"
    local max=30 attempt=1
    while [ $attempt -le $max ]; do
        local cid
        cid=$(docker compose -f "$COMPOSE_FILE" ps -q "$SERVICE" 2>/dev/null || true)
        if [ -n "$cid" ] && docker inspect --format='{{.State.Health.Status}}' \
               "$cid" 2>/dev/null | grep -q "healthy"; then
            break
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    echo ""

    if [ $attempt -gt $max ]; then
        log_warn "$SERVICE did not become healthy within $((max * 2)) seconds."
        log_warn "Check logs: docker compose -f $COMPOSE_FILE logs $SERVICE"
    else
        log_info "$SERVICE is ready at ${MCP_SERVER_PLAYWRIGHT_MCP:-$DEFAULT_URL}"
    fi

    echo ""
    echo "======================================================"
    echo " Playwright MCP Server"
    echo "======================================================"
    echo " URL : ${MCP_SERVER_PLAYWRIGHT_MCP:-$DEFAULT_URL}"
    echo " Env : set MCP_SERVER_PLAYWRIGHT_MCP to override"
    echo " Logs: docker compose -f $COMPOSE_FILE logs -f $SERVICE"
    echo "======================================================"
}

# ---------------------------------------------------------------------------
# Stop service
# ---------------------------------------------------------------------------
stop_service() {
    log_info "Stopping $SERVICE …"
    docker compose -f "$COMPOSE_FILE" stop "$SERVICE"
    docker compose -f "$COMPOSE_FILE" rm -f "$SERVICE"
    log_info "$SERVICE stopped."
}

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
show_status() {
    local cid
    cid=$(docker compose -f "$COMPOSE_FILE" ps -q "$SERVICE" 2>/dev/null || true)
    local status="not running"
    if [ -n "$cid" ]; then
        status=$(docker inspect --format='{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")
    fi
    log_info "$SERVICE status: $status"
    if [ "$status" = "running" ]; then
        log_info "URL: ${MCP_SERVER_PLAYWRIGHT_MCP:-$DEFAULT_URL}"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
check_prereqs

case "${1:-}" in
    --stop)   stop_service ;;
    --status) show_status  ;;
    *)        start_service ;;
esac
