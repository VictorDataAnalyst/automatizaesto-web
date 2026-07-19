import { useMemo, useState } from 'react';
import { Badge, Button, Card, Field, Input, KpiCard, Select, Table } from '@automatizaesto/ui';
import type { Inspeccion, Filtros, Score } from '../types';
import { filtradas, fmtFecha, pctScore, resumen, SCORE_LABEL } from '../lib/scoring';

const VACIO: Filtros = { d1: '', d2: '', score: '', consig: '' };
const SCORE_TONE: Record<Score, 'good' | 'fair' | 'poor'> = { good: 'good', fair: 'fair', poor: 'poor' };

export function Dashboard({ data }: { data: Inspeccion[] }) {
  const [fil, setFil] = useState<Filtros>(VACIO);
  const set = (patch: Partial<Filtros>) => setFil((f) => ({ ...f, ...patch }));

  const consignatarios = useMemo(
    () => [...new Set(data.map((i) => i.consignatario).filter(Boolean))] as string[],
    [data],
  );

  const list = useMemo(() => filtradas(data, fil), [data, fil]);

  const m = useMemo(() => {
    const cont: Record<Score, number> = { good: 0, fair: 0, poor: 0 };
    const defMap: Record<string, number> = {};
    let totPallets = 0, totCajas = 0;
    list.forEach((i) => {
      totCajas += i.cajas ?? 0;
      (i.pallets ?? []).forEach((p) => {
        totPallets++;
        if (p.pallet_score) cont[p.pallet_score]++;
        (p.defecto_principal ?? '').split(',').map((s) => s.trim()).forEach((d) => {
          if (d) defMap[d] = (defMap[d] ?? 0) + 1;
        });
      });
    });
    const pct = pctScore(cont);
    const defArr = Object.entries(defMap).sort((a, b) => b[1] - a[1]).slice(0, 7);
    return { cont, totPallets, totCajas, pct, defArr, maxDef: defArr[0]?.[1] ?? 1 };
  }, [list]);

  return (
    <div className="flex flex-col gap-6">
      {/* Filtros */}
      <Card className="flex flex-wrap items-end gap-3 p-4">
        <Field label="Ingreso desde" className="w-40">
          <Input type="date" value={fil.d1} onChange={(e) => set({ d1: e.target.value })} />
        </Field>
        <Field label="Ingreso hasta" className="w-40">
          <Input type="date" value={fil.d2} onChange={(e) => set({ d2: e.target.value })} />
        </Field>
        <Field label="Score global" className="w-36">
          <Select value={fil.score} onChange={(e) => set({ score: e.target.value as Filtros['score'] })}>
            <option value="">Todos</option>
            <option value="good">Good</option>
            <option value="fair">Fair</option>
            <option value="poor">Poor</option>
          </Select>
        </Field>
        <Field label="Consignatario" className="w-52">
          <Select value={fil.consig} onChange={(e) => set({ consig: e.target.value })}>
            <option value="">Todos</option>
            {consignatarios.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </Select>
        </Field>
        <Button variant="ghost" size="sm" onClick={() => setFil(VACIO)}>
          ↺ Limpiar
        </Button>
        <div className="ml-auto">
          <Badge tone="neutral">
            {list.length} inspección(es) · {m.totPallets} pallets
          </Badge>
        </div>
      </Card>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Inspecciones" value={list.length} />
        <KpiCard label="Pallets auditados" value={m.totPallets} unit={`· ${m.totCajas.toLocaleString('es-PE')} cajas`} />
        <KpiCard label="Aprobación (Good+Fair)" value={m.pct.good + m.pct.fair} unit="%" />
        <KpiCard label="Defecto principal" value={m.defArr[0]?.[0] ?? '—'} unit={m.defArr[0] ? `${m.defArr[0][1]} pallets` : undefined} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Distribución de scores */}
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-lg text-ink">Distribución de scores</h3>
            <span className="text-sm text-ink-mute">{m.totPallets} pallets</span>
          </div>
          <div className="flex h-3 overflow-hidden rounded-pill">
            <span className="bg-success" style={{ width: `${m.pct.good}%` }} />
            <span className="bg-warning" style={{ width: `${m.pct.fair}%` }} />
            <span className="bg-danger" style={{ width: `${m.pct.poor}%` }} />
          </div>
          <div className="mt-4 flex flex-col gap-2">
            {(['good', 'fair', 'poor'] as Score[]).map((s) => (
              <div key={s} className="flex items-center gap-2 text-sm">
                <Badge tone={SCORE_TONE[s]}>{SCORE_LABEL[s]}</Badge>
                <b className="text-ink">{m.pct[s]}%</b>
                <span className="text-ink-mute">({m.cont[s]})</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Pareto de defectos */}
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-lg text-ink">Pareto de defectos</h3>
            <span className="text-sm text-ink-mute">por pallet</span>
          </div>
          {m.defArr.length === 0 ? (
            <p className="text-sm text-ink-mute">Sin datos</p>
          ) : (
            <div className="flex flex-col gap-2.5">
              {m.defArr.map(([d, c]) => (
                <div key={d} className="flex items-center gap-3 text-sm">
                  <span className="w-40 truncate text-ink-dim" title={d}>{d}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-pill bg-bg-soft">
                    <div className="h-full rounded-pill bg-accent" style={{ width: `${Math.round((c / m.maxDef) * 100)}%` }} />
                  </div>
                  <b className="w-6 text-right text-ink [font-variant-numeric:tabular-nums]">{c}</b>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Tabla */}
      <div>
        <h3 className="mb-3 font-display text-lg text-ink">Inspecciones del período</h3>
        <Table<Inspeccion>
          rowKey={(i) => i.id}
          rows={list}
          empty="No hay inspecciones en este período."
          columns={[
            { key: 'codigo', header: 'Inspección', cell: (i) => <b>{i.codigo ?? i.id}</b> },
            { key: 'lote', header: 'Lote / Barco', cell: (i) => (
              <div>
                <div>{i.lote}</div>
                <div className="text-xs text-ink-mute">{i.barco}</div>
              </div>
            ) },
            { key: 'consignatario', header: 'Consignatario', cell: (i) => i.consignatario ?? '—' },
            { key: 'locacion', header: 'Locación', cell: (i) => i.locacion ?? '—' },
            { key: 'ingreso', header: 'Ingreso', cell: (i) => fmtFecha(i.fecha_frigorifico) },
            { key: 'pallets', header: 'Pallets', numeric: true, align: 'right', cell: (i) => resumen(i).n },
            { key: 'score', header: 'Score', cell: (i) => {
              const s = resumen(i).scoreGlobal;
              return <Badge tone={SCORE_TONE[s]}>{SCORE_LABEL[s]}</Badge>;
            } },
            { key: 'tot', header: 'Total', numeric: true, align: 'right', cell: (i) => `${resumen(i).totProm}%` },
          ]}
        />
      </div>
    </div>
  );
}
