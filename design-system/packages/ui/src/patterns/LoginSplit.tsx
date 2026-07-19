import { type ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface LoginSplitProps {
  brand: { mark?: ReactNode; name: ReactNode };
  title: ReactNode;
  subtitle?: ReactNode;
  /** El formulario (campos + botón de envío). */
  children: ReactNode;
  /** Contenido del panel lateral de marca (claim, ilustración…). */
  showcase?: ReactNode;
  footer?: ReactNode;
  className?: string;
}

/**
 * Pantalla de login a dos columnas. Unifica el patrón `.lx-*` que hoy está
 * duplicado (casi idéntico) entre las apps Forecast y AgroQuality.
 * Form a la izquierda; panel de marca con degradado de acento a la derecha.
 */
export function LoginSplit({ brand, title, subtitle, children, showcase, footer, className }: LoginSplitProps) {
  return (
    <div className={cn('grid min-h-screen bg-bg md:grid-cols-2', className)}>
      {/* Columna del formulario */}
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5">
            {brand.mark && (
              <span className="grid h-8 w-8 place-items-center rounded-sm bg-accent font-mono font-bold text-accent-contrast">
                {brand.mark}
              </span>
            )}
            <b className="font-display text-base text-ink">{brand.name}</b>
          </div>

          <h1 className="font-display text-3xl leading-snug text-ink">{title}</h1>
          {subtitle && <p className="mt-2 text-md text-ink-dim">{subtitle}</p>}

          <div className="mt-8 flex flex-col gap-4">{children}</div>

          {footer && <div className="mt-8 text-sm text-ink-mute">{footer}</div>}
        </div>
      </div>

      {/* Columna de marca */}
      <div className="relative hidden overflow-hidden md:flex md:flex-col md:justify-center md:gap-6 md:px-12 md:text-accent-contrast">
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(150deg, var(--color-accent-cool) 0%, var(--color-accent) 55%, var(--color-accent-warm) 130%)',
          }}
          aria-hidden
        />
        <div className="relative">{showcase}</div>
      </div>
    </div>
  );
}
