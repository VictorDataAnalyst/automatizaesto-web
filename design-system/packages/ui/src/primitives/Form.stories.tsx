import type { Meta, StoryObj } from '@storybook/react';
import { Card, CardTitle } from './Card';
import { Field, Input, Select } from './Field';
import { Button } from './Button';

const meta: Meta = {
  title: 'Primitivas/Formulario',
};
export default meta;
type Story = StoryObj;

export const FichaInspeccion: Story = {
  render: () => (
    <Card className="max-w-md">
      <CardTitle>Nueva inspección</CardTitle>
      <div className="mt-5 flex flex-col gap-4">
        <Field label="Código de lote" required hint="Formato EMP001-2026">
          <Input placeholder="EMP001-2026-014" />
        </Field>
        <Field label="Cultivo">
          <Select defaultValue="">
            <option value="" disabled>
              Selecciona…
            </option>
            <option>Arándano</option>
            <option>Uva</option>
            <option>Palta</option>
          </Select>
        </Field>
        <Field label="Materia seca (%)" error="Debe ser mayor a 0">
          <Input type="number" defaultValue={-1} />
        </Field>
        <Button block>Registrar</Button>
      </div>
    </Card>
  ),
};
