import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:10000',
      '/agent': 'http://localhost:10000',
      '/webhook': 'http://localhost:10000',
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
