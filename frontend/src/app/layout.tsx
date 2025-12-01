'use client';

import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { OIDCProvider } from '@/lib/auth';
import { theme } from '@/lib/theme';
import { Header } from '@/components/Header';
import { Container, Box } from '@mui/material';

export const metadata = {
  title: 'Data Space Inetum',
  description: 'IDSA & DSSC compliant Data Space for secure data sharing',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="IDSA & DSSC compliant Data Space for secure data sharing" />
        <title>Data Space Inetum</title>
      </head>
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
