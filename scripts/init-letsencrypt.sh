#!/bin/bash
# Obtain Let's Encrypt certificates for the Liquor Association domains.
# Run once after the stack is up:  docker compose -f docker-compose.liquor.yml exec liquor_web true && ./scripts/init-letsencrypt.sh
set -e

DOMAINS="wbliquorsocity.com,admin.wbliquorsocity.com,member.wbliquorsocity.com"
EMAIL="${LETSENCRYPT_EMAIL:-admin@wbliquorsocity.com}"
STAGING=${LETSENCRYPT_STAGING:-0}

echo ">>> Creating dummy certificate so nginx can start..."
docker compose -f docker-compose.liquor.yml exec liquor_nginx \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout /etc/letsencrypt/live/wbliquorsocity.com/privkey.pem \
  -out /etc/letsencrypt/live/wbliquorsocity.com/fullchain.pem \
  -subj "/CN=localhost" 2>/dev/null || true

echo ">>> Requesting real certificate from Let's Encrypt..."
if [ "$STAGING" = "1" ]; then
  STAGING_FLAG="--staging"
else
  STAGING_FLAG=""
fi

docker compose -f docker-compose.liquor.yml run --rm --entrypoint "\
certbot certonly --webroot -w /var/www/certbot \
  $STAGING_FLAG \
  --email $EMAIL --agree-tos --no-eff-email \
  -d wbliquorsocity.com -d admin.wbliquorsocity.com -d member.wbliquorsocity.com \
  --deploy-hook 'nginx -s reload'" liquor_certbot

echo ">>> Reloading nginx with the real certificate..."
docker compose -f docker-compose.liquor.yml exec liquor_nginx nginx -s reload

echo ">>> Done. Certificates installed for: $DOMAINS"