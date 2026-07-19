import { useRef, useState, type ChangeEvent } from 'react';
import { Badge } from '@automatizaesto/ui';
import { uploadFoto } from '../lib/api';
import { MAX_FOTOS } from '../lib/constants';
import { useToast } from '../lib/toast';
import type { Foto } from '../lib/draft';

interface Props {
  label: string;
  tipo: Foto['tipo'];
  fotos: Foto[];
  onChange: (fotos: Foto[]) => void;
}

/**
 * Galería de fotos con LÍMITE DURO de 15 por galería (requisito de captura):
 *  - contador persistente "n/15",
 *  - aviso explícito de cuántas se omiten ANTES de descartar,
 *  - input deshabilitado al llegar al tope (no más pérdida silenciosa).
 */
export function PhotoGallery({ label, tipo, fotos, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const propias = fotos.filter((f) => f.tipo === tipo);
  const lleno = propias.length >= MAX_FOTOS;

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    if (!files.length) return;

    const disp = Math.max(0, MAX_FOTOS - propias.length);
    if (files.length > disp) {
      toast(
        `Has excedido el límite de ${MAX_FOTOS} fotos en "${label}". Ya tienes ${propias.length}; se omitirán ${files.length - disp} de las ${files.length} seleccionadas.`,
        'warn',
        5200,
      );
    }
    const aSubir = files.slice(0, disp);
    if (!aSubir.length) return;

    setBusy(true);
    const nuevas: Foto[] = [];
    for (const file of aSubir) {
      try {
        const r = await uploadFoto(file, tipo);
        nuevas.push({ tipo, ref: r.ref, url: r.url });
      } catch {
        toast('Error al subir una foto.', 'error');
      }
    }
    setBusy(false);
    if (nuevas.length) {
      onChange([...fotos, ...nuevas]);
      if (files.length <= disp) toast(`${nuevas.length} foto(s) ✓`);
    }
  }

  function quitar(ref: string) {
    onChange(fotos.filter((f) => f.ref !== ref));
  }

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-semibold text-ink">{label}</span>
        <Badge tone={lleno ? 'poor' : 'neutral'}>
          {propias.length}/{MAX_FOTOS}
          {lleno ? ' — límite alcanzado' : ''}
        </Badge>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {propias.map((f) => (
          <span key={f.ref} className="relative inline-block">
            <img src={f.url} alt="" className="h-12 w-12 rounded-sm border border-border object-cover" />
            <button
              type="button"
              onClick={() => quitar(f.ref)}
              aria-label="Quitar foto"
              className="absolute -right-1.5 -top-1.5 grid h-4 w-4 place-items-center rounded-pill bg-ink text-[10px] leading-none text-bg"
            >
              ×
            </button>
          </span>
        ))}
        {propias.length === 0 && <span className="text-sm text-ink-mute">Sin fotos aún</span>}
      </div>
      <input ref={inputRef} type="file" accept="image/*" multiple hidden onChange={onPick} />
      <button
        type="button"
        disabled={lleno || busy}
        onClick={() => inputRef.current?.click()}
        className="mt-2 rounded-sm border border-border px-3 py-1.5 text-sm text-ink transition-colors hover:bg-bg-soft disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? 'Subiendo…' : lleno ? `Límite de ${MAX_FOTOS} alcanzado` : '📷 Agregar fotos'}
      </button>
    </div>
  );
}
