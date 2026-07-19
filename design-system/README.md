# @automatizaesto/design-system

Base de UI reutilizable para los productos SaaS de Automatizaesto
(AgroQuality, Forecast, Automatizaciones IA, marketing y futuros SaaS).

Arquitectura: **un núcleo de componentes + 3 temas de marca**. Los componentes
viven una sola vez; cada producto conserva su paleta y tipografía vía
`data-theme`.

```
packages/
  tokens/   → núcleo (escala, radios, sombras, tipografía) + 3 temas + preset Tailwind
  ui/       → componentes React (primitivas P0)
apps/       → (futuro) marketing, agroquality, forecast
```

## Temas

| Tema           | Fondo  | Acento        | Display  | Producto            |
| -------------- | ------ | ------------- | -------- | ------------------- |
| `corporate`    | oscuro | violeta       | Fraunces | sitio / landing     |
| `forecast`     | claro  | navy + oro    | Fraunces | app Forecast        |
| `agroquality`  | claro  | esmeralda     | Sora     | app AgroQuality     |

El tema por defecto (sin `data-theme`) es `corporate`.

## Uso en una app

```ts
// 1. tokens (una vez, en el entrypoint)
import '@automatizaesto/tokens/index.css';

// 2. tailwind.config.cjs
module.exports = {
  presets: [require('@automatizaesto/tokens/tailwind-preset.cjs')],
  content: ['./src/**/*.{ts,tsx}', '../../packages/ui/src/**/*.{ts,tsx}'],
};
```

```tsx
// 3. activar el tema y usar componentes
import { Button, KpiCard, Table, Badge } from '@automatizaesto/ui';

<html data-theme="agroquality">
  <Button variant="primary">Guardar inspección</Button>
  <KpiCard label="Materia seca" value="23.4" unit="%" delta={{ value: '+1.2', direction: 'up' }} />
  <Badge tone="good">Aprobado</Badge>
</html>;
```

## Componentes incluidos (P0)

`Button`, `Badge`, `Card`, `Input`, `Select`, `Field`, `KpiCard`, `Table`.

Cada uno consolida clases equivalentes de las tres fuentes previas
(`assets/site.css`, las apps Forecast y AgroQuality) en una sola API.

## Instalar y verificar

```bash
cd design-system
pnpm install
pnpm typecheck
```

## Pendiente (próximas iteraciones)

- P0 restante: `Sidebar` + `DashboardShell`, `LoginSplit`.
- P1: `Toast`, `Note`, `ProgressBar`, `Legend`, `Stepper`, `Spinner`.
- Marketing: `NavPill`, `PageHeader`, `CtaBand`, `Prose`.
- Storybook (documenta + habilita `/design-sync` a claude.ai/design).
- Apps: migrar la capa UI de AgroQuality y Forecast (backend FastAPI/Supabase intacto).
