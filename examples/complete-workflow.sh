#!/bin/bash
# Example workflow demonstrating the complete Data Space flow

set -e

API_URL="http://localhost:8000"
KEYCLOAK_URL="http://localhost:8080"

echo "📋 Data Space Complete Workflow Example"
echo "========================================"
echo ""

# Function to get token
get_token() {
    local username=$1
    local password=$2
    curl -s -X POST "$KEYCLOAK_URL/realms/dataspace/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$username" \
        -d "password=$password" \
        -d "grant_type=password" \
        -d "client_id=dataspace-api" \
        -d "client_secret=dataspace-secret" | jq -r '.access_token'
}

echo "1️⃣  Getting tokens for different users..."
PROVIDER_TOKEN=$(get_token "provider-user" "provider123")
CONSUMER_TOKEN=$(get_token "consumer-user" "consumer123")

if [ -z "$PROVIDER_TOKEN" ] || [ "$PROVIDER_TOKEN" == "null" ]; then
    echo "❌ Failed to get provider token. Is Keycloak running?"
    exit 1
fi

echo "✅ Got provider token: ${PROVIDER_TOKEN:0:20}..."
echo "✅ Got consumer token: ${CONSUMER_TOKEN:0:20}..."
echo ""

echo "2️⃣  Provider creates a publication..."
PUBLICATION=$(curl -s -X POST "$API_URL/publications" \
    -H "Authorization: Bearer $PROVIDER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Customer Analytics Dataset",
        "description": "Anonymized customer data for analytics purposes",
        "metadata": {
            "format": "CSV",
            "size": "500MB",
            "records": 1000000,
            "columns": ["customer_id", "age", "region", "purchase_amount"]
        }
    }')

PUBLICATION_ID=$(echo "$PUBLICATION" | jq -r '.id')
echo "✅ Created publication: $PUBLICATION_ID"
echo "   Title: $(echo "$PUBLICATION" | jq -r '.title')"
echo ""

echo "3️⃣  Consumer lists available publications..."
PUBLICATIONS=$(curl -s "$API_URL/publications")
echo "✅ Found $(echo "$PUBLICATIONS" | jq -r '.total') publications"
echo ""

echo "4️⃣  Consumer creates a request for the publication..."
REQUEST=$(curl -s -X POST "$API_URL/requests" \
    -H "Authorization: Bearer $CONSUMER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"subject\": \"Request access for market analysis\",
        \"publication_id\": \"$PUBLICATION_ID\"
    }")

REQUEST_ID=$(echo "$REQUEST" | jq -r '.id')
echo "✅ Created request: $REQUEST_ID"
echo "   State: $(echo "$REQUEST" | jq -r '.state')"
echo ""

echo "5️⃣  Provider reviews and creates/signs a contract..."
CONTRACT=$(curl -s -X POST "$API_URL/contracts" \
    -H "Authorization: Bearer $PROVIDER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"request_id\": \"$REQUEST_ID\",
        \"terms\": {
            \"duration\": \"1 year\",
            \"usage_purpose\": \"market analysis\",
            \"data_retention\": \"delete after 1 year\",
            \"allowed_operations\": [\"read\", \"aggregate\"]
        }
    }")

CONTRACT_ID=$(echo "$CONTRACT" | jq -r '.id')
echo "✅ Created and signed contract: $CONTRACT_ID"
echo "   State: $(echo "$CONTRACT" | jq -r '.state')"
echo ""

echo "6️⃣  Consumer initiates a data transfer..."
TRANSFER=$(curl -s -X POST "$API_URL/transfers" \
    -H "Authorization: Bearer $CONSUMER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"contract_id\": \"$CONTRACT_ID\",
        \"destination\": \"s3://consumer-bucket/analytics-data\",
        \"operation\": \"put_object\",
        \"expires_in\": 3600
    }")

TRANSFER_ID=$(echo "$TRANSFER" | jq -r '.id')
PRESIGNED_URL=$(echo "$TRANSFER" | jq -r '.presigned_url')
echo "✅ Created transfer: $TRANSFER_ID"
echo "   State: $(echo "$TRANSFER" | jq -r '.state')"
echo "   Presigned URL: ${PRESIGNED_URL:0:50}..."
echo ""

echo "7️⃣  Checking audit logs..."
AUDIT_LOGS=$(curl -s "$API_URL/audit" \
    -H "Authorization: Bearer $PROVIDER_TOKEN")
echo "✅ Found $(echo "$AUDIT_LOGS" | jq -r '.total') audit log entries"
echo ""

echo "Recent audit events:"
echo "$AUDIT_LOGS" | jq -r '.items[0:5] | .[] | "   - \(.event_type) at \(.timestamp)"'
echo ""

echo "8️⃣  Syncing catalog from OpenMetadata (optional)..."
SYNC_RESULT=$(curl -s -X POST "$API_URL/sync/catalog?limit=10" \
    -H "Authorization: Bearer $PROVIDER_TOKEN")
echo "✅ Catalog sync result:"
echo "   Imported: $(echo "$SYNC_RESULT" | jq -r '.imported')"
echo "   Updated: $(echo "$SYNC_RESULT" | jq -r '.updated')"
echo ""

echo "9️⃣  Listing catalog entries..."
CATALOG=$(curl -s "$API_URL/catalog")
echo "✅ Found $(echo "$CATALOG" | jq -r '.total') catalog entries"
echo ""

echo "🎉 Complete workflow executed successfully!"
echo ""
echo "Summary:"
echo "  - Publication created: $PUBLICATION_ID"
echo "  - Request created: $REQUEST_ID"
echo "  - Contract signed: $CONTRACT_ID"
echo "  - Transfer initiated: $TRANSFER_ID"
echo ""
echo "You can now:"
echo "  - Use the presigned URL to upload/download data"
echo "  - View all resources in the API docs: $API_URL/docs"
echo "  - Check audit logs for complete traceability"
echo ""
