import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: "/booking/",
  server: {
    proxy: {
      '/payments': 'http://localhost:8000',
      '/booking/categories': 'http://localhost:8000',
      '/booking/services': 'http://localhost:8000',
      '/booking/slots': 'http://localhost:8000',
      '/booking/staff': 'http://localhost:8000',
      '/booking/create': 'http://localhost:8000',
      '/booking/nearest_slot': 'http://localhost:8000',
      '/booking/booking': 'http://localhost:8000',
    }
  }
})
