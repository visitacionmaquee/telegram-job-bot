#!/bin/bash
# ==============================================================================
# JobRadar AI — Automated Let's Encrypt SSL Provisioner for Nginx
# ==============================================================================

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ]; then
    read -p "Enter your domain name (e.g. jobradar.duckdns.org or yourdomain.com): " DOMAIN
fi

if [ -z "$EMAIL" ]; then
    read -p "Enter your email address (for Let's Encrypt renewal alerts): " EMAIL
fi

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ Domain and Email are required to provision SSL."
    exit 1
fi

echo "🔐 [1/4] Preparing temporary SSL certificate for Nginx startup..."
CERT_PATH="/etc/letsencrypt/live/jobradar"

# Run helper in certbot container to initialize certificate directory
docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
  sh -c 'mkdir -p $CERT_PATH && \
  if [ ! -f $CERT_PATH/fullchain.pem ]; then \
    apk add --no-cache openssl && \
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout $CERT_PATH/privkey.pem \
      -out $CERT_PATH/fullchain.pem \
      -subj \"/CN=localhost\"; \
  fi'" certbot

echo "🚀 [2/4] Starting Nginx in production mode..."
docker compose -f docker-compose.prod.yml up -d nginx

echo "📜 [3/4] Requesting production Let's Encrypt certificate for $DOMAIN..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL \
    -d $DOMAIN \
    --rsa-key-size 4096 \
    --agree-tos \
    --force-renewal \
    --cert-name jobradar \
    --non-interactive" certbot

echo "🔄 [4/4] Reloading Nginx with trusted Let's Encrypt SSL certificate..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "🎉 SSL Certificate installed successfully!"
echo "👉 Your production dashboard is live at: https://$DOMAIN/dashboard"
