import { useEffect, useState } from 'react';
import { Button, DashboardShell, Sidebar } from '@automatizaesto/ui';
import { AuthProvider, useAuth } from './lib/auth';
import { api } from './lib/api';
import type { Inspeccion } from './types';
import { Login } from './screens/Login';
import { Dashboard } from './screens/Dashboard';
import { Inspecciones } from './screens/Inspecciones';

type Vista = 'gerencia' | 'inspecciones';

const TITULOS: Record<Vista, [string, string]> = {
  gerencia: ['Panel del gerente', 'Extrae la información por período de ingreso'],
  inspecciones: ['Inspecciones', 'Todos los reportes de auditoría guardados'],
};

function AppInterna() {
  const { loading, email, esAdmin, signOut } = useAuth();
  const [vista, setVista] = useState<Vista>('gerencia');
  const [data, setData] = useState<Inspeccion[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    api<{ inspecciones: Inspeccion[] }>('/api/inspecciones')
      .then((r) => setData(r.inspecciones ?? []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Error al cargar.'));
  }, [email]);

  if (loading) {
    return <div className="grid min-h-screen place-items-center text-ink-mute">Cargando…</div>;
  }
  if (!email) return <Login />;

  const [titulo, sub] = TITULOS[vista];

  return (
    <DashboardShell
      sidebar={
        <Sidebar
          brand={{ mark: 'λ', name: 'AgroQuality', tagline: 'Calidad post-cosecha' }}
          items={[
            { key: 'gerencia', label: 'Panel' },
            { key: 'inspecciones', label: 'Inspecciones' },
          ]}
          activeKey={vista}
          onSelect={(k) => setVista(k as Vista)}
          footer={{ who: email, mode: esAdmin ? 'Admin' : 'Analista' }}
        />
      }
      topbar={
        <>
          <div>
            <b className="font-display text-lg text-ink">{titulo}</b>
            <div className="text-xs text-ink-mute">{sub}</div>
          </div>
          <Button variant="ghost" size="sm" onClick={signOut}>
            Cerrar sesión
          </Button>
        </>
      }
    >
      {error && (
        <div className="mb-4 rounded-sm border border-danger bg-danger-bg px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}
      {vista === 'gerencia' ? <Dashboard data={data} /> : <Inspecciones data={data} />}
    </DashboardShell>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppInterna />
    </AuthProvider>
  );
}
