import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  plugins: [react()],
  server: {
    proxy: {
      '/process': 'http://127.0.0.1:5000',
      '/translate_references': 'http://127.0.0.1:5000',
      '/nearby_pharmacies': 'http://127.0.0.1:5000',
      '/route_to_pharmacy': 'http://127.0.0.1:5000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          motion: ['framer-motion'],
          three: ['three'],
          map: ['leaflet'],
        },
      },
    },
  },
}));
