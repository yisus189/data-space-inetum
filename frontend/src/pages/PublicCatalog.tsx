import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import DatasetCard from '../components/DatasetCard';
import { api, Dataset } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const PublicCatalog: React.FC = () => {
  const { token } = useAuth();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadDatasets();
  }, [token]);

  const loadDatasets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listDatasets(token);
      setDatasets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const filteredDatasets = datasets.filter(
    (d) =>
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      d.description?.toLowerCase().includes(search.toLowerCase())
  );

  const publicDatasets = filteredDatasets.filter((d) => d.visibility === 'public');

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Public Datasets
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Browse publicly available datasets in the Data Space.
      </Typography>

      <TextField
        fullWidth
        placeholder="Search datasets..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

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

      {!loading && !error && publicDatasets.length === 0 && (
        <Alert severity="info">
          No public datasets available. {search && 'Try a different search term.'}
        </Alert>
      )}

      <Grid container spacing={3}>
        {publicDatasets.map((dataset) => (
          <Grid item xs={12} sm={6} md={4} key={dataset.id}>
            <DatasetCard dataset={dataset} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default PublicCatalog;
