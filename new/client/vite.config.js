import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from "rollup-plugin-visualizer";
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// On Windows, esbuild temp file cleanup in AppData/Local/Temp can trigger Access Denied errors
// due to antivirus or file indexer locks. Directing TEMP to a project-local .tmp directory resolves this.
if (process.platform === 'win32') {
  const localTmp = path.resolve(__dirname, '.tmp');
  if (!fs.existsSync(localTmp)) {
    try {
      fs.mkdirSync(localTmp, { recursive: true });
    } catch {
      // ignore
    }
  }
  process.env.TEMP = localTmp;
  process.env.TMP = localTmp;
}

// https://vite.dev/config/
// FE-01 FIX: add dev proxy + production build optimisations
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    react(),
    tailwindcss(),
    visualizer({ filename: "stats.html", open: false })
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api/notifications/stream': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        compress: false,
      },
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      }
    }
  },

  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: false,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          export: ['jspdf', 'html2canvas'],
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
  }
})
