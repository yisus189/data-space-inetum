# Data Space conforme IDSA & DSSC

## Resumen

Implementación completa de un Data Space empresarial que sigue principios IDSA (International Data Spaces Association) y DSSC (Data Spaces Support Centre).

### Características principales

- ✅ **Gestión completa de datos**: Publicaciones, solicitudes, contratos y transferencias
- ✅ **Autenticación robusta**: Integración con Keycloak OIDC/JWT
- ✅ **Catálogo de datos**: Integración completa con OpenMetadata
- ✅ **Transferencias seguras**: Presigned URLs con MinIO/S3
- ✅ **Auditoría completa**: Registro inmutable de todas las acciones
- ✅ **Persistencia**: PostgreSQL con SQLAlchemy y Alembic
- ✅ **Testing**: Suite de tests con pytest
- ✅ **CI/CD**: GitHub Actions para validación automática

## Arquitectura

### Componentes

1. **API (FastAPI)**: API REST con endpoints para publicaciones, solicitudes, contratos, transferencias y auditoría
2. **PostgreSQL**: Base de datos principal para persistencia
3. **Keycloak**: Servidor de autenticación/autorización OIDC
4. **MinIO**: Almacenamiento S3-compatible para transferencias de datos
5. **OpenMetadata**: Catálogo de metadatos de datos

### Estructura del proyecto

```
data-space-inetum/
├── src/
│   ├── app/
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── audit.py        # Audit logging
│   │   └── transfers.py    # S3/MinIO transfers
│   ├── db/
│   │   ├── __init__.py     # Database config
│   │   └── models.py       # SQLAlchemy models
│   ├── auth/
│   │   └── __init__.py     # Keycloak authentication
│   ├── catalog/
│   │   └── __init__.py     # OpenMetadata integration
│   └── main.py             # FastAPI application
├── alembic/                # Database migrations
├── tests/                  # Test suite
├── infra/
│   └── keycloak/
│       └── realm-export.json  # Keycloak realm config
├── docker-compose.yml      # Complete stack
├── Dockerfile              # API container
├── pyproject.toml          # Dependencies
└── README.md               # This file
```

## Inicio rápido

### Prerrequisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

### 1. Configuración inicial

```bash
# Clonar el repositorio
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum

# Crear archivo de configuración local (opcional, usa valores por defecto)
cp .env.local.example .env.local
```

### 2. Levantar toda la infraestructura

```bash
# Levantar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Verificar que todos los servicios estén arriba
docker-compose ps
```

Servicios disponibles:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Keycloak**: http://localhost:8080 (admin: kc-admin / changeMeAdmin123!)
- **MinIO Console**: http://localhost:9001 (admin: minio_admin / minio_password)
- **OpenMetadata**: http://localhost:8585

### 3. Autenticación

El sistema usa Keycloak para autenticación. Usuarios preconfigurados:

| Usuario | Contraseña | Rol | Propósito |
|---------|-----------|-----|-----------|
| provider-user | provider123 | provider | Publicar datos |
| consumer-user | consumer123 | consumer | Solicitar datos |
| broker-user | broker123 | broker | Intermediación |

#### Obtener un token de acceso:

```bash
# Obtener token para provider-user
curl -X POST http://localhost:8080/realms/dataspace/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=provider-user" \
  -d "password=provider123" \
  -d "grant_type=password" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-secret" | jq -r '.access_token'
```

Guardar el token en una variable:
```bash
export TOKEN="eyJhbGc..."
```

## Uso del API

### Publicaciones

```bash
# Crear una publicación (requiere rol provider)
curl -X POST http://localhost:8000/publications \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer Dataset",
    "description": "Customer information dataset",
    "metadata": {"format": "CSV", "size": "10MB"}
  }'

# Listar publicaciones (público)
curl http://localhost:8000/publications

# Obtener publicación específica
curl http://localhost:8000/publications/{id}
```

### Solicitudes de acceso

```bash
# Crear solicitud (requiere rol consumer)
curl -X POST http://localhost:8000/requests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Request access to Customer Dataset",
    "publication_id": "pub-id-here"
  }'

# Listar solicitudes
curl http://localhost:8000/requests \
  -H "Authorization: Bearer $TOKEN"
```

### Contratos

```bash
# Crear/firmar contrato
curl -X POST http://localhost:8000/contracts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-id-here",
    "terms": {"duration": "1 year", "usage": "analytics"}
  }'

# Listar contratos
curl http://localhost:8000/contracts \
  -H "Authorization: Bearer $TOKEN"
```

### Transferencias de datos

```bash
# Iniciar transferencia (genera presigned URL)
curl -X POST http://localhost:8000/transfers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "contract-id-here",
    "destination": "s3://my-bucket/data.csv",
    "operation": "put_object",
    "expires_in": 3600
  }'

# La respuesta incluye el presigned_url que puede usarse para subir/descargar datos
```

### Auditoría

```bash
# Listar logs de auditoría
curl http://localhost:8000/audit \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por tipo de evento
curl "http://localhost:8000/audit?event_type=contract_created" \
  -H "Authorization: Bearer $TOKEN"
```

## Integración con OpenMetadata

### Sincronizar catálogo

```bash
# Sincronizar catálogo desde OpenMetadata (requiere rol provider)
curl -X POST http://localhost:8000/sync/catalog \
  -H "Authorization: Bearer $TOKEN"
```

### Visualizar catálogo

```bash
# Listar entradas del catálogo (público)
curl http://localhost:8000/catalog

# Ver entrada específica del catálogo
curl http://localhost:8000/catalog/{id}

# Descargar metadata como JSON
curl http://localhost:8000/catalog/{id}/download -o catalog-metadata.json
```

El catálogo importado incluye:
- **Schema**: Columnas, tipos de datos, nullability
- **Lineage**: Upstream y downstream dependencies
- **Metadata**: Tags, owner, source system, etc.

## Desarrollo local

### Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -e .[dev]
```

### Migraciones de base de datos

```bash
# Crear nueva migración
alembic revision --autogenerate -m "Description"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1
```

### Ejecutar tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=src --cov-report=html

# Tests específicos
pytest tests/test_api.py -v
```

### Ejecutar API localmente

```bash
# Con recarga automática
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuración

### Variables de entorno

Ver `.env.local.example` para todas las variables disponibles:

- **DATABASE_URL**: Conexión PostgreSQL
- **OPENMETADATA_URL**: URL de OpenMetadata
- **KEYCLOAK_URL**: URL de Keycloak
- **MINIO_ENDPOINT**: Endpoint de MinIO
- Etc.

### Credenciales importantes

**Keycloak Admin:**
- Usuario: `kc-admin`
- Contraseña: `changeMeAdmin123!`
- URL: http://localhost:8080

**MinIO:**
- Access Key: `minio_admin`
- Secret Key: `minio_password`
- Console: http://localhost:9001

**PostgreSQL:**
- Usuario: `dataspace_user`
- Contraseña: `changeme`
- Base de datos: `dataspace`

## Seguridad

⚠️ **IMPORTANTE**: Esta configuración es para desarrollo. Para producción:

1. Cambiar todas las contraseñas por defecto
2. Habilitar SSL/TLS en todos los servicios
3. Configurar firewalls y network policies
4. Revisar políticas de acceso en Keycloak
5. Configurar backups de la base de datos
6. Implementar rate limiting
7. Auditar logs de seguridad regularmente

## Cumplimiento IDSA/DSSC

Este Data Space implementa principios clave de IDSA y DSSC:

- ✅ **Soberanía de datos**: Control sobre quién accede a los datos
- ✅ **Trazabilidad**: Audit log completo de todas las operaciones
- ✅ **Contratos**: Acuerdos formales antes de transferencias
- ✅ **Autenticación**: Identity management con Keycloak
- ✅ **Catálogo**: Metadatos estandarizados con OpenMetadata

Ver `/docs/arch/IDSADSSC.md` para detalles del mapeo de controles.

## Troubleshooting

### Los servicios no inician

```bash
# Verificar logs
docker-compose logs

# Reiniciar servicios específicos
docker-compose restart api
```

### Problemas de autenticación

```bash
# Verificar que Keycloak esté arriba
curl http://localhost:8080/health/ready

# Verificar realm
curl http://localhost:8080/realms/dataspace
```

### Problemas con migraciones

```bash
# Ver estado actual
alembic current

# Historial de migraciones
alembic history

# Ejecutar desde contenedor
docker-compose run --rm migrations alembic upgrade head
```

## Contribuir

1. Fork el repositorio
2. Crear feature branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Apache-2.0 - Ver archivo LICENSE

## Soporte

Para preguntas o problemas, abrir un issue en GitHub.

---

**Nota**: Este proyecto es una implementación de referencia. Requiere ajustes legales y revisión de seguridad antes de uso en producción.