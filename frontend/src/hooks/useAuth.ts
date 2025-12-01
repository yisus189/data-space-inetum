'use client';

import { useAuth } from 'react-oidc-context';
import { useEffect } from 'react';
import { setAuthToken } from '@/lib/api';

export function useAuthToken() {
  const auth = useAuth();

  useEffect(() => {
    if (auth.user?.access_token) {
      setAuthToken(auth.user.access_token);
    } else {
      setAuthToken(null);
    }
  }, [auth.user?.access_token]);

  return auth;
}
