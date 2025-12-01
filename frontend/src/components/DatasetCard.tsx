'use client';

import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
} from '@mui/material';
import { Dataset } from '@/lib/api';
import Link from 'next/link';
import { Visibility, Public, Lock, Edit } from '@mui/icons-material';

interface DatasetCardProps {
  dataset: Dataset;
  onPublish?: (id: string) => void;
  showActions?: boolean;
}

export function DatasetCard({ dataset, onPublish, showActions }: DatasetCardProps) {
  const visibilityIcon = {
    draft: <Edit fontSize="small" />,
    private: <Lock fontSize="small" />,
    public: <Public fontSize="small" />,
  };

  const visibilityColor = {
    draft: 'warning',
    private: 'secondary',
    public: 'success',
  } as const;

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
          <Typography variant="h6" component="h3" gutterBottom>
            {dataset.title}
          </Typography>
          <Chip
            icon={visibilityIcon[dataset.visibility]}
            label={dataset.visibility}
            color={visibilityColor[dataset.visibility]}
            size="small"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {dataset.description || 'No description'}
        </Typography>

        {dataset.created_at && (
          <Typography variant="caption" color="text.secondary">
            Created: {new Date(dataset.created_at).toLocaleDateString()}
          </Typography>
        )}
      </CardContent>

      <CardActions>
        <Button
          size="small"
          component={Link}
          href={`/datasets/${dataset.id}`}
          startIcon={<Visibility />}
        >
          View Details
        </Button>

        {showActions && dataset.visibility === 'draft' && onPublish && (
          <Button
            size="small"
            color="primary"
            onClick={() => onPublish(dataset.id)}
          >
            Publish
          </Button>
        )}
      </CardActions>
    </Card>
  );
}
