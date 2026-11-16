import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(fileURLToPath(import.meta.url))
const wing = path.resolve(process.env.ONTOWING_FRONTEND || path.join(root, '../../ontowing/frontend/src'))

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@wing': wing }, dedupe: ['react', 'react-dom'] },
  server: {
    host: '127.0.0.1',
    port: 4180,
    strictPort: true,
    fs: { allow: [root, wing] },
  },
  preview: {
    host: '127.0.0.1',
    port: 4180,
    strictPort: true,
  },
  build: { chunkSizeWarningLimit: 1500 },
})
