import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // During development the API runs separately on :8000
    proxy: {
      '/api': { target: 'http://localhost:8000', ws: true },
    },
  },
})
