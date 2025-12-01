'use client';

import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { OIDCProvider } from '@/lib/auth';
import { theme } from '@/lib/theme';
import { Header } from '@/components/Header';
import { Container, Box } from '@mui/material';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <OIDCProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <Header />
            <Container maxWidth="xl">
              <Box sx={{ py: 4 }}>
                {children}
              </Box>
            </Container>
          </ThemeProvider>
        </OIDCProvider>
      </body>
    </html>
  );
}
