#!/usr/bin/env bash
# Rebuild the WB Foreign Liquor and IML Licensees stack cleanly.
# SCOPED to docker-compose.liquor.yml (project: liquor-association).
# SocialSync containers (socialsync_*) are NEVER touched.
#
# Usage:
#   ./scripts/rebuild-liquor.sh            # keep DB + media volumes
#   ./scripts/rebuild-liquor.sh --wipe     # also delete DB + media volumes
set -euo pipefail

COMPOSE_FILE="docker-compose.liquor.yml"
WIPE="${1:-}"

echo "==> Stopping & removing liquor containers/network (SocialSync untouched)"
docker compose -f "$COMPOSE_FILE" down ${WIPE:+ -v}

echo "==> Removing old liquor image (only the liquor_web image)"
docker image rm -f liquor-association-liquor_web:latest || true

echo "==> Rebuilding from scratch (no cache)"
docker compose -f "$COMPOSE_FILE" build --no-cache

echo "==> Starting liquor stack"
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Liquor stack status"
docker compose -f "$COMPOSE_FILE" ps
docker ps --filter "name=liquor_"

echo "==> Verify new CSS is served"
docker compose -f "$COMPOSE_FILE" exec liquor_web \
  cat /app/static/wb/css/member.css | grep -i "blurred" || true

echo "==> Done. SocialSync containers still running:"
docker ps --filter "name=socialsync_" --format "{{.Names}}\t{{.Status}}"