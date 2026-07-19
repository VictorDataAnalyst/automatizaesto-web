import { type HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export type BadgeTone = 'neutral' | 'accent' | 'good' | 'fair' | 'poor';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-bg-soft text-ink-dim border border-border',
  accent: 'bg-[rgba(var(--color-accent-rgb),0.14)] text-accent',
  good: 'bg-success-bg text-success',
  fair: 'bg-warning-bg text-warning',
  poor: 'bg-danger-bg text-danger',
};

/**
 * Chip / etiqueta de estado. Unifica `.chip` (good/fair/poor de AgroQuality),
 * `.post-tag`, `.var-chip` y `.veredicto`.
 */
export function Badge({ tone = 'neutral', className, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-pill px-3 py-1 text-xs font-semibold ' +
          'uppercase tracking-wide whitespace-nowrap',
        tones[tone],
        className,
      )}
      {...rest}
    />
  );
}
