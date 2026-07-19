import { type ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface KpiCardProps {
  label: ReactNode;
  value: ReactNode;
  /** Sufijo pequeño junto al valor (p.ej. "%", "kg"). */
  unit?: ReactNode;
  /** Variación; positiva = verde, negativa = roja. */
  delta?: { value: string; direction: 'up' | 'down' | 'flat' };
  className?: string;
}

const deltaTone = {
  up: 'text-success',
  down: 'text-danger',
  flat: 'text-ink-mute',
} as const;

const deltaGlyph = { up: '▲', down: '▼', flat: '–' } as const;

/**
 * Tarjeta de métrica. Unifica `.kpi .val` (AgroQuality) y los stat cards
 * de Forecast. El valor usa la display font con cifras tabulares.
 */
export function KpiCard({ label, value, unit, delta, className }: KpiCardProps) {
  return (
    <div className={cn('rounded-lg border border-border bg-surface p-5', className)}>
      <div className="text-sm font-medium text-ink-dim">{label}</div>
      <div className="mt-1.5 flex items-end gap-2">
        <span className="font-display text-3xl font-bold leading-tight [font-variant-numeric:tabular-nums]">
          {value}
        </span>
        {unit && <span className="pb-1 text-md text-ink-mute">{unit}</span>}
      </div>
      {delta && (
        <div className={cn('mt-2 text-sm font-semibold', deltaTone[delta.direction])}>
          {deltaGlyph[delta.direction]} {delta.value}
        </div>
      )}
    </div>
  );
}
