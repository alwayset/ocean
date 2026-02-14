const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

const authHeaders: Record<string, string> = API_KEY
  ? { "X-API-Key": API_KEY }
  : {};

export interface ToolResult {
  id: string;
  provider_domain: string;
  provider_name: string | null;
  name: string;
  description: string;
  protocol: string;
  input_schema: Record<string, unknown> | null;
  endpoint: string | null;
  relevance_score: number;
  reliability: number | null;
  avg_latency_ms: number | null;
}

export interface ToolDetail extends ToolResult {
  output_schema: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  call_count: number;
  created_at: string;
  last_seen: string;
}

export interface DiscoverResponse {
  query: string;
  results: ToolResult[];
  total: number;
}

export interface ToolListResponse {
  tools: ToolResult[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total_tools: number;
  total_providers: number;
  protocols: Record<string, number>;
}

export async function discover(
  intent: string,
  constraints?: Record<string, unknown>,
  limit = 20
): Promise<DiscoverResponse> {
  const res = await fetch(`${API_BASE}/v1/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ intent, constraints, limit }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function listTools(
  page = 1,
  pageSize = 20,
  protocol?: string
): Promise<ToolListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (protocol) params.set("protocol", protocol);
  const res = await fetch(`${API_BASE}/v1/tools?${params}`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getToolDetail(id: string): Promise<ToolDetail> {
  const res = await fetch(`${API_BASE}/v1/tools/${id}`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/v1/stats`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
