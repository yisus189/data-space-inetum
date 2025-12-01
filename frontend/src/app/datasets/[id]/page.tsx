'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  Typography,
  Box,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Download, Public, Lock, Edit } from '@mui/icons-material';
import { DatasetDetail, datasetsApi } from '@/lib/api';
import { useAuthToken } from '@/hooks/useAuth';

export default function DatasetDetailPage() {
  const params = useParams();
  const auth = useAuthToken();
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      loadDataset(params.id as string);
    }
  }, [params.id]);

  const loadDataset = async (id: string) => {
    try {
      setLoading(true);
      const data = await datasetsApi.get(id);
      setDataset(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dataset');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (version?: number) => {
    if (!dataset) return;
    
    try {
      const { download_url } = await datasetsApi.getDownloadUrl(dataset.id, version);
      window.open(download_url, '_blank');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to get download URL');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !dataset) {
    return <Alert severity="error">{error || 'Dataset not found'}</Alert>;
  }

  const visibilityIcon = {
    draft: <Edit fontSize="small" />,
    private: <Lock fontSize="small" />,
    public: <Public fontSize="small" />,
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 3 }}>
        <Box>
          <Typography variant="h3" component="h1" gutterBottom>
            {dataset.title}
          </Typography>
          <Chip
            icon={visibilityIcon[dataset.visibility]}
            label={dataset.visibility}
            color={dataset.visibility === 'public' ? 'success' : 'warning'}
            sx={{ mb: 2 }}
          />
        </Box>
        
        {dataset.visibility === 'public' && auth.isAuthenticated && (
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => handleDownload()}
          >
            Download
          </Button>
        )}
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Description
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            {dataset.description || 'No description provided'}
          </Typography>

          <Typography variant="body2" color="text.secondary">
            <strong>Provider:</strong> {dataset.provider_id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Created by:</strong> {dataset.created_by}
          </Typography>
          {dataset.created_at && (
            <Typography variant="body2" color="text.secondary">
              <strong>Created:</strong> {new Date(dataset.created_at).toLocaleString()}
            </Typography>
          )}
          {dataset.updated_at && (
            <Typography variant="body2" color="text.secondary">
              <strong>Updated:</strong> {new Date(dataset.updated_at).toLocaleString()}
            </Typography>
          )}
        </CardContent>
      </Card>

      {dataset.versions && dataset.versions.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Versions
            </Typography>
          </Box>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Version</TableCell>
                <TableCell>Object Key</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {dataset.versions.map((version) => (
                <TableRow key={version.id}>
                  <TableCell>{version.version}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {version.object_key}
                  </TableCell>
                  <TableCell>
                    {version.size ? `${(version.size / 1024 / 1024).toFixed(2)} MB` : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {version.created_at
                      ? new Date(version.created_at).toLocaleDateString()
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {dataset.visibility === 'public' && auth.isAuthenticated && (
                      <Button
                        size="small"
                        onClick={() => handleDownload(version.version)}
                      >
                        Download
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {dataset.metadata && Object.keys(dataset.metadata).length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Metadata
            </Typography>
            <Box component="pre" sx={{ overflow: 'auto', fontSize: '0.875rem' }}>
              {JSON.stringify(dataset.metadata, null, 2)}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
