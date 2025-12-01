import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  TextField,
  InputAdornment,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Stack,
} from '@mui/material';
import {
  Search as SearchIcon,
  Download as ImportIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { api, CatalogEntity } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const CatalogBrowser: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  
  const [entities, setEntities] = useState<CatalogEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  
  // Import dialog
  const [importDialog, setImportDialog] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<CatalogEntity | null>(null);
  const [takeData, setTakeData] = useState(false);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    loadCatalog();
  }, [token]);

  const loadCatalog = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.listCatalog(token, search || undefined);
      setEntities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadCatalog();
  };

  const openImportDialog = (entity: CatalogEntity) => {
    setSelectedEntity(entity);
    setTakeData(false);
    setImportDialog(true);
  };

  const handleImport = async () => {
    if (!token || !selectedEntity) return;
    
    try {
      setImporting(true);
      const result = await api.importFromCatalog(selectedEntity.id, takeData, token);
      setImportDialog(false);
      // Navigate to the new dataset
      navigate(`/datasets/${result.dataset_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import entity');
    } finally {
      setImporting(false);
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            OpenMetadata Catalog
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Browse and import entities from the connected OpenMetadata catalog.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadCatalog}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      <Box display="flex" gap={2} mb={3}>
        <TextField
          fullWidth
          placeholder="Search catalog..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Button variant="contained" onClick={handleSearch}>
          Search
        </Button>
      </Box>

      {loading && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!loading && !error && entities.length === 0 && (
        <Alert severity="info">
          No entities found in the catalog.
          {search && ' Try a different search term or clear the search.'}
        </Alert>
      )}

      <Grid container spacing={3}>
        {entities.map((entity) => (
          <Grid item xs={12} sm={6} md={4} key={entity.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" gutterBottom noWrap>
                  {entity.display_name || entity.name}
                </Typography>
                
                {entity.fqn && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                    sx={{ mb: 1, fontFamily: 'monospace' }}
                    noWrap
                  >
                    {entity.fqn}
                  </Typography>
                )}
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>
                  {entity.description || 'No description available'}
                </Typography>
                
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  <Chip label={entity.entity_type} size="small" color="primary" variant="outlined" />
                  {entity.owner && (
                    <Chip label={`Owner: ${entity.owner}`} size="small" variant="outlined" />
                  )}
                  {entity.tags.slice(0, 3).map((tag, idx) => (
                    <Chip key={idx} label={tag} size="small" variant="outlined" />
                  ))}
                  {entity.tags.length > 3 && (
                    <Chip label={`+${entity.tags.length - 3} more`} size="small" />
                  )}
                </Stack>
              </CardContent>
              
              <CardActions>
                <Button
                  size="small"
                  startIcon={<ImportIcon />}
                  onClick={() => openImportDialog(entity)}
                >
                  Import
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Import Dialog */}
      <Dialog open={importDialog} onClose={() => !importing && setImportDialog(false)}>
        <DialogTitle>Import Entity</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Import <strong>{selectedEntity?.display_name || selectedEntity?.name}</strong> as a
            new dataset in your Data Space.
          </DialogContentText>
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={takeData}
                  onChange={(e) => setTakeData(e.target.checked)}
                />
              }
              label="Copy data to storage (if available)"
            />
            <Typography variant="caption" color="text.secondary" display="block" sx={{ ml: 4 }}>
              When enabled, the data will be copied to MinIO storage. Otherwise, only metadata
              will be imported.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportDialog(false)} disabled={importing}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleImport}
            disabled={importing}
            startIcon={importing ? <CircularProgress size={20} /> : <ImportIcon />}
          >
            {importing ? 'Importing...' : 'Import'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CatalogBrowser;
