import { http } from '../lib/http';
import type {
  ChatQueryRequest,
  ChatQueryResponse,
  DocumentIndexRequest,
  DocumentIndexResponse,
  DocumentListResponse,
  DocumentRead,
  EvalResultRead,
  EvalRunRequest,
  EvalRunResponse,
  HealthResponse,
  ProviderCheckRequest,
  ProviderCheckResponse,
  ProviderSettingsResponse,
  ProviderSettingsUpdateRequest,
  ReadyResponse,
  TraceRead,
  UUID,
} from './contracts';

export interface DocumentUploadPayload {
  title: string;
  file: File;
  metadata?: Record<string, unknown>;
}

export const apiClient = {
  uploadDocument: async (payload: DocumentUploadPayload): Promise<DocumentRead> => {
    const form = new FormData();
    form.append('title', payload.title);
    form.append('file', payload.file);

    if (payload.metadata && Object.keys(payload.metadata).length > 0) {
      form.append('metadata_json', JSON.stringify(payload.metadata));
    }

    const { data } = await http.post<DocumentRead>('/documents', form, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  listDocuments: async (params?: { limit?: number; offset?: number }): Promise<DocumentListResponse> => {
    const { data } = await http.get<DocumentListResponse>('/documents', {
      params,
    });
    return data;
  },

  indexDocument: async (id: UUID, payload: DocumentIndexRequest = {}): Promise<DocumentIndexResponse> => {
    const { data } = await http.post<DocumentIndexResponse>(`/documents/${id}/index`, payload);
    return data;
  },

  chatQuery: async (payload: ChatQueryRequest): Promise<ChatQueryResponse> => {
    const { data } = await http.post<ChatQueryResponse>('/chat/query', payload);
    return data;
  },

  getChatTrace: async (id: UUID): Promise<TraceRead> => {
    const { data } = await http.get<TraceRead>(`/chat/${id}/trace`);
    return data;
  },

  health: async (): Promise<HealthResponse> => {
    const { data } = await http.get<HealthResponse>('/health');
    return data;
  },

  ready: async (): Promise<ReadyResponse> => {
    const { data } = await http.get<ReadyResponse>('/ready');
    return data;
  },

  getProviderSettings: async (): Promise<ProviderSettingsResponse> => {
    const { data } = await http.get<ProviderSettingsResponse>('/settings/providers');
    return data;
  },

  updateProviderSettings: async (
    payload: ProviderSettingsUpdateRequest,
  ): Promise<ProviderSettingsResponse> => {
    const { data } = await http.put<ProviderSettingsResponse>('/settings/providers', payload);
    return data;
  },

  checkProviderConnectivity: async (
    payload: ProviderCheckRequest = { target: 'all' },
  ): Promise<ProviderCheckResponse> => {
    const { data } = await http.post<ProviderCheckResponse>('/settings/providers/check', payload);
    return data;
  },

  runEval: async (payload: EvalRunRequest): Promise<EvalRunResponse> => {
    const { data } = await http.post<EvalRunResponse>('/evals/run', payload);
    return data;
  },

  getEvalResult: async (id: UUID): Promise<EvalResultRead> => {
    const { data } = await http.get<EvalResultRead>(`/evals/${id}`);
    return data;
  },

  getLatestEvalResult: async (): Promise<EvalResultRead> => {
    const { data } = await http.get<EvalResultRead>('/evals/latest');
    return data;
  },
};
