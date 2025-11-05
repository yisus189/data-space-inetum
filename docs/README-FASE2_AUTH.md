# Fase 2 — Autenticación OIDC con Keycloak y RBAC

Este documento explica cómo habilitar autenticación OIDC con Keycloak en el Data Space, validar tokens JWT vía JWKS y aplicar RBAC (provider, consumer, broker).

## Variables de entorno

Añade al `.env` o `.env.local`:

```
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=dataspace-realm
KEYCLOAK_CLIENT_ID=dataspace-api
# Opcional: si no se define, se usa KEYCLOAK_CLIENT_ID
KEYCLOAK_AUDIENCE=dataspace-api
OIDC_JWKS_TTL=600
```

## Flujo de autenticación (desarrollo)

1. Inicia Keycloak (ver infra/docker-compose.override.yml si aplica).
2. Obtén un token (password grant) con un usuario de test:
   ```bash
   curl -X POST "$KEYCLOAK_SERVER_URL/realms/$KEYCLOAK_REALM/protocol/openid-connect/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=$KEYCLOAK_CLIENT_ID" \
     -d "grant_type=password" \
     -d "username=provider1" \
     -d "password=provider123"
   ```
3. Usa el `access_token` en las llamadas a la API:
   ```bash
   curl -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/publications
   ```

## Dependencias de FastAPI

- `current_user`: valida el JWT (RS256) contra el JWKS del realm y expone `CurrentUser` con roles.
- Guards:
  - `require_provider`, `require_consumer`, `require_broker`

Ejemplo (ruta protegida):
```python
from fastapi import APIRouter, Depends
from src.app.deps import require_provider, CurrentUser

router = APIRouter()

@router.post("/publications")
def create_publication(payload: dict, user: CurrentUser = Depends(require_provider)):
    ...
```

## Testing

- Los tests unitarios no hacen llamadas de red: mock de la respuesta JWKS.
- Firmado de tokens en local con RS256 usando una clave RSA generada en pruebas.
- Casos cubiertos: exp/iss/aud inválidos, extracción de roles.

Para ejecutar:
```bash
pytest -q -k auth
```