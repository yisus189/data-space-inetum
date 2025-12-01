import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  Stack,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Lock as LockIcon,
  Edit as EditIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { Dataset } from '../services/api';

interface DatasetCardProps {
  dataset: Dataset;
  isOwner?: boolean;
  onPublish?: () => void;
}

const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, isOwner, onPublish }) => {
  const navigate = useNavigate();

  const getVisibilityChip = () => {
    switch (dataset.visibility) {
      case 'public':
        return <Chip label="Public" color="success" size="small" icon={<VisibilityIcon />} />;
      case 'private':
        return <Chip label="Private" color="warning" size="small" icon={<LockIcon />} />;
      case 'draft':
        return <Chip label="Draft" color="default" size="small" icon={<EditIcon />} />;
      default:
        return null;
    }
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
          <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
            {dataset.title}
          </Typography>
          {getVisibilityChip()}
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>
          {dataset.description || 'No description available'}
        </Typography>
        
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {dataset.provider_name && (
            <Chip 
              label={`By: ${dataset.provider_name}`} 
              size="small" 
              variant="outlined" 
            />
          )}
          {dataset.external_source && (
            <Chip 
              label="Imported" 
              size="small" 
              color="info" 
              variant="outlined" 
            />
          )}
          {dataset.versions && dataset.versions.length > 0 && (
            <Chip 
              label={`${dataset.versions.length} file(s)`} 
              size="small" 
              variant="outlined" 
            />
          )}
        </Stack>
        
        <Typography variant="caption" color="text.secondary" display="block" mt={2}>
          Created: {new Date(dataset.created_at).toLocaleDateString()}
          {dataset.published_at && (
            <> | Published: {new Date(dataset.published_at).toLocaleDateString()}</>
          )}
        </Typography>
      </CardContent>
      
      <CardActions>
        <Button size="small" onClick={() => navigate(`/datasets/${dataset.id}`)}>
          View Details
        </Button>
        {dataset.visibility === 'public' && (
          <Button size="small" startIcon={<DownloadIcon />}>
            Download
          </Button>
        )}
        {isOwner && dataset.visibility !== 'public' && onPublish && (
          <Button size="small" color="primary" onClick={onPublish}>
            Publish
          </Button>
        )}
      </CardActions>
    </Card>
  );
};

export default DatasetCard;
