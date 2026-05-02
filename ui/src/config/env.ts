// Simple environment config - single source of truth
const env = import.meta.env

export const CONFIG = {
  API_BASE_URL: env.VITE_API_BASE_URL || 'http://localhost:8000',
  APP_NAME: 'FinOps Console',
  VERSION: '0.1.0',
}

export default CONFIG