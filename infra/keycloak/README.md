# Keycloak dev for Data Space — Fase 3

This directory contains the minimal configuration to run Keycloak locally with a development realm (example users and roles).

Steps:

1. cd infra/keycloak
2. docker compose up -d
3. Wait for healthcheck: http://localhost:8080/health/ready
4. Admin console: http://localhost:8080 (admin/admin)

Users:
- provider1 / password (role: provider)
- consumer1 / password (role: consumer)
- broker1 / password (role: broker)

Client: dataspace-api (public client)

Example token request (password grant):

TOKEN=$(curl -s -X POST "http://localhost:8080/realms/myrealm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=dataspace-api" \
  -d "username=provider1" \
  -d "password=password" | jq -r .access_token)