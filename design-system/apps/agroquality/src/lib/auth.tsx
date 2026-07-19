import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { getConfig, setToken } from './api';

interface AuthState {
  loading: boolean;
  /** null = no configurado (no se pudo cargar /api/config). */
  ready: boolean;
  email: string | null;
  esAdmin: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth fuera de <AuthProvider>');
  return v;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [supa, setSupa] = useState<SupabaseClient | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [esAdmin, setEsAdmin] = useState(false);

  // Bootstrap: carga config, inicializa Supabase y reanuda sesión si existe.
  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const cfg = await getConfig();
        if (cfg.supabase_url && cfg.supabase_anon_key) {
          const client = createClient(cfg.supabase_url, cfg.supabase_anon_key);
          if (!activo) return;
          setSupa(client);
          setReady(true);
          const { data } = await client.auth.getSession();
          if (data.session) await aplicarSesion(client, data.session.access_token, data.session.user.email ?? null);
        }
      } catch {
        // backend caído o sin configurar: mostramos login igualmente.
        setReady(false);
      } finally {
        if (activo) setLoading(false);
      }
    })();
    return () => { activo = false; };
  }, []);

  async function aplicarSesion(_client: SupabaseClient, token: string, mail: string | null) {
    setToken(token);
    setEmail(mail);
    try {
      const st = await fetch('/api/estado', { headers: { Authorization: 'Bearer ' + token } }).then((r) => r.json());
      setEsAdmin(!!st.es_admin);
    } catch {
      setEsAdmin(false);
    }
  }

  async function signIn(mail: string, password: string) {
    if (!supa) throw new Error('Servicio de acceso no disponible (backend sin conexión).');
    const { data, error } = await supa.auth.signInWithPassword({ email: mail, password });
    if (error) throw new Error(error.message);
    await aplicarSesion(supa, data.session!.access_token, data.user?.email ?? null);
  }

  async function signOut() {
    await supa?.auth.signOut();
    setToken(null);
    setEmail(null);
    setEsAdmin(false);
  }

  return (
    <Ctx.Provider value={{ loading, ready, email, esAdmin, signIn, signOut }}>
      {children}
    </Ctx.Provider>
  );
}
