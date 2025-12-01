import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Card,
  CardContent,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  InsertDriveFile as FileIcon,
} from '@mui/icons-material';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface FileWithPreview {
  file: File;
  id: string;
}

const UploadDataset: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  
  const [activeStep, setActiveStep] = useState(0);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [metadata, setMetadata] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const steps = ['Dataset Info', 'Upload Files', 'Review & Submit'];

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const newFiles = Array.from(event.target.files).map((file) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
      }));
      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const handleFileRemove = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    if (event.dataTransfer.files) {
      const newFiles = Array.from(event.dataTransfer.files).map((file) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
      }));
      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
  }, []);

  const handleSubmit = async () => {
    if (!token) {
      setError('Authentication required');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      
      if (metadata.trim()) {
        try {
          JSON.parse(metadata);
          formData.append('metadata', metadata);
        } catch {
          setError('Invalid JSON in metadata field');
          setUploading(false);
          return;
        }
      }

      files.forEach((f) => {
        formData.append('files', f.file);
      });

      await api.createDataset(formData, token);
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create dataset');
    } finally {
      setUploading(false);
    }
  };

  const canProceed = () => {
    switch (activeStep) {
      case 0:
        return title.trim().length > 0;
      case 1:
        return true; // Files are optional
      case 2:
        return true;
      default:
        return false;
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            <TextField
              fullWidth
              label="Dataset Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              margin="normal"
              required
              helperText="Enter a descriptive title for your dataset"
            />
            <TextField
              fullWidth
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              margin="normal"
              multiline
              rows={4}
              helperText="Describe the contents and purpose of this dataset"
            />
            <TextField
              fullWidth
              label="Metadata (JSON)"
              value={metadata}
              onChange={(e) => setMetadata(e.target.value)}
              margin="normal"
              multiline
              rows={3}
              helperText="Optional: Add custom metadata as JSON"
              placeholder='{"tags": ["example"], "schema": {}}'
            />
          </Box>
        );

      case 1:
        return (
          <Box>
            <Card
              variant="outlined"
              sx={{
                p: 4,
                textAlign: 'center',
                border: '2px dashed',
                borderColor: 'primary.main',
                bgcolor: 'action.hover',
                cursor: 'pointer',
                mb: 2,
              }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input
                id="file-input"
                type="file"
                multiple
                hidden
                onChange={handleFileSelect}
              />
              <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6">Drop files here or click to upload</Typography>
              <Typography variant="body2" color="text.secondary">
                Supports all file types
              </Typography>
            </Card>

            {files.length > 0 && (
              <List>
                {files.map((f) => (
                  <ListItem key={f.id}>
                    <FileIcon sx={{ mr: 2, color: 'text.secondary' }} />
                    <ListItemText
                      primary={f.file.name}
                      secondary={`${(f.file.size / 1024).toFixed(1)} KB`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton edge="end" onClick={() => handleFileRemove(f.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}

            {files.length === 0 && (
              <Alert severity="info">
                You can create a dataset without files and add them later.
              </Alert>
            )}
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Review Your Dataset
            </Typography>

            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Title
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {title}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>
                  Description
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {description || 'No description provided'}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>
                  Files
                </Typography>
                <Typography variant="body1">
                  {files.length > 0
                    ? `${files.length} file(s) selected`
                    : 'No files attached'}
                </Typography>

                {metadata && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>
                      Custom Metadata
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        p: 1,
                        bgcolor: 'grey.100',
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        overflow: 'auto',
                      }}
                    >
                      {metadata}
                    </Box>
                  </>
                )}
              </CardContent>
            </Card>

            <Alert severity="info">
              Your dataset will be created as a <strong>draft</strong>. You can publish
              it later from your dashboard.
            </Alert>
          </Box>
        );

      default:
        return null;
    }
  };

  if (success) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5" color="success.main" gutterBottom>
          Dataset Created Successfully!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Redirecting to dashboard...
        </Typography>
        <CircularProgress sx={{ mt: 2 }} />
      </Paper>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Upload Dataset
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Create a new dataset by providing information and uploading files.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {renderStepContent()}

        <Box display="flex" justifyContent="space-between" mt={4}>
          <Button
            disabled={activeStep === 0}
            onClick={() => setActiveStep((prev) => prev - 1)}
          >
            Back
          </Button>
          <Box>
            <Button onClick={() => navigate('/dashboard')} sx={{ mr: 1 }}>
              Cancel
            </Button>
            {activeStep === steps.length - 1 ? (
              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={uploading || !canProceed()}
                startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
              >
                {uploading ? 'Creating...' : 'Create Dataset'}
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={() => setActiveStep((prev) => prev + 1)}
                disabled={!canProceed()}
              >
                Next
              </Button>
            )}
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default UploadDataset;
