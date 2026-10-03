import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from "rollup-plugin-visualizer";

// Legacy page/component CSS goes into a `legacy` cascade layer that sits below Tailwind utilities,
// so utility classes on an element always win over old class rules. Tokens and base stay unlayered.
const legacyLayer = () => ({
  name: 'legacy-css-layer',
  enforce: 'pre',
  transform(code, id) {
    const file = id.split('?')[0].split(String.fromCharCode(92)).join('/');
    if (!file.endsWith('.css') || !file.includes('/src/')) return null;
    if (['index', 'tokens', 'base'].some((n) => file.endsWith('/src/styles/' + n + '.css'))) return null;
    return { code: '@layer legacy {' + String.fromCharCode(10) + code + String.fromCharCode(10) + '}', map: null };
  },
});

// https://vite.dev/config/
// FE-01 FIX: add dev proxy + production build optimisations
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    legacyLayer(),
    react(),
    tailwindcss(),
    visualizer({ filename: "stats.html", open: false })
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // SSE stream — must NOT compress or buffer, otherwise events are held
      // until the connection closes and real-time delivery is lost.
      '/api/notifications/stream': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        compress: false,        // No gzip — SSE frames must flush immediately
      },
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      }
    }
  },

  build: {
    sourcemap: false,            // No source maps in production builds
    chunkSizeWarningLimit: 500,  // Warn on chunks > 500KB
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.js'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
  }
})

