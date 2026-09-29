import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'axios',
      'i18next',
      'react-i18next',
      'recharts',
      'leaflet',
      'react-leaflet',
      'leaflet-draw',
      'three',
      '@react-three/fiber',
      '@react-three/drei',
      'jspdf',
      'docx',
      'file-saver',
      'xlsx',
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_INTERNAL_URL || 'http://backend:8000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_BACKEND_INTERNAL_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          leaflet: ['leaflet', 'react-leaflet', 'leaflet-draw'],
          charts: ['recharts'],
          documents: ['jspdf', 'docx', 'file-saver'],
        },
      },
    },
  },
})
