/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [require('@automatizaesto/tokens/tailwind-preset.cjs')],
  content: ['./src/**/*.{ts,tsx}', './.storybook/**/*.{ts,tsx}'],
};
