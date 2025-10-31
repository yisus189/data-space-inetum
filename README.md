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
- Integración con OpenMetadata para sincronizar catálogo.
- Almacenamiento de metadatos y eventos (Postgres)
- Servicio de auditoría que registra trazabilidad (event store)
- Autenticación/Autorización: soporta OAuth2 / mTLS (configurable)
- Cumplimiento: mapeo inicial de controles IDSA/DSSC documentado en /docs/arch/IDSADSSC.md

Cómo usar (rápido)
1. Levantar con Docker Compose:
   docker-compose up --build
2. API disponible en: http://localhost:8000
3. UI OpenAPI: http://localhost:8000/docs
4. Configurar endpoint OpenMetadata en `config/.env` para sincronizar catálogo.

Notas
- Este repo ofrece una base arquitectónica y un prototipo. Requiere ajustes legales y revisión de seguridad antes de uso en producción.
- La "firma implícita" de contratos está modelada como aceptación digital y registro inmutable del evento con auditoría; si necesitas firma basada en claves asimétricas, lo añadimos.