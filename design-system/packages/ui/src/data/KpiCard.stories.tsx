import type { Meta, StoryObj } from '@storybook/react';
import { KpiCard } from './KpiCard';

const meta: Meta<typeof KpiCard> = {
  title: 'Datos/KpiCard',
  component: KpiCard,
  args: { label: 'Materia seca promedio', value: '23.4', unit: '%' },
};
export default meta;
type Story = StoryObj<typeof KpiCard>;

export const Default: Story = {};

export const Grilla: Story = {
  render: () => (
    <div className="grid max-w-3xl grid-cols-3 gap-4">
      <KpiCard label="Lotes inspeccionados" value="128" delta={{ value: '+12', direction: 'up' }} />
      <KpiCard label="Materia seca" value="23.4" unit="%" delta={{ value: '+1.2', direction: 'up' }} />
      <KpiCard label="Rechazos" value="4" delta={{ value: '-2', direction: 'down' }} />
    </div>
  ),
};
