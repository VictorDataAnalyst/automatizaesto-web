// Cliente de la API FastAPI existente. El token (JWT de Supabase) se inyecta
// vía setToken() desde el contexto de auth.
let TOKEN: string | null = null;

export function setToken(t: string | null) {
  TOKEN = t;
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (TOKEN) headers['Authorization'] = 'Bearer ' + TOKEN;
  const r = await fetch(path, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) throw new Error((await r.text()) || 'HTTP ' + r.status);
  const ct = r.headers.get('content-type') ?? '';
  return (ct.includes('json') ? r.json() : r.text()) as Promise<T>;
}

export async function fotoUrl(ref: string): Promise<string> {
  const r = await api<{ url: string }>('/api/fotos-url?ref=' + encodeURIComponent(ref));
  return r.url;
}

export interface FotoSubida {
  ref: string;
  tipo: string;
  url: string;
}

// Subida multipart (no usa api(): el Content-Type lo fija el navegador con el boundary).
export async function uploadFoto(file: File, tipo: string): Promise<FotoSubida> {
  const fd = new FormData();
  fd.append('archivo', file);
  fd.append('tipo', tipo);
  const headers: Record<string, string> = {};
  if (TOKEN) headers['Authorization'] = 'Bearer ' + TOKEN;
  const r = await fetch('/api/fotos', { method: 'POST', headers, body: fd });
  if (!r.ok) throw new Error((await r.text()) || 'No se pudo subir la foto.');
  return r.json();
}

export interface PublicConfig {
  modo: string;
  supabase_url: string | null;
  supabase_anon_key: string | null;
}

export function getConfig(): Promise<PublicConfig> {
  return fetch('/api/config').then((r) => r.json());
}
