import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Button,
  Chip,
  Stack,
} from '@mui/material';
import {
  Add as AddIcon,
  CloudUpload as UploadIcon,
  Storage as CatalogIcon,
} from '@mui/icons-material';
import DatasetCard from '../components/DatasetCard';
import { api, Dataset } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
  </div>
);

const ProviderDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    loadDatasets();
  }, [token]);

  const loadDatasets = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.listDatasets(token);
      // Filter to show only user's datasets
      const myDatasets = data.filter((d) => d.provider_id === user?.sub);
      setDatasets(myDatasets);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (datasetId: string) => {
    if (!token) return;
    try {
      await api.publishDataset(datasetId, token);
      await loadDatasets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish dataset');
    }
  };

  const draftDatasets = datasets.filter((d) => d.visibility === 'draft');
  const privateDatasets = datasets.filter((d) => d.visibility === 'private');
  const publicDatasets = datasets.filter((d) => d.visibility === 'public');

  const getDatasetsByTab = () => {
    switch (tabValue) {
      case 0:
        return datasets;
      case 1:
        return draftDatasets;
      case 2:
        return privateDatasets;
      case 3:
        return publicDatasets;
      default:
        return datasets;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Provider Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your datasets and import from catalogs.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<CatalogIcon />}
            onClick={() => navigate('/catalog')}
          >
            Browse Catalog
          </Button>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => navigate('/upload')}
          >
            Upload Dataset
          </Button>
        </Stack>
      </Box>

      {/* Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{datasets.length}</Typography>
            <Typography variant="body2" color="text.secondary">
              Total Datasets
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="text.secondary">
              {draftDatasets.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Drafts
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="warning.main">
              {privateDatasets.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Private
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="success.main">
              {publicDatasets.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Published
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label={`All (${datasets.length})`} />
          <Tab label={`Drafts (${draftDatasets.length})`} />
          <Tab label={`Private (${privateDatasets.length})`} />
          <Tab label={`Published (${publicDatasets.length})`} />
        </Tabs>
      </Paper>

      {loading && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && getDatasetsByTab().length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No datasets found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {tabValue === 0
              ? "You haven't created any datasets yet."
              : `No datasets in this category.`}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/upload')}
          >
            Create Your First Dataset
          </Button>
        </Paper>
      )}

      <Grid container spacing={3}>
        {getDatasetsByTab().map((dataset) => (
          <Grid item xs={12} sm={6} md={4} key={dataset.id}>
            <DatasetCard
              dataset={dataset}
              isOwner={true}
              onPublish={() => handlePublish(dataset.id)}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default ProviderDashboard;
