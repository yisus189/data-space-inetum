# Data Space Frontend

React + TypeScript + Next.js + Material-UI frontend for the Data Space.

## Features

- **OIDC Authentication** with Keycloak
- **Provider Dashboard** for dataset management
- **Consumer Catalog** for browsing public datasets
- **OpenMetadata Integration** for importing datasets
- **Responsive Design** with Material-UI

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Configuration

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=myrealm
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=dataspace-ui
```

## Pages

- `/` - Public catalog
- `/datasets/[id]` - Dataset details
- `/provider/dashboard` - Provider dashboard
- `/provider/upload` - Upload new dataset

## Authentication Roles

- **Provider**: Can upload, manage, and publish datasets
- **Consumer**: Can browse and download public datasets
