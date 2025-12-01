import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
});

// Add auth token to requests
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Dataset types
export interface Dataset {
  id: string;
  title: string;
  description: string;
  visibility: 'draft' | 'private' | 'public';
  created_at?: string;
  metadata?: any;
}

export interface DatasetDetail extends Dataset {
  provider_id: string;
  created_by: string;
  updated_at?: string;
  versions: DatasetVersion[];
}

export interface DatasetVersion {
  id: string;
  version: number;
  object_key: string;
  size?: number;
  checksum?: string;
  created_at?: string;
}

// OpenMetadata types
export interface CatalogItem {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  type?: string;
  service?: string;
  database?: string;
  tags?: string[];
}

// API functions
export const datasetsApi = {
  list: async (): Promise<Dataset[]> => {
    const response = await api.get('/datasets');
    return response.data;
  },

  get: async (id: string): Promise<DatasetDetail> => {
    const response = await api.get(`/datasets/${id}`);
    return response.data;
  },

  create: async (data: FormData): Promise<Dataset> => {
    const response = await api.post('/datasets', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  requestUploadUrl: async (data: {
    title: string;
    description: string;
    filename: string;
    content_type: string;
  }): Promise<{ upload_url: string; object_key: string; expires_in: number }> => {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      formData.append(key, value);
    });
    const response = await api.post('/datasets/upload-request', formData);
    return response.data;
  },

  publish: async (id: string): Promise<Dataset> => {
    const response = await api.post(`/datasets/${id}/publish`);
    return response.data;
  },

  getDownloadUrl: async (id: string, version?: number): Promise<{ download_url: string }> => {
    const response = await api.get(`/datasets/${id}/download`, {
      params: version ? { version } : {},
    });
    return response.data;
  },
};

export const openmetadataApi = {
  getCatalog: async (query?: string, page = 1, limit = 20): Promise<{
    items: CatalogItem[];
    total: number;
    page: number;
    limit: number;
  }> => {
    const response = await api.get('/integrations/openmetadata/catalog', {
      params: { query, page, limit },
    });
    return response.data;
  },

  getEntity: async (entityId: string): Promise<any> => {
    const response = await api.get(`/integrations/openmetadata/entities/${entityId}`);
    return response.data;
  },

  importEntity: async (entityId: string, takeData: boolean): Promise<any> => {
    const response = await api.post('/integrations/openmetadata/import', {
      entity_id: entityId,
      take_data: takeData,
    });
    return response.data;
  },
};
