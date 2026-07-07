import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './'  -> Assets relativ, damit das Bundle vom Plugin-Server (localhost)
// ausgeliefert werden kann. build.outDir -> src/web (deploy.ps1 kopiert es ins Plugin).
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: '../src/web',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8787',
    },
  },
})
