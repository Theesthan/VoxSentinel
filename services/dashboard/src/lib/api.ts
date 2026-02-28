/**
 * VoxSentinel API client.
 *
 * All requests are proxied through nginx at /api/v1/*.
 * Authentication is via Bearer token stored in localStorage.
 */

const BASE = "/api/v1";

// ── Auth helpers ──

export function getApiKey(): string {
  return localStorage.getItem("vox_api_key") ?? "";
}

export function setApiKey(key: string) {
  localStorage.setItem("vox_api_key", key);
}

export function clearApiKey() {
  localStorage.removeItem("vox_api_key");
}

// ── Generic fetch wrapper ──

async function apiFetch<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const key = getApiKey();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${key}`,
    ...(opts.headers as Record<string, string> ?? {}),
  };
  if (opts.body && typeof opts.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (res.status === 204) return undefined as unknown as T;
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text);
  }
  return res.json();
}

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

// ── Types ──

export interface Stream {
  stream_id: string;
  name: string;
  status: string;
  source_type: string;
  source_url?: string;
  asr_backend: string;
  asr_fallback_backend?: string | null;
  language_override?: string | null;
  vad_threshold?: number;
  chunk_size_ms?: number;
  session_id: string | null;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown> | null;
}

export interface StreamListResponse {
  streams: Stream[];
  total: number;
}

export interface StreamCreateRequest {
  name: string;
  source_type: string;
  source_url: string;
  asr_backend?: string;
  asr_fallback_backend?: string | null;
  language_override?: string | null;
  vad_threshold?: number;
  chunk_size_ms?: number;
  metadata?: Record<string, unknown> | null;
}

export interface Rule {
  rule_id: string;
  rule_set_name: string;
  keyword: string;
  match_type: string;
  fuzzy_threshold: number | null;
  severity: string;
  category: string;
  language: string | null;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface RuleListResponse {
  rules: Rule[];
  total: number;
}

export interface RuleCreateRequest {
  rule_set_name: string;
  keyword: string;
  match_type?: string;
  fuzzy_threshold?: number;
  severity?: string;
  category?: string;
  language?: string | null;
  enabled?: boolean;
}

export interface Alert {
  alert_id: string;
  stream_id: string;
  stream_name?: string | null;
  alert_type: string;
  severity: string;
  matched_rule?: string | null;
  match_type?: string | null;
  matched_text?: string | null;
  speaker_id?: string | null;
  surrounding_context?: string | null;
  created_at: string | null;
  delivery_status?: Record<string, string> | null;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
}

export interface AlertChannel {
  channel_id: string;
  channel_type: string;
  config: Record<string, unknown>;
  min_severity: string | null;
  alert_types: string[] | null;
  stream_ids: string[] | null;
  enabled: boolean;
  created_at: string | null;
}

export interface AlertChannelListResponse {
  channels: AlertChannel[];
  total: number;
}

export interface AlertChannelCreateRequest {
  channel_type: string;
  config: Record<string, unknown>;
  min_severity?: string;
  alert_types?: string[];
  stream_ids?: string[] | null;
  enabled?: boolean;
}

export interface SearchHit {
  segment_id: string;
  session_id: string;
  stream_id: string;
  stream_name?: string | null;
  speaker_id?: string | null;
  timestamp: string;
  text: string;
  sentiment_label?: string | null;
  score?: number | null;
}

export interface SearchResponse {
  results: SearchHit[];
  total: number;
}

export interface SearchRequest {
  query: string;
  search_type?: string;
  stream_ids?: string[] | null;
  date_from?: string | null;
  date_to?: string | null;
  speaker_id?: string | null;
  language?: string | null;
  limit?: number;
  offset?: number;
}

export interface TranscriptSegment {
  segment_id: string;
  speaker_id: string | null;
  start_time: string;
  end_time: string;
  text: string;
  sentiment_label: string | null;
  sentiment_score: number | null;
  language: string;
  confidence: number;
}

export interface TranscriptResponse {
  session_id: string;
  segments: TranscriptSegment[];
  total: number;
}

export interface HealthResponse {
  status: string;
  services: Record<string, string>;
}

// ── Health (no auth needed) ──

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch("/health");
  return res.json();
}

// ── Streams ──

export const listStreams = () => apiFetch<StreamListResponse>("/streams");

export const getStream = (id: string) => apiFetch<Stream>(`/streams/${id}`);

export const createStream = (body: StreamCreateRequest) =>
  apiFetch<{ stream_id: string; status: string; session_id: string; created_at: string }>(
    "/streams",
    { method: "POST", body: JSON.stringify(body) },
  );

export const updateStream = (id: string, body: Partial<StreamCreateRequest>) =>
  apiFetch<Stream>(`/streams/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteStream = (id: string) =>
  apiFetch<void>(`/streams/${id}`, { method: "DELETE" });

export const pauseStream = (id: string) =>
  apiFetch<{ status: string }>(`/streams/${id}/pause`, { method: "POST" });

export const resumeStream = (id: string) =>
  apiFetch<{ status: string }>(`/streams/${id}/resume`, { method: "POST" });

// ── Rules ──

export const listRules = (params?: { rule_set_name?: string; category?: string }) => {
  const q = new URLSearchParams();
  if (params?.rule_set_name) q.set("rule_set_name", params.rule_set_name);
  if (params?.category) q.set("category", params.category);
  const qs = q.toString();
  return apiFetch<RuleListResponse>(`/rules${qs ? `?${qs}` : ""}`);
};

export const createRule = (body: RuleCreateRequest) =>
  apiFetch<{ rule_id: string; created_at: string }>("/rules", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updateRule = (id: string, body: Partial<RuleCreateRequest>) =>
  apiFetch<Rule>(`/rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteRule = (id: string) =>
  apiFetch<void>(`/rules/${id}`, { method: "DELETE" });

// ── Alerts ──

export const listAlerts = (params?: {
  stream_id?: string;
  alert_type?: string;
  severity?: string;
  limit?: number;
}) => {
  const q = new URLSearchParams();
  if (params?.stream_id) q.set("stream_id", params.stream_id);
  if (params?.alert_type) q.set("alert_type", params.alert_type);
  if (params?.severity) q.set("severity", params.severity);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<AlertListResponse>(`/alerts${qs ? `?${qs}` : ""}`);
};

// ── Alert Channels ──

export const listAlertChannels = () =>
  apiFetch<AlertChannelListResponse>("/alert-channels");

export const createAlertChannel = (body: AlertChannelCreateRequest) =>
  apiFetch<{ channel_id: string; created_at: string }>("/alert-channels", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updateAlertChannel = (
  id: string,
  body: Partial<AlertChannelCreateRequest>,
) =>
  apiFetch<AlertChannel>(`/alert-channels/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteAlertChannel = (id: string) =>
  apiFetch<void>(`/alert-channels/${id}`, { method: "DELETE" });

// ── Search ──

export const searchTranscripts = (body: SearchRequest) =>
  apiFetch<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(body),
  });

// ── Transcripts ──

export const getTranscript = (sessionId: string) =>
  apiFetch<TranscriptResponse>(`/sessions/${sessionId}/transcript`);

// ── Audit ──

export interface AuditVerifyResponse {
  segment_id: string;
  segment_hash: string;
  anchor_id?: number | null;
  merkle_root?: string | null;
  merkle_proof: { position: string; hash: string }[];
  verified: boolean;
  anchored_at?: string | null;
}

export const verifySegment = (segmentId: string) =>
  apiFetch<AuditVerifyResponse>(`/audit/verify/${segmentId}`);
