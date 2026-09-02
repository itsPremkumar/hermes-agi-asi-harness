const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface Server {
  id: string;
  name: string;
  slug: string;
  description: string;
  author: string;
  github_stars: number;
  downloads: number;
  mcp_transport: string;
  category: string;
  tags: string[];
  health_score: number;
}

export interface ServerListResponse {
  total: number;
  page: number;
  per_page: number;
  servers: Server[];
}

export interface SearchResult {
  total: number;
  page: number;
  per_page: number;
  results: Server[];
  facets: Record<string, any>;
}

export async function searchServers(
  query: string,
  options: { category?: string; transport?: string; sort?: string; page?: number; perPage?: number } = {}
): Promise<SearchResult> {
  const params = new URLSearchParams({ q: query });
  if (options.category) params.set("category", options.category);
  if (options.transport) params.set("transport", options.transport);
  if (options.sort) params.set("sort", options.sort);
  if (options.page) params.set("page", String(options.page));
  if (options.perPage) params.set("per_page", String(options.perPage));

  const resp = await fetch(`${API_BASE}/search?${params}`);
  if (!resp.ok) throw new Error("Search failed");
  return resp.json();
}

export async function listServers(
  options: { page?: number; perPage?: number; category?: string; sort?: string } = {}
): Promise<ServerListResponse> {
  const params = new URLSearchParams();
  if (options.page) params.set("page", String(options.page));
  if (options.perPage) params.set("per_page", String(options.perPage));
  if (options.category) params.set("category", options.category);
  if (options.sort) params.set("sort", options.sort);

  const resp = await fetch(`${API_BASE}/servers?${params}`);
  if (!resp.ok) throw new Error("Failed to fetch servers");
  return resp.json();
}

export async function getServer(serverId: string): Promise<Server> {
  const resp = await fetch(`${API_BASE}/servers/${serverId}`);
  if (!resp.ok) throw new Error("Server not found");
  return resp.json();
}

export async function submitServer(data: {
  name: string;
  description?: string;
  author: string;
  repository_url?: string;
}): Promise<{ id: string; status: string }> {
  const resp = await fetch(`${API_BASE}/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) throw new Error("Submission failed");
  return resp.json();
}
