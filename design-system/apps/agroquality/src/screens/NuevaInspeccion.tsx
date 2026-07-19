import { useState, type ReactNode } from 'react';
import { Badge, Button, Card, Field, Input, Select } from '@automatizaesto/ui';
import { api } from '../lib/api';
import { useToast } from '../lib/toast';
import { scoreDe } from '../lib/scoring';
import { DEFECTOS_COMUNES, nuevoDraft, nuevoPallet, OPTS, PRODUCTORES } from '../lib/constants';
import type { DraftInspeccion, DraftPallet, Defecto, Foto, Termo } from '../lib/draft';
import { PhotoGallery } from '../components/PhotoGallery';
import type { Score } from '../types';

const TONE: Record<Score, 'good' | 'fair' | 'poor'> = { good: 'good', fair: 'fair', poor: 'poor' };
const PALLET_COLS = 'grid-cols-[1.3fr_.6fr_1fr_.7fr_.7fr_1.4fr_auto_auto_auto]';

function num(v: string): number | null {
  return v === '' || v == null ? null : Number(v);
}

export function NuevaInspeccion({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const [d, setD] = useState<DraftInspeccion>(nuevoDraft);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const set = <K extends keyof DraftInspeccion>(k: K, v: DraftInspeccion[K]) => setD((p) => ({ ...p, [k]: v }));
  const setPallet = (i: number, patch: Partial<DraftPallet>) =>
    setD((p) => ({ ...p, pallets: p.pallets.map((pl, j) => (j === i ? { ...pl, ...patch } : pl)) }));

  function F(k: keyof DraftInspeccion, label: string, type = 'text', opts?: string[], required = false) {
    return (
      <Field label={label} required={required}>
        {opts ? (
          <Select value={d[k] as string} onChange={(e) => set(k, e.target.value as never)}>
            {opts.map((o) => <option key={o}>{o}</option>)}
          </Select>
        ) : (
          <Input type={type} value={d[k] as string} onChange={(e) => set(k, e.target.value as never)} />
        )}
      </Field>
    );
  }

  async function guardar() {
    if (!d.lote) return toast('Falta el Lote.', 'error');
    if (!d.fecha_frigorifico) return toast('Falta la fecha de ingreso al frigorífico.', 'error');
    if (!d.pallets.length) return toast('Agrega al menos un pallet.', 'error');

    const body = {
      ...d,
      codigo: d.codigo || null,
      cajas: num(d.cajas),
      total_pallets: num(d.total_pallets),
      fotos: d.fotos.length ? d.fotos.map((f) => ({ tipo: f.tipo, ref: f.ref })) : null,
      termografia: d.termografia.filter((t) => t.serial || t.temp_avg || t.temp_min || t.temp_max).map((t) => ({
        serial: t.serial || null,
        trip_length_dias: num(t.trip_length_dias),
        temp_min: num(t.temp_min),
        temp_max: num(t.temp_max),
        temp_avg: num(t.temp_avg),
      })),
      pallets: d.pallets.map((p) => ({
        codigo: p.codigo,
        productor: p.productor || null,
        clase: p.clase || null,
        calibre: num(p.calibre),
        temp_prom: num(p.temp_prom),
        peso_neto_prom: num(p.peso_neto_prom) ?? 10,
        brix_prom: num(p.brix_prom),
        cajas_muestra: num(p.cajas_muestra),
        tamano_muestra: num(p.tamano_muestra),
        pct_calidad: num(p.pct_calidad) ?? 0,
        pct_condicion: num(p.pct_condicion) ?? 0,
        defecto_principal: p.defecto_principal || null,
        variedad: p.variedad || null,
        fecha_embalaje: p.fecha_embalaje || null,
        etiqueta: p.etiqueta || null,
        embalaje: p.embalaje || null,
        firmeza_psi_min: num(p.firmeza_psi_min),
        firmeza_psi_max: num(p.firmeza_psi_max),
        plu_pct: num(p.plu_pct),
        golpe_vista: p.golpe_vista || null,
        qc_embalaje: p.qc_embalaje || null,
        trazabilidad: p.trazabilidad,
        pti: p.pti,
        base_pallet_danado: p.base_pallet_danado,
        defectos: p.defectos.filter((x) => x.nombre).map((x) => ({ nombre: x.nombre, categoria: x.categoria, pct: Number(x.pct) || 0 })),
        fotos: p.fotos.length ? p.fotos.map((f) => ({ tipo: f.tipo, ref: f.ref })) : null,
      })),
    };

    setBusy(true);
    try {
      await api('/api/inspecciones', { method: 'POST', body });
      toast('Inspección guardada ✓');
      onSaved();
    } catch (e) {
      toast('Error: ' + (e instanceof Error ? e.message : 'no se pudo guardar'), 'error', 5000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-sm border border-border bg-bg-soft px-4 py-3 text-sm text-ink-dim">
        ⌬ Captura jerárquica: cabecera del lote, luego cada pallet con su % de defectos. El score Good/Fair/Poor lo calcula el servidor.
      </div>

      {/* Cabecera */}
      <Card>
        <Seccion>Cabecera del lote</Seccion>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {F('lote', 'Lote ★', 'text', undefined, true)}
          {F('container', 'Container / Guía')}
          {F('compania', 'Compañía')}
          {F('consignatario', 'Consignatario')}
          {F('producto', 'Producto')}
          {F('variedad', 'Variedad')}
          {F('embalaje', 'Embalaje')}
          {F('tipo_producto', 'Tipo producto', 'text', OPTS.tipo_producto)}
          {F('locacion', 'Locación (destino)')}
          {F('pais_origen', 'País origen')}
          {F('barco', 'Barco')}
          {F('tipo_carrier', 'Tipo carrier', 'text', OPTS.tipo_carrier)}
          {F('frigorifico', 'Frigorífico')}
          {F('inspector', 'Inspector')}
          {F('tipo_inspeccion', 'Tipo inspección', 'text', OPTS.tipo_inspeccion)}
          {F('fumigacion', 'Fumigación', 'text', OPTS.fumigacion)}
          {F('cajas', 'Cajas', 'number')}
          {F('total_pallets', '# Pallets', 'number')}
          {F('num_factura', 'Nº Factura')}
          {F('hora_frigorifico', 'Hora frigorífico')}
          {F('fecha_embalaje', 'Fecha embalaje', 'date')}
          {F('fecha_arribo', 'Fecha arribo', 'date')}
          {F('fecha_frigorifico', 'Ingreso frigorífico ★', 'date', undefined, true)}
          {F('numero_reporte', 'Nº reporte')}
        </div>
      </Card>

      {/* Fotos del contenedor */}
      <Card>
        <Seccion>Fotos del contenedor</Seccion>
        <PhotoGallery label="Contenedor" tipo="contenedor" fotos={d.fotos} onChange={(fotos) => set('fotos', fotos as Foto[])} />
      </Card>

      {/* Termografía */}
      <Card>
        <Seccion>Termografía del contenedor</Seccion>
        <Termografia rows={d.termografia} onChange={(termografia) => set('termografia', termografia)} />
      </Card>

      {/* Pallets */}
      <Card>
        <Seccion>Pallets · {d.pallets.length} agregados</Seccion>
        {d.pallets.length === 0 ? (
          <p className="text-sm text-ink-mute">Aún no agregas pallets.</p>
        ) : (
          <div>
            {/* Cabeceras de la grilla (requisito: toda grilla de captura debe rotularse) */}
            <div className={`grid ${PALLET_COLS} gap-2 border-b border-border px-1 pb-2 text-[11px] uppercase tracking-wide text-ink-mute`}>
              <span>Código</span><span>Calibre</span><span>Productor</span><span>% Calidad</span>
              <span>% Condición</span><span>Defecto principal</span><span>Score</span><span>Detalle</span><span></span>
            </div>
            {d.pallets.map((p, i) => {
              const score = scoreDe((Number(p.pct_calidad) || 0) + (Number(p.pct_condicion) || 0));
              return (
                <div key={i} className="border-b border-border last:border-0">
                  <div className={`grid ${PALLET_COLS} items-center gap-2 py-2`}>
                    <Input value={p.codigo} placeholder="R-MAR-…" onChange={(e) => setPallet(i, { codigo: e.target.value })} />
                    <Input type="number" value={p.calibre} onChange={(e) => setPallet(i, { calibre: e.target.value })} />
                    <Select value={p.productor} onChange={(e) => setPallet(i, { productor: e.target.value })}>
                      {PRODUCTORES.map((o) => <option key={o}>{o}</option>)}
                    </Select>
                    <Input type="number" step="0.1" value={p.pct_calidad} onChange={(e) => setPallet(i, { pct_calidad: e.target.value })} />
                    <Input type="number" step="0.1" value={p.pct_condicion} onChange={(e) => setPallet(i, { pct_condicion: e.target.value })} />
                    <Input value={p.defecto_principal} placeholder="Defecto principal" onChange={(e) => setPallet(i, { defecto_principal: e.target.value })} />
                    <Badge tone={TONE[score]}>{score}</Badge>
                    <Button variant="ghost" size="sm" onClick={() => setPallet(i, { _open: !p._open })}>
                      {p._open ? '▾ Cerrar' : '⋯ Abrir'}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => set('pallets', d.pallets.filter((_, j) => j !== i))}>✕</Button>
                  </div>
                  {p._open && <PalletDetalle p={p} onPatch={(patch) => setPallet(i, patch)} />}
                </div>
              );
            })}
          </div>
        )}
        <Button variant="subtle" size="sm" className="mt-4" onClick={() => set('pallets', [...d.pallets, nuevoPallet() as DraftPallet])}>
          ＋ Agregar pallet
        </Button>
      </Card>

      {/* Notas */}
      <Card>
        <Seccion>Notas del reporte</Seccion>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Quality & Condition" className="md:col-span-1">
            <textarea
              className="min-h-20 w-full rounded-sm border border-border bg-surface px-3 py-2 text-base text-ink"
              value={d.notas_calidad}
              onChange={(e) => set('notas_calidad', e.target.value)}
            />
          </Field>
          <Field label="Inspector Notes">
            <textarea
              className="min-h-20 w-full rounded-sm border border-border bg-surface px-3 py-2 text-base text-ink"
              value={d.notas_inspector}
              onChange={(e) => set('notas_inspector', e.target.value)}
            />
          </Field>
          <Field label="Digitado por">
            <Input value={d.digitado_por} onChange={(e) => set('digitado_por', e.target.value)} />
          </Field>
        </div>
      </Card>

      <div className="flex gap-3 border-t border-border pt-5">
        <Button onClick={guardar} disabled={busy}>{busy ? 'Guardando…' : 'Guardar inspección'}</Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>Cancelar</Button>
      </div>
    </div>
  );
}

function Seccion({ children }: { children: ReactNode }) {
  return <h3 className="mb-4 font-display text-base font-semibold uppercase tracking-wide text-ink-dim">{children}</h3>;
}

function Termografia({ rows, onChange }: { rows: Termo[]; onChange: (r: Termo[]) => void }) {
  const vacio: Termo = { serial: '', trip_length_dias: '', temp_min: '', temp_max: '', temp_avg: '' };
  const upd = (i: number, patch: Partial<Termo>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <div>
      {rows.length > 0 && (
        <div className="grid grid-cols-[1.4fr_.9fr_.7fr_.7fr_.7fr_auto] gap-2 px-1 pb-2 text-[11px] uppercase tracking-wide text-ink-mute">
          <span>Serial</span><span>Días viaje</span><span>Temp. Min</span><span>Temp. Max</span><span>Temp. Avg</span><span></span>
        </div>
      )}
      {rows.map((t, i) => (
        <div key={i} className="grid grid-cols-[1.4fr_.9fr_.7fr_.7fr_.7fr_auto] items-center gap-2 pb-2">
          <Input value={t.serial} placeholder="U1085015" onChange={(e) => upd(i, { serial: e.target.value })} />
          <Input type="number" value={t.trip_length_dias} onChange={(e) => upd(i, { trip_length_dias: e.target.value })} />
          <Input type="number" step="0.1" value={t.temp_min} onChange={(e) => upd(i, { temp_min: e.target.value })} />
          <Input type="number" step="0.1" value={t.temp_max} onChange={(e) => upd(i, { temp_max: e.target.value })} />
          <Input type="number" step="0.1" value={t.temp_avg} onChange={(e) => upd(i, { temp_avg: e.target.value })} />
          <Button variant="ghost" size="sm" onClick={() => onChange(rows.filter((_, j) => j !== i))}>×</Button>
        </div>
      ))}
      <Button variant="subtle" size="sm" className="mt-2" onClick={() => onChange([...rows, vacio])}>＋ Agregar serial</Button>
    </div>
  );
}

function PalletDetalle({ p, onPatch }: { p: DraftPallet; onPatch: (patch: Partial<DraftPallet>) => void }) {
  const updDef = (i: number, patch: Partial<Defecto>) =>
    onPatch({ defectos: p.defectos.map((d, j) => (j === i ? { ...d, ...patch } : d)) });
  const text = (k: keyof DraftPallet, label: string, type = 'text') => (
    <Field label={label}>
      <Input type={type} value={p[k] as string} onChange={(e) => onPatch({ [k]: e.target.value } as Partial<DraftPallet>)} />
    </Field>
  );
  return (
    <div className="mb-3 rounded-md bg-bg-soft p-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {text('variedad', 'Variedad')}
        {text('fecha_embalaje', 'Fecha embalaje', 'date')}
        {text('etiqueta', 'Etiqueta')}
        {text('embalaje', 'Embalaje')}
        {text('firmeza_psi_min', 'Firmeza PSI Min', 'number')}
        {text('firmeza_psi_max', 'Firmeza PSI Max', 'number')}
        {text('brix_prom', 'Brix', 'number')}
        {text('plu_pct', 'PLU %', 'number')}
        <Field label="Golpe de vista">
          <Select value={p.golpe_vista} onChange={(e) => onPatch({ golpe_vista: e.target.value })}>
            {OPTS.golpe_vista.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select>
        </Field>
        {text('qc_embalaje', 'QC embalaje')}
        {text('clase', 'Clase')}
        {text('cajas_muestra', 'Cajas muestra', 'number')}
        {text('temp_prom', 'Temp. prom', 'number')}
        {text('tamano_muestra', 'Tamaño muestra', 'number')}
      </div>

      <div className="mt-3 flex flex-wrap gap-5">
        {(['trazabilidad', 'pti', 'base_pallet_danado'] as const).map((k) => (
          <label key={k} className="flex cursor-pointer items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={p[k]} onChange={(e) => onPatch({ [k]: e.target.checked } as Partial<DraftPallet>)} className="h-4 w-4 accent-[var(--color-accent)]" />
            {k === 'base_pallet_danado' ? 'Base pallet dañado' : k.toUpperCase()}
          </label>
        ))}
      </div>

      {/* Defectos por nombre */}
      <div className="mt-4">
        <div className="mb-2 text-[11px] uppercase tracking-wide text-ink-mute">Defectos por nombre (%)</div>
        <datalist id="defOpts">{DEFECTOS_COMUNES.map((x) => <option key={x} value={x} />)}</datalist>
        {p.defectos.map((def, di) => (
          <div key={di} className="mb-1.5 grid grid-cols-[1.6fr_.9fr_.6fr_auto] items-center gap-2">
            <Input list="defOpts" value={def.nombre} placeholder="Defecto" onChange={(e) => updDef(di, { nombre: e.target.value })} />
            <Select value={def.categoria} onChange={(e) => updDef(di, { categoria: e.target.value as Defecto['categoria'] })}>
              <option value="condicion">Condición</option>
              <option value="calidad">Calidad</option>
            </Select>
            <Input type="number" step="0.01" value={def.pct} placeholder="%" onChange={(e) => updDef(di, { pct: e.target.value })} />
            <Button variant="ghost" size="sm" onClick={() => onPatch({ defectos: p.defectos.filter((_, j) => j !== di) })}>×</Button>
          </div>
        ))}
        <Button variant="subtle" size="sm" className="mt-1" onClick={() => onPatch({ defectos: [...p.defectos, { nombre: '', categoria: 'condicion', pct: '' }] })}>
          ＋ Agregar defecto
        </Button>
      </div>

      {/* Galerías de pallet y muestra */}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <PhotoGallery label="Fotos de pallet" tipo="pallet" fotos={p.fotos} onChange={(fotos) => onPatch({ fotos })} />
        <PhotoGallery label="Fotos de muestra" tipo="muestra" fotos={p.fotos} onChange={(fotos) => onPatch({ fotos })} />
      </div>
    </div>
  );
}
