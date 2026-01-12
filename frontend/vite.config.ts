import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import os from 'os'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  // Use temp directory for cache to avoid Dropbox file locking issues on Windows
  cacheDir: path.join(os.tmpdir(), 'vite-cache-retirement-lab')
})

