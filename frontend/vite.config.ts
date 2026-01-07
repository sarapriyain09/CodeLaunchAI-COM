import { defineConfig } from 'vite'
import { resolve } from 'node:path'

// https://vite.dev/config/
//
// This repo supports two build targets:
// - mode=backend: build output goes to repo-level ../app and uses base '/app/'
//                (served by the FastAPI backend at /app/)
// - default (static): build output goes to ./dist and uses base '/'
//                     (deploy to Vercel/Netlify/static hosting)
export default defineConfig(({ mode }) => {
  const isBackend = mode === 'backend'

  return {
    base: isBackend ? '/app/' : '/',
    build: {
      outDir: isBackend ? '../app' : 'dist',
      emptyOutDir: true,
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'index.html'),
          dashboard: resolve(__dirname, 'dashboard.html'),
        },
      },
    },
  }
})
