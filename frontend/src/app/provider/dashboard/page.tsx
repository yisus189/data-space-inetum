'use client';

import { useEffect, useState } from 'react';
import {
  Typography,
  Box,
  Tabs,
  Tab,
  Grid,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import { Add, CloudUpload } from '@mui/icons-material';
import { DatasetCard } from '@/components/DatasetCard';
import { ImportModal } from '@/components/ImportModal';
import { Dataset, datasetsApi, openmetadataApi, CatalogItem } from '@/lib/api';
import { useAuthToken } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

export default function ProviderDashboardPage() {
  const auth = useAuthToken();
  const router = useRouter();
  const [tab, setTab] = useState(0);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<CatalogItem | null>(null);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      router.push('/');
      return;
    }

    const isProvider = auth.user?.profile?.realm_access?.roles?.includes('provider');
    if (!isProvider) {
      router.push('/');
      return;
    }

    loadDatasets();
  }, [auth.isAuthenticated]);

  useEffect(() => {
    if (tab === 1) {
      loadCatalog();
    }
  }, [tab]);

  const loadDatasets = async () => {
    try {
      setLoading(true);
      const data = await datasetsApi.list();
      setDatasets(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const loadCatalog = async () => {
    try {
      setLoading(true);
      const data = await openmetadataApi.getCatalog();
      setCatalog(data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await datasetsApi.publish(id);
      await loadDatasets();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to publish dataset');
    }
  };

  const handleImport = (item: CatalogItem) => {
    setSelectedItem(item);
    setImportModalOpen(true);
  };

  if (!auth.isAuthenticated) {
    return null;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h3" component="h1">
          Provider Dashboard
        </Typography>
        <Button
          variant="contained"
          startIcon={<CloudUpload />}
          onClick={() => router.push('/provider/upload')}
        >
          Upload Dataset
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="My Datasets" />
        <Tab label="OpenMetadata Catalog" />
      </Tabs>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {tab === 0 && !loading && (
        <>
          {datasets.length === 0 ? (
            <Alert severity="info">
              No datasets yet. Upload your first dataset or import from OpenMetadata.
            </Alert>
          ) : (
            <Grid container spacing={3}>
              {datasets.map((dataset) => (
                <Grid item xs={12} sm={6} md={4} key={dataset.id}>
                  <DatasetCard
                    dataset={dataset}
                    onPublish={handlePublish}
                    showActions
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}

      {tab === 1 && !loading && (
        <>
          {catalog.length === 0 ? (
            <Alert severity="info">
              No items found in OpenMetadata catalog. Make sure OpenMetadata is configured.
            </Alert>
          ) : (
            <Grid container spacing={2}>
              {catalog.map((item) => (
                <Grid item xs={12} key={item.id}>
                  <Box
                    sx={{
                      p: 2,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Box>
                      <Typography variant="h6">{item.display_name || item.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {item.description || 'No description'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Service: {item.service} | Database: {item.database}
                      </Typography>
                    </Box>
                    <Button
                      variant="outlined"
                      startIcon={<Add />}
                      onClick={() => handleImport(item)}
                    >
                      Import
                    </Button>
                  </Box>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}

      <ImportModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        item={selectedItem}
        onSuccess={() => {
          setTab(0);
          loadDatasets();
        }}
      />
    </Box>
  );
}
