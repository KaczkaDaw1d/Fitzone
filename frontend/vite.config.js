import { defineConfig } from 'vite';
export default defineConfig({
  base: '/static/app/',
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/admin': 'http://127.0.0.1:8000', '/static/admin': 'http://127.0.0.1:8000' } },
  build: { outDir: '../backend/frontend_dist', emptyOutDir: true },
});
