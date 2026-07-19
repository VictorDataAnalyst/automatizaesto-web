/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [require('@automatizaesto/tokens/tailwind-preset.cjs')],
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
};
