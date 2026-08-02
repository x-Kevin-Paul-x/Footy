import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    define: {
      'process.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL ?? ''),
      'process.env.VITE_API_TIMEOUT_MS': JSON.stringify(env.VITE_API_TIMEOUT_MS ?? ''),
    },
  }
})
