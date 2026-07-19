import type { Preview, Decorator } from '@storybook/react';
import './tailwind.css';

export const globalTypes = {
  theme: {
    description: 'Tema de marca',
    defaultValue: 'corporate',
    toolbar: {
      title: 'Tema',
      icon: 'paintbrush',
      items: [
        { value: 'corporate', title: 'Corporate (marketing)' },
        { value: 'forecast', title: 'Forecast' },
        { value: 'agroquality', title: 'AgroQuality' },
      ],
      dynamicTitle: true,
    },
  },
};

const withTheme: Decorator = (Story, ctx) => {
  const theme = (ctx.globals.theme as string) ?? 'corporate';
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.style.background = 'var(--color-bg)';
  }
  return (
    <div
      data-theme={theme}
      style={{ background: 'var(--color-bg)', color: 'var(--color-ink)', minHeight: '100vh', padding: 24 }}
    >
      <Story />
    </div>
  );
};

const preview: Preview = {
  decorators: [withTheme],
  parameters: {
    layout: 'fullscreen',
    controls: { expanded: true },
  },
};

export default preview;
