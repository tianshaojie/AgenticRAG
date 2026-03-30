import { http } from '../lib/http';
import type {
  ChatQueryRequest,
  ChatQueryResponse,
  DocumentCreateRequest,
  DocumentIndexRequest,
  DocumentIndexResponse,
  DocumentListResponse,
  DocumentRead,
  EvalResultRead,
  EvalRunRequest,
  EvalRunResponse,
  HealthResponse,
  ReadyResponse,
  TraceRead,
  UUID,
} from './contracts';

export const apiClient = {
  createDocument: async (payload: DocumentCreateRequest): Promise<DocumentRead> => {
    const { data } = await http.post<DocumentRead>('/documents', payload);
    return data;
  },

  listDocuments: async (): Promise<DocumentListResponse> => {
    const { data } = await http.get<DocumentListResponse>('/documents');
    return data;
  },

  indexDocument: async (id: UUID, payload: DocumentIndexRequest): Promise<DocumentIndexResponse> => {
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

  runEval: async (payload: EvalRunRequest): Promise<EvalRunResponse> => {
    const { data } = await http.post<EvalRunResponse>('/evals/run', payload);
    return data;
  },

  getEval: async (id: UUID): Promise<EvalResultRead> => {
    const { data } = await http.get<EvalResultRead>(`/evals/${id}`);
    return data;
  },
};
