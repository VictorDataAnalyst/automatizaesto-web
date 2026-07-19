import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from './Badge';

const meta: Meta<typeof Badge> = {
  title: 'Primitivas/Badge',
  component: Badge,
  args: { children: 'Aprobado', tone: 'good' },
  argTypes: {
    tone: { control: 'select', options: ['neutral', 'accent', 'good', 'fair', 'poor'] },
  },
};
export default meta;
type Story = StoryObj<typeof Badge>;

export const Good: Story = {};

export const Galeria: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Badge tone="neutral">Neutral</Badge>
      <Badge tone="accent">Destacado</Badge>
      <Badge tone="good">Aprobado</Badge>
      <Badge tone="fair">Observado</Badge>
      <Badge tone="poor">Rechazado</Badge>
    </div>
  ),
};
