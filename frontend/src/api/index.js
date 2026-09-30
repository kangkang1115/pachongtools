import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

// Backend base URL: set VITE_API_BASE_URL at build time for production (e.g. Render),
// falls back to same-origin '/api' for local dev (Vite proxy).
export const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: API_BASE + '/api',
  timeout: 30000,
})

// Absolute URL for file downloads (browser <a> tag cannot use relative API path
// when frontend and backend are on different origins)
export function fileUrl(path) {
  return API_BASE + path
}

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    }
    return Promise.reject(error)
  }
)

export default api
