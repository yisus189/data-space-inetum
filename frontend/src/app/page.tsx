'use client';

import { useEffect, useState } from 'react';
import {
  Typography,
  Grid,
  Box,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { DatasetCard } from '@/components/DatasetCard';
import { Dataset, datasetsApi } from '@/lib/api';
import { useAuthToken } from '@/hooks/useAuth';

export default function HomePage() {
  const auth = useAuthToken();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadDatasets();
  }, []);

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

  const filteredDatasets = datasets.filter((ds) =>
    ds.title.toLowerCase().includes(search.toLowerCase()) ||
    ds.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Box>
      <Typography variant="h3" component="h1" gutterBottom>
        Data Catalog
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Explore available datasets in the Data Space
      </Typography>

      <TextField
        fullWidth
        placeholder="Search datasets..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 4 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
      />

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && filteredDatasets.length === 0 && (
        <Alert severity="info">
          {search ? 'No datasets match your search' : 'No datasets available yet'}
        </Alert>
      )}

      <Grid container spacing={3}>
        {filteredDatasets.map((dataset) => (
          <Grid item xs={12} sm={6} md={4} key={dataset.id}>
            <DatasetCard dataset={dataset} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
