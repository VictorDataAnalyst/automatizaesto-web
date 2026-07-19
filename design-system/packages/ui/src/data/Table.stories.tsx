import type { Meta, StoryObj } from '@storybook/react';
import { Table } from './Table';
import { Badge } from '../primitives/Badge';

interface Lote {
  codigo: string;
  cultivo: string;
  ms: number;
  estado: 'good' | 'fair' | 'poor';
}

const rows: Lote[] = [
  { codigo: 'EMP001-014', cultivo: 'Arándano', ms: 23.4, estado: 'good' },
  { codigo: 'EMP001-015', cultivo: 'Uva', ms: 19.1, estado: 'fair' },
  { codigo: 'EMP002-003', cultivo: 'Palta', ms: 14.8, estado: 'poor' },
];

const estadoLabel = { good: 'Aprobado', fair: 'Observado', poor: 'Rechazado' };

const meta: Meta<typeof Table<Lote>> = {
  title: 'Datos/Table',
  component: Table,
};
export default meta;
type Story = StoryObj<typeof Table<Lote>>;

export const Lotes: Story = {
  render: () => (
    <div className="max-w-3xl">
      <Table<Lote>
        rowKey={(r) => r.codigo}
        rows={rows}
        onRowClick={() => {}}
        columns={[
          { key: 'codigo', header: 'Lote' },
          { key: 'cultivo', header: 'Cultivo' },
          { key: 'ms', header: 'MS %', numeric: true, align: 'right', cell: (r) => r.ms.toFixed(1) },
          {
            key: 'estado',
            header: 'Estado',
            cell: (r) => <Badge tone={r.estado}>{estadoLabel[r.estado]}</Badge>,
          },
        ]}
      />
    </div>
  ),
};
