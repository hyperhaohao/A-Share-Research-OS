#!/bin/bash
# Self-signed cert for development / staging (production: use Let's Encrypt)
mkdir -p deploy/certs
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout deploy/certs/tls.key \
  -out deploy/certs/tls.crt \
  -subj "/CN=asro.local"
echo "Self-signed certs generated in deploy/certs/"
