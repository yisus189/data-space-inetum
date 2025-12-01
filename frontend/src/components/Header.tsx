'use client';

import { AppBar, Toolbar, Typography, Button, Box, Container } from '@mui/material';
import { useAuth } from 'react-oidc-context';
import Link from 'next/link';

export function Header() {
  const auth = useAuth();

  const handleLogin = () => {
    auth.signinRedirect();
  };

  const handleLogout = () => {
    auth.signoutRedirect();
  };

  const isProvider = auth.user?.profile?.realm_access?.roles?.includes('provider');
  const isConsumer = auth.user?.profile?.realm_access?.roles?.includes('consumer');

  return (
    <AppBar position="static">
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          <Typography
            variant="h6"
            component={Link}
            href="/"
            sx={{
              flexGrow: 1,
              fontWeight: 700,
              color: 'inherit',
              textDecoration: 'none',
            }}
          >
            Data Space Inetum
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button color="inherit" component={Link} href="/">
              Catalog
            </Button>

            {isProvider && (
              <>
                <Button color="inherit" component={Link} href="/provider/dashboard">
                  My Datasets
                </Button>
                <Button color="inherit" component={Link} href="/provider/upload">
                  Upload
                </Button>
              </>
            )}

            {auth.isAuthenticated ? (
              <>
                <Typography variant="body2" sx={{ mr: 2 }}>
                  {auth.user?.profile?.preferred_username}
                </Typography>
                <Button color="inherit" onClick={handleLogout}>
                  Logout
                </Button>
              </>
            ) : (
              <Button color="inherit" onClick={handleLogin}>
                Login
              </Button>
            )}
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
