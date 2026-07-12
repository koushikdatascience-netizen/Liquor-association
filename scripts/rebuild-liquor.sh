#!/usr/bin/env bash
# Rebuild/redeploy the WB Foreign Liquor and IML Licensees stack.
# SCOPED to docker-compose.liquor.yml (project: liquor-association).
# SocialSync containers (socialsync_*) are NEVER touched.
#
# Usage:
#   ./scripts/rebuild-liquor.sh            # low-downtime rebuild; keep old web live while building
#   ./scripts/rebuild-liquor.sh --clean    # low-downtime rebuild without Docker cache
#   ./scripts/rebuild-liquor.sh --wipe     # destructive clean rebuild; deletes DB + media volumes
set -euo pipefail

COMPOSE_FILE="docker-compose.liquor.yml"
MODE="${1:-}"

if [ "$MODE" = "--wipe" ]; then
  echo "==> WIPING liquor stack containers + volumes (SocialSync untouched)"
  docker compose -f "$COMPOSE_FILE" down -v

  echo "==> Removing old liquor image"
  docker image rm -f liquor-association-liquor_web:latest || true

  echo "==> Rebuilding from scratch (no cache)"
  docker compose -f "$COMPOSE_FILE" build --no-cache

  echo "==> Starting liquor stack"
  docker compose -f "$COMPOSE_FILE" up -d
elif [ "$MODE" = "--clean" ]; then
  echo "==> Building new liquor_web image without cache while current site stays live"
  docker compose -f "$COMPOSE_FILE" build --no-cache liquor_web

  echo "==> Switching liquor_web to the new image"
  docker compose -f "$COMPOSE_FILE" up -d --no-deps liquor_web
else
  echo "==> Building new liquor_web image with Docker cache while current site stays live"
  docker compose -f "$COMPOSE_FILE" build liquor_web

  echo "==> Switching liquor_web to the new image"
  docker compose -f "$COMPOSE_FILE" up -d --no-deps liquor_web
fi

echo "==> Liquor stack status"
docker compose -f "$COMPOSE_FILE" ps
docker ps --filter "name=liquor_"

echo "==> Verify new CSS is served"
docker compose -f "$COMPOSE_FILE" exec liquor_web \
  cat /app/static/wb/css/member.css | grep -i "blurred" || true

echo "==> Done. SocialSync containers still running:"
docker ps --filter "name=socialsync_" --format "{{.Names}}\t{{.Status}}"
