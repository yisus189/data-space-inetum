import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Keycloak from 'keycloak-js';

interface User {
  sub: string;
  preferred_username?: string;
  email?: string;
  roles: string[];
  isProvider: boolean;
  isConsumer: boolean;
  isAdmin: boolean;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  keycloak: Keycloak | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8180',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'myrealm',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'dataspace-ui',
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const kc = new Keycloak(keycloakConfig);

    kc.init({
      onLoad: 'check-sso',
      silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
      pkceMethod: 'S256',
    })
      .then((authenticated) => {
        setKeycloak(kc);
        setIsAuthenticated(authenticated);
        
        if (authenticated && kc.tokenParsed) {
          const tokenParsed = kc.tokenParsed as Record<string, unknown>;
          const realmRoles = (tokenParsed.realm_access as { roles?: string[] })?.roles || [];
          
          setUser({
            sub: tokenParsed.sub as string,
            preferred_username: tokenParsed.preferred_username as string,
            email: tokenParsed.email as string,
            roles: realmRoles,
            isProvider: realmRoles.includes('provider') || realmRoles.includes('admin'),
            isConsumer: realmRoles.includes('consumer') || realmRoles.includes('admin'),
            isAdmin: realmRoles.includes('admin'),
          });
          setToken(kc.token || null);
        }
        
        setIsLoading(false);
      })
      .catch((error) => {
        console.error('Keycloak init error:', error);
        setIsLoading(false);
      });

    // Token refresh
    const refreshInterval = setInterval(() => {
      if (kc.authenticated) {
        kc.updateToken(70)
          .then((refreshed) => {
            if (refreshed) {
              setToken(kc.token || null);
            }
          })
          .catch(() => {
            console.warn('Token refresh failed');
          });
      }
    }, 60000);

    return () => clearInterval(refreshInterval);
  }, []);

  const login = () => {
    keycloak?.login();
  };

  const logout = () => {
    keycloak?.logout({ redirectUri: window.location.origin });
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        user,
        token,
        login,
        logout,
        keycloak,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
