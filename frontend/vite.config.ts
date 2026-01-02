import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
    plugins: [react()],
    base: isBackend ? '/app/' : '/',
    build: {
      outDir: isBackend ? '../app' : 'dist',
      emptyOutDir: true,
    },
  }
})
