#!/bin/bash
# Quick start script for Data Space

set -e

echo "🚀 Data Space - Quick Start"
echo "=============================="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose first."
    exit 1
fi

echo "1️⃣  Creating .env.local from example..."
if [ ! -f .env.local ]; then
    cp .env.local.example .env.local
    echo "✅ .env.local created"
else
    echo "ℹ️  .env.local already exists, skipping"
fi

echo ""
echo "2️⃣  Starting all services..."
docker-compose up -d

echo ""
echo "3️⃣  Waiting for services to be ready..."
echo "   This may take a few minutes..."

# Wait for API to be ready
echo "   Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ API is ready"
        break
    fi
    sleep 2
done

# Wait for Keycloak
echo "   Waiting for Keycloak..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health/ready > /dev/null 2>&1; then
        echo "   ✅ Keycloak is ready"
        break
    fi
    sleep 2
done

echo ""
echo "✅ All services are running!"
echo ""
echo "📊 Service URLs:"
echo "   API:              http://localhost:8000"
echo "   API Docs:         http://localhost:8000/docs"
echo "   Keycloak:         http://localhost:8080"
echo "   MinIO Console:    http://localhost:9001"
echo "   OpenMetadata:     http://localhost:8585"
echo ""
echo "🔑 Default Credentials:"
echo "   Keycloak Admin:   kc-admin / changeMeAdmin123!"
echo "   MinIO:            minio_admin / minio_password"
echo ""
echo "👤 Test Users (for API authentication):"
echo "   Provider:  provider-user / provider123"
echo "   Consumer:  consumer-user / consumer123"
echo "   Broker:    broker-user / broker123"
echo ""
echo "📚 Get started:"
echo "   1. Visit http://localhost:8000/docs to explore the API"
echo "   2. Get an access token:"
echo '      TOKEN=$(curl -s -X POST http://localhost:8080/realms/dataspace/protocol/openid-connect/token \'
echo "        -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "        -d 'username=provider-user' \\"
echo "        -d 'password=provider123' \\"
echo "        -d 'grant_type=password' \\"
echo "        -d 'client_id=dataspace-api' \\"
echo "        -d 'client_secret=dataspace-secret' | jq -r '.access_token')"
echo ""
echo "   3. Create a publication:"
echo '      curl -X POST http://localhost:8000/publications \'
echo '        -H "Authorization: Bearer $TOKEN" \'
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"title\": \"My Dataset\", \"description\": \"Test dataset\"}'"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
