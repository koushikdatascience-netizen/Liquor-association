#!/usr/bin/env bash
# Pull latest code and redeploy the WB Foreign Liquor and IML Licensees stack.
# SCOPED to docker-compose.liquor.yml (project: liquor-association).
# SocialSync containers (socialsync_*) are NEVER touched.
#
# Usage:
#   ./scripts/deploy-liquor.sh            # low-downtime deploy; build first, switch last
#   ./scripts/deploy-liquor.sh --clean    # low-downtime deploy without Docker cache
#   ./scripts/deploy-liquor.sh --wipe     # destructive rebuild; deletes DB + media volumes
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

echo "==> Pulling latest changes"
git pull --ff-only origin master

echo "==> Deploying liquor stack"
bash scripts/rebuild-liquor.sh "${1:-}"
