import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// El backend FastAPI corre en :8603 (ver .claude/launch.json "agroquality").
// En dev, proxyeamos /api hacia él para reutilizar la API y la auth existentes.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8603', changeOrigin: true },
    },
  },
});
