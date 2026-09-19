import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from "rollup-plugin-visualizer";

// https://vite.dev/config/
// FE-01 FIX: add dev proxy + production build optimisations
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    react(),
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
  }
})
