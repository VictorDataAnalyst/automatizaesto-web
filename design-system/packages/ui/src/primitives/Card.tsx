import { type HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Eleva con sombra en hover (para tarjetas clicables). */
  interactive?: boolean;
  /** Borde discontinuo (estado "próximamente"/placeholder). */
  dashed?: boolean;
}

/**
 * Contenedor base. Unifica `.feature-card`, `.post-card`, `.callout`,
 * `.card` y `.panel` de las tres fuentes.
 */
export function Card({ interactive, dashed, className, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-surface p-6',
        dashed ? 'border-dashed border-border opacity-75' : 'border-border',
        interactive &&
          'transition-[transform,border-color] duration-[var(--dur-slow)] ease-out ' +
            'hover:-translate-y-1 hover:border-accent/40 cursor-pointer',
        className,
      )}
      {...rest}
    />
  );
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('font-display text-xl text-ink', className)} {...rest} />;
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('mt-2 text-md leading-relaxed text-ink-dim', className)} {...rest} />;
}
