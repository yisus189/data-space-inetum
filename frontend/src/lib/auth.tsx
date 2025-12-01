'use client';

import { AuthProvider } from 'react-oidc-context';
import { WebStorageStateStore } from 'oidc-client-ts';

const keycloakConfig = {
  authority: `${process.env.NEXT_PUBLIC_KEYCLOAK_URL}/realms/${process.env.NEXT_PUBLIC_KEYCLOAK_REALM}`,
  client_id: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'dataspace-ui',
  redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
  response_type: 'code',
  scope: 'openid profile email',
  automaticSilentRenew: true,
  userStore: typeof window !== 'undefined' ? new WebStorageStateStore({ store: window.localStorage }) : undefined,
};

export function OIDCProvider({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider {...keycloakConfig}>
      {children}
    </AuthProvider>
  );
}
