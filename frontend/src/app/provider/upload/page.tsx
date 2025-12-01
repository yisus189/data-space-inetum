'use client';

import { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Alert,
  LinearProgress,
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { datasetsApi } from '@/lib/api';
import { useAuthToken } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const auth = useAuthToken();
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title) {
      setError('Title is required');
      return;
    }

    if (!file) {
      setError('File is required');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      // Create FormData for upload
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      formData.append('file', file);

      // Upload dataset
      await datasetsApi.create(formData);

      setSuccess(true);
      setTimeout(() => {
        router.push('/provider/dashboard');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload dataset');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFile(files[0]);
    }
  };

  if (!auth.isAuthenticated) {
    return (
      <Alert severity="warning">
        Please login as a provider to upload datasets.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h3" component="h1" gutterBottom>
        Upload Dataset
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Upload a new dataset to the Data Space
      </Typography>

      <Card sx={{ maxWidth: 800, mx: 'auto' }}>
        <CardContent>
          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              label="Title"
              fullWidth
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              sx={{ mb: 2 }}
              disabled={uploading}
            />

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              sx={{ mb: 2 }}
              disabled={uploading}
            />

            <Box sx={{ mb: 2 }}>
              <input
                accept="*/*"
                style={{ display: 'none' }}
                id="file-upload"
                type="file"
                onChange={handleFileChange}
                disabled={uploading}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<CloudUpload />}
                  disabled={uploading}
                  fullWidth
                >
                  {file ? file.name : 'Choose File'}
                </Button>
              </label>
            </Box>

            {uploading && <LinearProgress sx={{ mb: 2 }} />}

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 2 }}>
                Dataset uploaded successfully! Redirecting...
              </Alert>
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={() => router.back()}
                disabled={uploading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={uploading || !title || !file}
                startIcon={<CloudUpload />}
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
