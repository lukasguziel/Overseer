import { defineConfig, configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'

// base './' -> relative asset URLs so the bundle can be served by the plugin
// server (localhost). build.outDir -> src/web (deploy.ps1 copies it into the plugin).
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
  test: {
    // e2e/*.spec.ts are Playwright tests (their own runner + config) —
    // vitest must not try to collect them.
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
