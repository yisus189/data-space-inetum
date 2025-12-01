'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  FormControlLabel,
  Checkbox,
  Box,
  Alert,
} from '@mui/material';
import { CatalogItem, openmetadataApi } from '@/lib/api';

interface ImportModalProps {
  open: boolean;
  onClose: () => void;
  item: CatalogItem | null;
  onSuccess?: () => void;
}

export function ImportModal({ open, onClose, item, onSuccess }: ImportModalProps) {
  const [takeData, setTakeData] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!item) return;

    setLoading(true);
    setError(null);

    try {
      await openmetadataApi.importEntity(item.id, takeData);
      onSuccess?.();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to import dataset');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Import from OpenMetadata</DialogTitle>
      <DialogContent>
        {item && (
          <Box sx={{ mb: 2 }}>
            <TextField
              label="Name"
              value={item.display_name || item.name}
              fullWidth
              margin="normal"
              InputProps={{ readOnly: true }}
            />
            <TextField
              label="Description"
              value={item.description || 'N/A'}
              fullWidth
              margin="normal"
              multiline
              rows={2}
              InputProps={{ readOnly: true }}
            />
            <TextField
              label="Service"
              value={item.service || 'N/A'}
              fullWidth
              margin="normal"
              InputProps={{ readOnly: true }}
            />
          </Box>
        )}

        <FormControl fullWidth>
          <FormControlLabel
            control={
              <Checkbox
                checked={takeData}
                onChange={(e) => setTakeData(e.target.checked)}
              />
            }
            label="Copy data to MinIO (creates background job)"
          />
        </FormControl>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleImport}
          variant="contained"
          disabled={loading || !item}
        >
          {loading ? 'Importing...' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
