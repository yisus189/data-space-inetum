const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  token?: string | null;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

// Dataset types
export interface Dataset {
  id: string;
  title: string;
  description?: string;
  provider_id: string;
  provider_name?: string;
  visibility: string;
  external_source?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  published_at?: string;
  versions?: DatasetVersion[];
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version_number: number;
  object_key: string;
  filename?: string;
  content_type?: string;
  size_bytes?: number;
  created_at: string;
}

export interface CatalogEntity {
  id: string;
  name: string;
  fqn?: string;
  display_name?: string;
  description?: string;
  entity_type: string;
  owner?: string;
  tags: string[];
  metadata?: Record<string, unknown>;
}

// API functions
export const api = {
  // Datasets
  listDatasets: (token?: string | null) =>
    apiRequest<Dataset[]>('/datasets', { token }),

  getDataset: (id: string, token?: string | null) =>
    apiRequest<Dataset>(`/datasets/${id}`, { token }),

  createDataset: async (
    data: FormData,
    token: string
  ): Promise<Dataset> => {
    const response = await fetch(`${API_URL}/datasets`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: data,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Create failed' }));
      throw new Error(error.detail || `HTTP error ${response.status}`);
    }

    return response.json();
  },

  publishDataset: (id: string, token: string) =>
    apiRequest<Dataset>(`/datasets/${id}/publish`, {
      method: 'POST',
      token,
    }),

  getDownloadUrl: (id: string, token?: string | null) =>
    apiRequest<{ download_url: string; filename: string }>(
      `/datasets/${id}/download`,
      { token }
    ),

  deleteDataset: (id: string, token: string) =>
    apiRequest<void>(`/datasets/${id}`, { method: 'DELETE', token }),

  // Catalog (OpenMetadata)
  listCatalog: (token: string, search?: string) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    return apiRequest<CatalogEntity[]>(
      `/integrations/openmetadata/catalog?${params}`,
      { token }
    );
  },

  getCatalogEntity: (id: string, token: string) =>
    apiRequest<{ entity: unknown; dataset_metadata: unknown }>(
      `/integrations/openmetadata/entities/${id}`,
      { token }
    ),

  importFromCatalog: (
    entityId: string,
    takeData: boolean,
    token: string
  ) =>
    apiRequest<{ dataset_id: string; message: string }>(
      '/integrations/openmetadata/import',
      {
        method: 'POST',
        token,
        body: JSON.stringify({
          entity_id: entityId,
          take_data: takeData,
        }),
      }
    ),

  // Storage
  getPresignedUploadUrl: (
    filename: string,
    contentType: string,
    token: string
  ) =>
    apiRequest<{ upload_url: string; object_key: string }>(
      '/storage/presign',
      {
        method: 'POST',
        token,
        body: JSON.stringify({
          filename,
          content_type: contentType,
        }),
      }
    ),

  // Health
  healthCheck: () => apiRequest<{ status: string }>('/health'),
};

export default api;
