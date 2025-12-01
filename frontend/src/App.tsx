import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import PublicCatalog from './pages/PublicCatalog';
import DatasetDetail from './pages/DatasetDetail';
import ProviderDashboard from './pages/ProviderDashboard';
import UploadDataset from './pages/UploadDataset';
import CatalogBrowser from './pages/CatalogBrowser';

const ProtectedRoute: React.FC<{ 
  children: React.ReactNode;
  requireProvider?: boolean;
}> = ({ children, requireProvider = false }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (requireProvider && !user?.isProvider) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minHeight="100vh"
      >
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<PublicCatalog />} />
          <Route path="/datasets/:id" element={<DatasetDetail />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireProvider>
                <ProviderDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/upload"
            element={
              <ProtectedRoute requireProvider>
                <UploadDataset />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalog"
            element={
              <ProtectedRoute requireProvider>
                <CatalogBrowser />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
