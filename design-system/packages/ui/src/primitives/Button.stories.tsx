import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'Primitivas/Button',
  component: Button,
  args: { children: 'Guardar inspección', variant: 'primary', size: 'md' },
  argTypes: {
    variant: { control: 'select', options: ['primary', 'ghost', 'subtle', 'whatsapp'] },
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
  },
};
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {};
export const Ghost: Story = { args: { variant: 'ghost' } };
export const Subtle: Story = { args: { variant: 'subtle' } };
export const WhatsApp: Story = { args: { variant: 'whatsapp', children: 'Escríbenos' } };

export const Galeria: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="primary">Primario</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="subtle">Subtle</Button>
      <Button variant="whatsapp">WhatsApp</Button>
      <Button size="sm">sm</Button>
      <Button size="lg">lg</Button>
      <Button disabled>Deshabilitado</Button>
    </div>
  ),
};
