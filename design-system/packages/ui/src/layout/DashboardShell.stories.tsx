import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { DashboardShell } from './DashboardShell';
import { Sidebar } from './Sidebar';
import { KpiCard } from '../data/KpiCard';
import { Table } from '../data/Table';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';

type Row = { codigo: string; nombre: string; estado: 'good' | 'fair' | 'poor' };

interface AppConfig {
  mark: string;
  name: string;
  tagline: string;
  role: string;
  cta: string;
  nav: string[];
  kpis: { label: string; value: string; unit?: string; delta: { value: string; direction: 'up' | 'down' } }[];
  colLabel: string;
  rows: Row[];
}

/** Cada producto tiene su marca y contenido; el tema aporta la paleta.
 *  Derivamos el contenido del tema activo para que la demo sea coherente. */
const APPS: Record<string, AppConfig> = {
  corporate: {
    mark: 'A',
    name: 'Automatizaesto',
    tagline: 'Plataforma',
    role: 'Admin',
    cta: 'Nuevo flujo',
    nav: ['Panel', 'Productos', 'Clientes', 'Facturación'],
    kpis: [
      { label: 'Productos activos', value: '3', delta: { value: '+1', direction: 'up' } },
      { label: 'Clientes', value: '12', delta: { value: '+2', direction: 'up' } },
      { label: 'MRR', value: 'S/ 8.4k', delta: { value: '+6%', direction: 'up' } },
    ],
    colLabel: 'Producto',
    rows: [
      { codigo: 'PRD-01', nombre: 'AgroQuality', estado: 'good' },
      { codigo: 'PRD-02', nombre: 'Forecast', estado: 'good' },
    ],
  },
  forecast: {
    mark: 'ƒ',
    name: 'Forecast',
    tagline: 'Pronóstico de demanda',
    role: 'Analista',
    cta: 'Nuevo pronóstico',
    nav: ['Panel', 'Pronósticos', 'Escenarios', 'Insights'],
    kpis: [
      { label: 'Pronósticos', value: '46', delta: { value: '+8', direction: 'up' } },
      { label: 'Precisión (MAPE)', value: '92', unit: '%', delta: { value: '+1.4', direction: 'up' } },
      { label: 'Alertas', value: '3', delta: { value: '-1', direction: 'down' } },
    ],
    colLabel: 'SKU',
    rows: [
      { codigo: 'SKU-114', nombre: 'Arándano 125g', estado: 'good' },
      { codigo: 'SKU-220', nombre: 'Uva Red Globe', estado: 'fair' },
    ],
  },
  agroquality: {
    mark: 'λ',
    name: 'AgroQuality',
    tagline: 'Calidad post-cosecha',
    role: 'Inspector',
    cta: 'Nueva inspección',
    nav: ['Panel', 'Lotes', 'Inspecciones', 'Reportes'],
    kpis: [
      { label: 'Lotes', value: '128', delta: { value: '+12', direction: 'up' } },
      { label: 'Materia seca', value: '23.4', unit: '%', delta: { value: '+1.2', direction: 'up' } },
      { label: 'Rechazos', value: '4', delta: { value: '-2', direction: 'down' } },
    ],
    colLabel: 'Lote',
    rows: [
      { codigo: 'EMP001-014', nombre: 'Arándano', estado: 'good' },
      { codigo: 'EMP001-015', nombre: 'Uva', estado: 'fair' },
    ],
  },
};

const meta: Meta = {
  title: 'Layout/DashboardShell',
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj;

export const AppCompleta: Story = {
  render: (_args, { globals }) => {
    const cfg = APPS[(globals.theme as string) ?? 'corporate'] ?? APPS.corporate;
    const [active, setActive] = useState('panel');
    const items = cfg.nav.map((label, i) => ({ key: i === 0 ? 'panel' : label.toLowerCase(), label }));
    return (
      <DashboardShell
        sidebar={
          <Sidebar
            brand={{ mark: cfg.mark, name: cfg.name, tagline: cfg.tagline }}
            items={items}
            activeKey={active}
            onSelect={setActive}
            footer={{ who: 'Víctor C. · Marand', mode: cfg.role }}
          />
        }
        topbar={
          <>
            <b className="font-display text-lg text-ink">Panel</b>
            <Button size="sm">{cfg.cta}</Button>
          </>
        }
      >
        <div className="grid grid-cols-3 gap-4">
          {cfg.kpis.map((k) => (
            <KpiCard key={k.label} {...k} />
          ))}
        </div>
        <div className="mt-6">
          <Table<Row>
            rowKey={(r) => r.codigo}
            rows={cfg.rows}
            columns={[
              { key: 'codigo', header: cfg.colLabel },
              { key: 'nombre', header: 'Detalle' },
              {
                key: 'estado',
                header: 'Estado',
                cell: (r) => <Badge tone={r.estado}>{r.estado}</Badge>,
              },
            ]}
          />
        </div>
      </DashboardShell>
    );
  },
};
