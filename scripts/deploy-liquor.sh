#!/usr/bin/env bash
# Pull latest code and cleanly rebuild the WB Foreign Liquor and IML Licensees stack.
# SCOPED to docker-compose.liquor.yml (project: liquor-association).
# SocialSync containers (socialsync_*) are NEVER touched.
#
# Usage:
#   ./scripts/deploy-liquor.sh            # keep DB + media volumes
#   ./scripts/deploy-liquor.sh --wipe     # also delete DB + media volumes
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

echo "==> Pulling latest changes"
git pull --ff-only origin master

echo "==> Rebuilding liquor stack"
bash scripts/rebuild-liquor.sh "${1:-}"