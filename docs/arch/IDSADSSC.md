# Mapeo de controles IDSA y DSSC

Objetivo: indicar cómo el Data Space aplica normas IDSA y DSSC a nivel funcional y técnico.

1. Identidad y confianza
- Soporte para autenticación fuerte (OAuth2 / OIDC y mTLS).
- Registro de participantes y roles (Proveedor, Consumidor, Broker).

2. Gobernanza de datos
- Publicaciones con metadatos estandarizados (schema compatible con OpenMetadata).
- Políticas de uso y licencias adjuntas a cada publicación.

3. Contratos y acuerdos
- Contratos modelados como recursos con estado: draft -> offered -> accepted -> active -> terminated.
- "Firma implícita": aceptación electrónica registrada, con sello temporal y hash del acuerdo.

4. Transferencias
- Transferencias iniciadas por contratos activos.
- Registro inmutable de eventos de transferencia (auditoría).

5. Seguridad y protección de datos
- Encriptación en tránsito (TLS) y en reposo (configurable).
- Control de acceso por políticas (RBAC + atributos si se requiere).

6. Interoperabilidad
- Catálogo extraído desde OpenMetadata; metadatos compatibles (datasets, schema, lineage).

Recomendaciones legales/operacionales
- Revisar plantillas de contrato con el equipo legal.
- Auditoría externa para verificar cumplimiento.