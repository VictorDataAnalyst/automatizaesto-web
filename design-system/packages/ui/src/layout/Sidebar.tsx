import { type ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface SidebarItem {
  key: string;
  label: ReactNode;
  icon?: ReactNode;
}

export interface SidebarBrand {
  /** Marca/logo: glifo o nodo (p.ej. la λ del logo). */
  mark?: ReactNode;
  name: ReactNode;
  tagline?: ReactNode;
}

export interface SidebarFooter {
  /** Usuario / org. */
  who?: ReactNode;
  /** Etiqueta de modo o rol (se muestra como pill). */
  mode?: ReactNode;
}

export interface SidebarProps {
  brand: SidebarBrand;
  items: SidebarItem[];
  activeKey?: string;
  onSelect?: (key: string) => void;
  footer?: SidebarFooter;
  className?: string;
}

/**
 * Barra lateral de navegación. Promueve el `.side` de AgroQuality a estándar,
 * pero themeable: usa tokens semánticos, así funciona en los 3 temas.
 */
export function Sidebar({ brand, items, activeKey, onSelect, footer, className }: SidebarProps) {
  return (
    <aside
      className={cn(
        'sticky top-0 flex h-screen flex-col border-r border-border bg-bg-soft',
        'w-[var(--sidebar-w)] flex-shrink-0',
        className,
      )}
    >
      {/* Marca */}
      <div className="flex items-center gap-3 px-4 py-5">
        {brand.mark && (
          <span className="grid h-9 w-9 place-items-center rounded-sm bg-accent font-mono text-xl font-bold text-accent-contrast">
            {brand.mark}
          </span>
        )}
        <span className="leading-tight">
          <b className="block font-display text-base text-ink">{brand.name}</b>
          {brand.tagline && <small className="text-xs text-ink-mute">{brand.tagline}</small>}
        </span>
      </div>

      {/* Navegación */}
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3">
        {items.map((item) => {
          const active = item.key === activeKey;
          return (
            <button
              key={item.key}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => onSelect?.(item.key)}
              className={cn(
                'flex w-full items-center gap-3 rounded-sm px-3 py-2.5 text-left text-sm font-medium',
                'transition-colors duration-[var(--dur-fast)]',
                active
                  ? 'bg-[rgba(var(--color-accent-rgb),0.14)] text-accent'
                  : 'text-ink-dim hover:bg-surface hover:text-ink',
              )}
            >
              {item.icon && <span className="grid w-5 place-items-center">{item.icon}</span>}
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Pie: usuario + modo */}
      {footer && (
        <div className="border-t border-border px-4 py-4 text-xs text-ink-mute">
          {footer.who}
          {footer.mode && (
            <span className="mt-1.5 inline-block rounded-sm bg-[rgba(var(--color-accent-rgb),0.18)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-accent">
              {footer.mode}
            </span>
          )}
        </div>
      )}
    </aside>
  );
}
