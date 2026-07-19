import { type ReactNode } from 'react';
import { cn } from '../lib/cn';

export interface Column<Row> {
  key: string;
  header: ReactNode;
  /** Render de celda; por defecto lee row[key]. */
  cell?: (row: Row) => ReactNode;
  align?: 'left' | 'right' | 'center';
  /** Cifras tabulares + display font (para columnas numéricas). */
  numeric?: boolean;
}

export interface TableProps<Row> {
  columns: Column<Row>[];
  rows: Row[];
  /** Clave única por fila. */
  rowKey: (row: Row, index: number) => string | number;
  /** Hace la fila clicable (cursor + hover). */
  onRowClick?: (row: Row) => void;
  empty?: ReactNode;
  className?: string;
}

const alignClass = { left: 'text-left', right: 'text-right', center: 'text-center' } as const;

/**
 * Tabla de datos. Unifica `.tbl` (orden + hover) y las listas de Forecast.
 */
export function Table<Row>({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty = 'Sin registros',
  className,
}: TableProps<Row>) {
  return (
    <div className={cn('overflow-hidden rounded-lg border border-border', className)}>
      <table className="w-full border-collapse text-base">
        <thead>
          <tr className="border-b border-border bg-bg-soft">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-mute',
                  alignClass[col.align ?? 'left'],
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center text-ink-mute">
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr
                key={rowKey(row, i)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  'border-b border-border last:border-0',
                  onRowClick && 'cursor-pointer transition-colors hover:bg-bg-soft',
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      'px-4 py-3 text-ink',
                      alignClass[col.align ?? 'left'],
                      col.numeric && 'font-display [font-variant-numeric:tabular-nums]',
                    )}
                  >
                    {col.cell ? col.cell(row) : (row as Record<string, ReactNode>)[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
