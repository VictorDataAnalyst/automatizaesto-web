import { Badge, Button, Table } from '@automatizaesto/ui';
import type { Inspeccion, Score } from '../types';
import { fmtFecha, resumen, SCORE_LABEL } from '../lib/scoring';

const TONE: Record<Score, 'good' | 'fair' | 'poor'> = { good: 'good', fair: 'fair', poor: 'poor' };

export function Inspecciones({ data }: { data: Inspeccion[] }) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-lg text-ink">Reportes de auditoría</h3>
        <span className="text-sm text-ink-mute">{data.length} guardados</span>
      </div>
      <Table<Inspeccion>
        rowKey={(i) => i.id}
        rows={data}
        empty="Aún no hay inspecciones."
        columns={[
          { key: 'codigo', header: 'ID', cell: (i) => <b>{i.codigo ?? i.id}</b> },
          { key: 'lote', header: 'Lote', cell: (i) => i.lote ?? '' },
          { key: 'producto', header: 'Producto', cell: (i) => `${i.producto ?? ''} · ${i.variedad ?? ''}` },
          { key: 'consignatario', header: 'Consignatario', cell: (i) => i.consignatario ?? '—' },
          { key: 'inspector', header: 'Inspector', cell: (i) => i.inspector ?? '—' },
          { key: 'ingreso', header: 'Ingreso', cell: (i) => fmtFecha(i.fecha_frigorifico) },
          { key: 'pallets', header: 'Pallets', numeric: true, align: 'right', cell: (i) => resumen(i).n },
          { key: 'score', header: 'Score', cell: (i) => {
            const s = resumen(i).scoreGlobal;
            return <Badge tone={TONE[s]}>{SCORE_LABEL[s]}</Badge>;
          } },
          { key: 'ver', header: '', align: 'right', cell: () => <Button variant="subtle" size="sm">Ver ›</Button> },
        ]}
      />
    </div>
  );
}
