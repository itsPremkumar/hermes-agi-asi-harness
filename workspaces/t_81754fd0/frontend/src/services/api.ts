const API_BASE = '/api/v1';

export async function generateUI(description: string, framework: string) {
  const resp = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description, framework }),
  });
  if (!resp.ok) throw new Error(`Generation failed: ${resp.statusText}`);
  return resp.json();
}

export async function exportUI(generationId: string, framework: string, minify = false) {
  const resp = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ generation_id: generationId, framework, minify }),
  });
  if (!resp.ok) throw new Error(`Export failed: ${resp.statusText}`);
  return resp.json();
}

export async function fetchComponents(category = '', search = '', limit = 50) {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (search) params.set('search', search);
  params.set('limit', String(limit));

  const resp = await fetch(`${API_BASE}/components?${params}`);
  if (!resp.ok) throw new Error(`Failed to fetch components: ${resp.statusText}`);
  return resp.json();
}

export async function fetchCategories() {
  const resp = await fetch(`${API_BASE}/categories`);
  if (!resp.ok) throw new Error(`Failed to fetch categories: ${resp.statusText}`);
  return resp.json();
}
