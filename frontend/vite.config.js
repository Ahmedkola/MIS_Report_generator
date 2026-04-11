import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [
    react(),
    viteSingleFile(),
  ],
  base: './',
  build: {
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        // CRITICAL FOR FILE:// PROTOCOL:
        // By default, Vite outputs ES Modules (format: 'es'), which browser
        // CORS policies block from executing locally over the file:// scheme,
        // even if the script is inlined. Forcing format to 'iife' compiles the
        // bundle as a classic script, making it perfectly runnable completely offline.
        format: 'iife',
      },
    },
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
