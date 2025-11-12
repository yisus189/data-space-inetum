# Data Space conforme IDSA & DSSC

Resumen
- Proyecto: Data Space empresarial que sigue principios IDSA y DSSC.
- Objetivo: Permitir publicación de datos, emisiones/recepciones de solicitudes, firma implícita de contratos, y gestión de transferencias de datos.
- Catálogo: Integración con OpenMetadata para importar el catálogo y exponerlo en el Data Space.

Componentes principales
- API (FastAPI) con endpoints para:
  - Publicaciones (datasets/catalog items)
  - Solicitudes (requests)
  - Contratos (agreements) — firmados implícitamente mediante aceptación y registro de eventos
  - Transferencias de datos (data transfers)
  - Métricas Prometheus (`/metrics`)
  - Health check (`/health`)
- Integración con OpenMetadata para sincronizar catálogo.
- Almacenamiento de metadatos y eventos (Postgres)
- Servicio de auditoría que registra trazabilidad (event store)
- **Autenticación/Autorización**: 
  - JWT/JWKS con Keycloak (OAuth2/OIDC)
  - Cache JWKS con TTL configurable
  - Validación completa de claims (iss, aud, exp, nbf)
  - Retry con exponential backoff
- **Observabilidad**:
  - Error handling estandarizado con request_id
  - Logging estructurado con request tracking
  - Métricas Prometheus (HTTP, JWT, JWKS cache)
- Cumplimiento: mapeo inicial de controles IDSA/DSSC documentado en /docs/arch/IDSADSSC.md

Cómo usar (rápido)
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Configurar variables de entorno (copiar .env.example a .env y ajustar):
   ```bash
   cp .env.example .env
   # Editar .env con configuración de Keycloak, OpenMetadata, etc.
   ```

3. Levantar con Docker Compose (opcional):
   ```bash
   docker-compose up --build
   ```

4. O ejecutar directamente:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. API disponible en: http://localhost:8000
6. UI OpenAPI: http://localhost:8000/docs
7. Métricas Prometheus: http://localhost:8000/metrics
8. Health check: http://localhost:8000/health

Ejecutar tests
```bash
pytest tests/ -v
```

Documentación adicional
- [Autenticación y Middleware](docs/auth-middleware.md) - Documentación completa sobre autenticación JWT, error handling, logging y métricas
- [Arquitectura IDSA/DSSC](docs/arch/IDSADSSC.md) - Mapeo de controles de cumplimiento
- [Ejemplos de uso](examples/auth_example.py) - Ejemplos de cómo proteger endpoints con autenticación

Notas
- Este repo ofrece una base arquitectónica y un prototipo. Requiere ajustes legales y revisión de seguridad antes de uso en producción.
- La "firma implícita" de contratos está modelada como aceptación digital y registro inmutable del evento con auditoría; si necesitas firma basada en claves asimétricas, lo añadimos.
- Fase 4 implementada: Hardening, observabilidad y resiliencia para autenticación ✅