import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Stack,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Download as DownloadIcon,
  Publish as PublishIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { api, Dataset } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const DatasetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token, user, isAuthenticated } = useAuth();
  
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const isOwner = isAuthenticated && user?.sub === dataset?.provider_id;

  useEffect(() => {
    if (id) {
      loadDataset();
    }
  }, [id, token]);

  const loadDataset = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDataset(id, token);
      setDataset(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dataset');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!id) return;
    try {
      setDownloading(true);
      const { download_url } = await api.getDownloadUrl(id, token);
      window.open(download_url, '_blank');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get download URL');
    } finally {
      setDownloading(false);
    }
  };

  const handlePublish = async () => {
    if (!id || !token) return;
    try {
      setPublishing(true);
      await api.publishDataset(id, token);
      await loadDataset();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish dataset');
    } finally {
      setPublishing(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Button startIcon={<BackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
          Back
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!dataset) {
    return (
      <Box>
        <Button startIcon={<BackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
          Back
        </Button>
        <Alert severity="warning">Dataset not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Button startIcon={<BackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Back
      </Button>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {dataset.title}
            </Typography>
            <Stack direction="row" spacing={1} mb={2}>
              <Chip
                label={dataset.visibility}
                color={dataset.visibility === 'public' ? 'success' : 'default'}
                size="small"
              />
              {dataset.external_source && (
                <Chip label="Imported from OpenMetadata" size="small" color="info" />
              )}
              {isOwner && <Chip label="You own this dataset" size="small" color="primary" />}
            </Stack>
          </Box>
          <Stack direction="row" spacing={1}>
            {dataset.visibility === 'public' && dataset.versions && dataset.versions.length > 0 && (
              <Button
                variant="contained"
                startIcon={<DownloadIcon />}
                onClick={handleDownload}
                disabled={downloading}
              >
                {downloading ? 'Getting URL...' : 'Download'}
              </Button>
            )}
            {isOwner && dataset.visibility !== 'public' && (
              <Button
                variant="contained"
                color="success"
                startIcon={<PublishIcon />}
                onClick={handlePublish}
                disabled={publishing}
              >
                {publishing ? 'Publishing...' : 'Publish'}
              </Button>
            )}
          </Stack>
        </Box>

        <Typography variant="body1" paragraph>
          {dataset.description || 'No description available'}
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Details
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Provider
            </Typography>
            <Typography variant="body2">{dataset.provider_name || dataset.provider_id}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Created
            </Typography>
            <Typography variant="body2">
              {new Date(dataset.created_at).toLocaleString()}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Updated
            </Typography>
            <Typography variant="body2">
              {new Date(dataset.updated_at).toLocaleString()}
            </Typography>
          </Box>
          {dataset.published_at && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                Published
              </Typography>
              <Typography variant="body2">
                {new Date(dataset.published_at).toLocaleString()}
              </Typography>
            </Box>
          )}
        </Box>

        {dataset.external_source && (
          <Box mt={2}>
            <Typography variant="caption" color="text.secondary">
              External Source
            </Typography>
            <Box display="flex" alignItems="center">
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                {dataset.external_source}
              </Typography>
              <Tooltip title="Copy">
                <IconButton size="small" onClick={() => copyToClipboard(dataset.external_source!)}>
                  <CopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        )}
      </Paper>

      {/* Versions */}
      {dataset.versions && dataset.versions.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Files ({dataset.versions.length})
          </Typography>
          <Stack spacing={2}>
            {dataset.versions.map((version) => (
              <Card key={version.id} variant="outlined">
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="body1">
                        {version.filename || `Version ${version.version_number}`}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {version.content_type} • {version.size_bytes ? `${(version.size_bytes / 1024).toFixed(1)} KB` : 'Unknown size'}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(version.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </Paper>
      )}

      {/* Metadata */}
      {dataset.metadata && Object.keys(dataset.metadata).length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Metadata
          </Typography>
          <Box
            component="pre"
            sx={{
              p: 2,
              bgcolor: 'grey.100',
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.875rem',
            }}
          >
            {JSON.stringify(dataset.metadata, null, 2)}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default DatasetDetail;
