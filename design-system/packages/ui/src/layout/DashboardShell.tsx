import { type ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface DashboardShellProps {
  /** Barra lateral (normalmente <Sidebar />). */
  sidebar: ReactNode;
  /** Barra superior opcional (acciones, breadcrumb, perfil). */
  topbar?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Layout de aplicación: sidebar fija + área de contenido con topbar opcional.
 * Es el shell base para AgroQuality, Forecast y Automatizaciones IA.
 */
export function DashboardShell({ sidebar, topbar, children, className }: DashboardShellProps) {
  return (
    <div className={cn('flex min-h-screen bg-bg text-ink', className)}>
      {sidebar}
      <div className="flex min-w-0 flex-1 flex-col">
        {topbar && (
          <header className="sticky top-0 z-nav flex items-center justify-between gap-4 border-b border-border bg-bg/80 px-6 py-3 backdrop-blur">
            {topbar}
          </header>
        )}
        <main className="mx-auto w-full max-w-container flex-1 px-6 py-8">{children}</main>
      </div>
    </div>
  );
}
