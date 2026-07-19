import type { Meta, StoryObj } from '@storybook/react';
import { LoginSplit } from './LoginSplit';
import { Field, Input } from '../primitives/Field';
import { Button } from '../primitives/Button';

/** Marca + copy por producto. El tema (data-theme) aporta la paleta;
 *  el contenido viene por props, así que lo derivamos del tema activo
 *  para que la demo sea coherente. */
const BRANDS: Record<string, { mark: string; name: string; title: string; subtitle: string; claim: string; sub: string }> = {
  corporate: {
    mark: 'A',
    name: 'Automatizaesto',
    title: 'Inicia sesión',
    subtitle: 'Accede a tu panel de automatizaciones.',
    claim: 'Automatización con IA para agroexportadoras.',
    sub: 'Menos hojas de cálculo, más decisiones.',
  },
  forecast: {
    mark: 'ƒ',
    name: 'Forecast',
    title: 'Inicia sesión',
    subtitle: 'Accede a tus pronósticos de demanda.',
    claim: 'Pronostica tu demanda con confianza.',
    sub: 'Escenarios e insights por rol, en español.',
  },
  agroquality: {
    mark: 'λ',
    name: 'AgroQuality',
    title: 'Inicia sesión',
    subtitle: 'Accede al panel de auditoría de calidad.',
    claim: 'Auditoría de calidad post-cosecha, sin papeles.',
    sub: 'Inspecciona, califica y reporta desde un solo lugar.',
  },
};

const meta: Meta<typeof LoginSplit> = {
  title: 'Patrones/LoginSplit',
  component: LoginSplit,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof LoginSplit>;

export const Acceso: Story = {
  render: (_args, { globals }) => {
    const b = BRANDS[(globals.theme as string) ?? 'corporate'] ?? BRANDS.corporate;
    return (
      <LoginSplit
        brand={{ mark: b.mark, name: b.name }}
        title={b.title}
        subtitle={b.subtitle}
        showcase={
          <div className="max-w-sm">
            <p className="font-display text-3xl leading-snug">{b.claim}</p>
            <p className="mt-4 opacity-90">{b.sub}</p>
          </div>
        }
        footer="¿Olvidaste tu contraseña?"
      >
        <Field label="Correo">
          <Input type="email" placeholder="tu@empresa.com" />
        </Field>
        <Field label="Contraseña">
          <Input type="password" placeholder="••••••••" />
        </Field>
        <Button block>Entrar</Button>
      </LoginSplit>
    );
  },
};
