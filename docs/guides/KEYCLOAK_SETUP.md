# Keycloak Setup Guide

This guide explains how to configure Keycloak for the Data Space application.

## Automatic Setup (Recommended)

The docker-compose configuration automatically imports the realm configuration on startup. The pre-configured realm includes:

- **Realm**: `dataspace`
- **Clients**: `dataspace-api`, `dataspace-ui`
- **Roles**: `provider`, `consumer`, `broker`
- **Test Users**: See table below

### Pre-configured Users

| Username | Password | Role | Email |
|----------|----------|------|-------|
| provider-user | provider123 | provider | provider@dataspace.local |
| consumer-user | consumer123 | consumer | consumer@dataspace.local |
| broker-user | broker123 | broker | broker@dataspace.local |

## Manual Setup

If you need to set up Keycloak manually:

### 1. Access Keycloak Admin Console

1. Navigate to http://localhost:8080
2. Click "Administration Console"
3. Login with admin/admin

### 2. Create Realm

1. Click "Create Realm" button
2. Name: `dataspace`
3. Click "Create"

### 3. Create Roles

1. Go to "Realm roles"
2. Click "Create role"
3. Create the following roles:
   - `provider` - Data provider role
   - `consumer` - Data consumer role
   - `broker` - Data broker role

### 4. Create Client for API

1. Go to "Clients" → "Create client"
2. Client ID: `dataspace-api`
3. Client Protocol: `openid-connect`
4. Click "Next"
5. **Authentication flow**:
   - Standard flow: ON
   - Direct access grants: ON
   - Service accounts roles: ON
6. Click "Next"
7. **Valid redirect URIs**: `*`
8. **Web origins**: `*`
9. Click "Save"
10. Go to "Credentials" tab
11. Copy the "Client secret" (use this in your .env file)

### 5. Create Client for UI (Optional)

1. Go to "Clients" → "Create client"
2. Client ID: `dataspace-ui`
3. Client Protocol: `openid-connect`
4. Click "Next"
5. **Authentication flow**:
   - Standard flow: ON
   - Direct access grants: ON
6. **Client authentication**: OFF (public client)
7. Click "Next"
8. **Valid redirect URIs**: 
   - `http://localhost:3000/*`
   - `http://localhost:8000/*`
9. **Web origins**: `*`
10. Click "Save"

### 6. Create Users

1. Go to "Users" → "Create user"
2. Fill in user details:
   - Username: `provider-user`
   - Email: `provider@dataspace.local`
   - First name: `Provider`
   - Last name: `User`
3. Click "Create"
4. Go to "Credentials" tab
5. Click "Set password"
6. Set password: `provider123`
7. Temporary: OFF
8. Click "Save"
9. Go to "Role mapping" tab
10. Click "Assign role"
11. Filter by realm roles
12. Select `provider` role
13. Click "Assign"

Repeat for other users (consumer-user, broker-user).

## Using the Realm Export

The realm export file is located at `infra/keycloak/realm-export.json`.

### Importing the Realm

#### Via Docker (Automatic)

The docker-compose.yml already includes the import configuration:

```yaml
volumes:
  - ./infra/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json
command: start-dev --import-realm
```

#### Via Admin Console

1. Log in to Keycloak Admin Console
2. Click "Create Realm"
3. Click "Browse" under "Resource file"
4. Select `infra/keycloak/realm-export.json`
5. Click "Create"

### Exporting a Realm

To export your realm configuration:

```bash
docker exec -it <keycloak-container> /opt/keycloak/bin/kc.sh export \
  --dir /opt/keycloak/data/export \
  --realm dataspace \
  --users realm_file
```

Then copy the file from the container:

```bash
docker cp <keycloak-container>:/opt/keycloak/data/export/dataspace-realm.json ./infra/keycloak/realm-export.json
```

## Testing Authentication

### Get Access Token

```bash
curl -X POST "http://localhost:8080/realms/dataspace/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" \
  -d "grant_type=password" \
  -d "username=provider-user" \
  -d "password=provider123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Decode JWT Token

Visit https://jwt.io and paste the `access_token` to inspect the claims:

```json
{
  "exp": 1234567890,
  "iat": 1234567890,
  "sub": "user-id-here",
  "preferred_username": "provider-user",
  "email": "provider@dataspace.local",
  "realm_access": {
    "roles": ["provider"]
  }
}
```

### Use Token in API Request

```bash
curl -X GET "http://localhost:8000/publications" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Production Considerations

### SSL/TLS

For production, enable HTTPS:

1. Set `KC_HOSTNAME_STRICT_HTTPS=true`
2. Configure SSL certificates
3. Use a reverse proxy (nginx, Traefik)

### Database

Use external PostgreSQL database instead of the shared database:

```yaml
environment:
  KC_DB: postgres
  KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
  KC_DB_USERNAME: keycloak
  KC_DB_PASSWORD: secure-password
```

### High Availability

For HA setup:
- Run multiple Keycloak instances
- Use load balancer (nginx, HAProxy)
- Shared database for session storage
- Configure cache replication

### Security Best Practices

1. **Change default admin password**
2. **Use strong client secrets**
3. **Enable SSL/TLS**
4. **Configure password policies**
5. **Enable MFA for admin accounts**
6. **Regular security updates**
7. **Monitor authentication logs**

## Troubleshooting

### Cannot connect to Keycloak

- Check if Keycloak container is running: `docker ps`
- Check Keycloak logs: `docker logs <keycloak-container>`
- Verify port 8080 is not in use: `lsof -i :8080`

### Authentication fails

- Verify credentials are correct
- Check if realm name matches (`dataspace`)
- Verify client ID and secret
- Check if user has required roles

### Token validation fails

- Ensure Keycloak is accessible from API container
- Check KEYCLOAK_SERVER_URL in .env file
- Verify token hasn't expired
- Check if realm public key is accessible

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [OpenID Connect](https://openid.net/connect/)
