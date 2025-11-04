# Fase 1 — API (Endpoints)

Endpoints implementados:
- Participants: CRUD (/participants)
- Publications: CRUD (/publications)
- Requests: create/list/get/update (/requests)
- Contracts: create/list/get/toggle (/contracts)
- Transfers: create/list/get/update (/transfers)

Autenticación (desarrollo):
- Placeholder: Authorization: Bearer <username>
- Fase 2: integrar Keycloak para validación real de tokens.

Ejecutar localmente:
1. Instalar dependencias: pip install -r requirements.txt
2. Ejecutar la app: uvicorn src.app.main:app --reload --port 8000
3. Documentación: http://localhost:8000/docs

Tests:
- pytest -q
