/**
 * VoxSentinel API client.
 *
 * In dev, requests are proxied through Vite at /api/v1/*.
 * In production, set VITE_API_BASE_URL to the backend URL
 * (e.g. https://your-tunnel.trycloudflare.com)
 */

const BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : "/api/v1";

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
  keyword_rule_set_names?: string[];
  alert_channel_ids?: string[];
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

export const listStreams = (params?: { exclude_source_type?: string }) => {
  const q = new URLSearchParams();
  if (params?.exclude_source_type) q.set("exclude_source_type", params.exclude_source_type);
  const qs = q.toString();
  return apiFetch<StreamListResponse>(`/streams${qs ? `?${qs}` : ""}`);
};

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

// ── File Analyze ──

export interface FileAnalyzeKeywordHit {
  keyword: string;
  match_type: string;
  severity: string;
}

export interface FileAnalyzeSegment {
  segment_id: string;
  speaker_id: string | null;
  start_offset_ms: number;
  end_offset_ms: number;
  text: string;
  sentiment_label: string | null;
  sentiment_score: number | null;
  confidence: number;
  keywords_matched: FileAnalyzeKeywordHit[];
}

export interface FileAnalyzeAlert {
  alert_id: string;
  alert_type: string;
  severity: string;
  matched_rule: string | null;
  match_type: string | null;
  matched_text: string | null;
  speaker_id: string | null;
  surrounding_context: string | null;
  timestamp_offset_ms: number;
}

export interface FileAnalyzeSummary {
  total_segments: number;
  total_alerts: number;
  sentiments: Record<string, number>;
  speakers_detected: number;
  languages_detected: string[];
}

export interface FileAnalyzeSubmitResponse {
  job_id: string;
  stream_id: string;
  session_id: string;
  status: string;
  file_name: string;
  created_at: string;
}

export interface FileAnalyzeStatusResponse {
  job_id: string;
  status: string;
  progress_pct: number;
  file_name: string;
  stream_id: string | null;
  session_id: string | null;
  duration_seconds: number | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  transcript: FileAnalyzeSegment[];
  alerts: FileAnalyzeAlert[];
  summary: FileAnalyzeSummary | null;
}

export interface FileAnalyzeJobSummary {
  job_id: string;
  status: string;
  file_name: string;
  duration_seconds: number | null;
  total_alerts: number;
  created_at: string;
  completed_at: string | null;
}

export interface FileAnalyzeListResponse {
  jobs: FileAnalyzeJobSummary[];
  total: number;
}

export async function submitFileForAnalysis(
  file: File,
  opts?: { name?: string; asr_backend?: string; keyword_rule_sets?: string },
): Promise<FileAnalyzeSubmitResponse> {
  const form = new FormData();
  form.append("file", file);
  if (opts?.name) form.append("name", opts.name);
  if (opts?.asr_backend) form.append("asr_backend", opts.asr_backend);
  if (opts?.keyword_rule_sets) form.append("keyword_rule_sets", opts.keyword_rule_sets);

  const key = getApiKey();
  const res = await fetch(`${BASE}/file-analyze`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}` },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text);
  }
  return res.json();
}

export const getFileAnalyzeJob = (jobId: string) =>
  apiFetch<FileAnalyzeStatusResponse>(`/file-analyze/${jobId}`);

export const listFileAnalyzeJobs = (params?: { status?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<FileAnalyzeListResponse>(`/file-analyze${qs ? `?${qs}` : ""}`);
};

// ── WebSocket helpers ──

export function createTranscriptSocket(streamId: string): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${proto}//${window.location.host}/ws/streams/${streamId}/transcript`);
}

export function createAlertSocket(): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${proto}//${window.location.host}/ws/alerts`);
}

export function createMicSocket(): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${proto}//${window.location.host}/ws/mic`);
}

// ── YouTube ──

export interface YouTubeResolveResponse {
  is_live: boolean;
  title: string;
  hls_url: string | null;
  message: string;
}

export const resolveYouTubeUrl = (url: string) =>
  apiFetch<YouTubeResolveResponse>("/youtube/resolve", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

export const youtubeDownloadAnalyze = (url: string) =>
  apiFetch<FileAnalyzeSubmitResponse>("/youtube/download-analyze", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
