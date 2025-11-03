# Data Space - Fase 0: Infraestructura de Desarrollo

Este documento describe la configuración de infraestructura para el desarrollo local del Data Space en Fase 0.

## Componentes

La infraestructura de desarrollo incluye los siguientes servicios:

1. **PostgreSQL** - Base de datos para la API, Keycloak y OpenMetadata
2. **Keycloak** - Servidor de autenticación y autorización
3. **MinIO** - Almacenamiento de objetos (S3-compatible)
4. **OpenMetadata** - Catálogo de datos
5. **Elasticsearch** - Motor de búsqueda para OpenMetadata
6. **API** - Servicio principal del Data Space

## Requisitos Previos

- Docker 20.10 o superior
- Docker Compose 2.0 o superior
- Al menos 8GB de RAM disponible
- Puertos disponibles: 8000, 8080, 8585, 9000, 9001, 9200, 5432

## Inicio Rápido

### 1. Configuración de Variables de Entorno

Copiar el archivo de ejemplo de variables de entorno:

```bash
cp .env.local.example .env.local
```

Editar `.env.local` según sea necesario. Los valores por defecto son apropiados para desarrollo local.

### 2. Levantar los Servicios

Desde el directorio raíz del proyecto:

```bash
# Usar el docker-compose.override.yml automáticamente
docker-compose -f docker-compose.yml -f infra/docker-compose.override.yml up --build
```

O simplemente (si docker-compose.override.yml está en el directorio raíz):

```bash
docker-compose up --build
```

### 3. Verificar los Servicios

Una vez iniciados, los servicios estarán disponibles en:

- **API**: http://localhost:8000
  - Documentación OpenAPI: http://localhost:8000/docs
  
- **Keycloak**: http://localhost:8080
  - Admin console: http://localhost:8080/admin
  - Usuario admin: `admin` / `admin`
  - Usuario de prueba: `kc-admin` / `changeMeAdmin123!`
  
- **MinIO Console**: http://localhost:9001
  - Credenciales: `minioadmin` / `minioadmin123`
  
- **OpenMetadata**: http://localhost:8585
  - Sin autenticación en modo desarrollo
  
- **Elasticsearch**: http://localhost:9200

### 4. Inicialización

El sistema se inicializa automáticamente con:

- **Keycloak**: Realm `dataspace-realm` importado con:
  - Roles: `provider`, `consumer`, `broker`
  - Usuario: `kc-admin` con todos los roles
  - Cliente: `dataspace-api` con secret `dataspace-client-secret`
  
- **MinIO**: Bucket `dataspace-transfers` creado automáticamente

## Configuración de Keycloak

### Realm: dataspace-realm

El realm está preconfigurado con:

- **Roles**:
  - `provider`: Permite publicar datasets
  - `consumer`: Permite consumir/solicitar datos
  - `broker`: Permite mediar entre providers y consumers

- **Usuarios**:
  - Username: `kc-admin`
  - Password: `changeMeAdmin123!`
  - Roles asignados: provider, consumer, broker

- **Clientes**:
  - Client ID: `dataspace-api`
  - Client Secret: `dataspace-client-secret`
  - Grant Types: authorization_code, client_credentials, password

### Obtener Token de Acceso

Ejemplo usando password grant:

```bash
curl -X POST http://localhost:8080/realms/dataspace-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=dataspace-api" \
  -d "client_secret=dataspace-client-secret" \
  -d "grant_type=password" \
  -d "username=kc-admin" \
  -d "password=changeMeAdmin123!"
```

## Configuración de MinIO

MinIO se inicializa automáticamente con el bucket `dataspace-transfers`.

### Acceso Programático

```python
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    secure=False
)

# Listar buckets
buckets = client.list_buckets()
```

## OpenMetadata

OpenMetadata corre en modo desarrollo sin autenticación. Puedes:

- Explorar el catálogo: http://localhost:8585
- Usar la API REST: http://localhost:8585/api/v1/
- Sincronizar con el Data Space: `POST http://localhost:8000/sync/catalog`

### Nota sobre OpenMetadata en Producción

En algunos entornos, OpenMetadata puede requerir servicios adicionales o configuración avanzada. Para Fase 1, si OpenMetadata no se inicia correctamente, se documentará un fallback con catálogo mock.

## Probar la API

Una vez que los servicios estén corriendo:

```bash
# Crear una publicación
curl -X POST http://localhost:8000/publications \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Customer Dataset",
    "description": "Sample customer data",
    "metadata": {"schema": {"fields": [{"name": "id", "type": "int"}]}}
  }'

# Listar publicaciones
curl http://localhost:8000/publications
```

## Detener los Servicios

```bash
docker-compose down
```

Para eliminar también los volúmenes (datos):

```bash
docker-compose down -v
```

## Troubleshooting

### OpenMetadata no inicia

Si OpenMetadata no inicia correctamente:

1. Verificar logs: `docker-compose logs openmetadata-server`
2. Verificar que Elasticsearch está corriendo: `curl http://localhost:9200`
3. Aumentar tiempo de inicio en healthcheck
4. Como alternativa, comentar el servicio `openmetadata-server` y usar el catálogo mock

### MinIO bucket no se crea

Si el bucket no se crea automáticamente:

1. Verificar logs: `docker-compose logs minio-init`
2. Crear manualmente desde la consola: http://localhost:9001
3. O ejecutar el script manualmente:
   ```bash
   docker-compose exec minio-init sh /scripts/init_minio.sh
   ```

### Keycloak no importa el realm

Si el realm no se importa:

1. Verificar que el archivo existe: `infra/keycloak/realm-export.json`
2. Importar manualmente desde Keycloak admin console
3. Verificar logs: `docker-compose logs keycloak`

## Credenciales de Desarrollo

**⚠️ IMPORTANTE**: Las credenciales incluidas son solo para desarrollo local.

**NUNCA** usar estas credenciales en entornos de producción o expuestos públicamente:

- Keycloak admin: `admin` / `admin`
- Keycloak user: `kc-admin` / `changeMeAdmin123!`
- Keycloak client secret: `dataspace-client-secret`
- MinIO: `minioadmin` / `minioadmin123`
- Database: `dataspace_user` / `changeme`

Antes de cualquier deployment público, rotar todas las credenciales y usar secretos seguros.

## Próximos Pasos (Fase 1)

- Implementar autenticación OAuth2 con Keycloak en la API
- Integración real con OpenMetadata API
- Transferencias de archivos usando MinIO
- Persistencia de datos en PostgreSQL (migrar desde in-memory)
- Tests de integración
- CI/CD pipeline
