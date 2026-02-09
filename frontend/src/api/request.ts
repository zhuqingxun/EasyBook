import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
console.log('[HTTP] 创建 axios 实例, baseURL:', baseURL)

const http = axios.create({
  baseURL,
  timeout: 60000,
})

http.interceptors.request.use(
  (config) => {
    console.log(`[HTTP] 请求: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config.params || '')
    return config
  },
  (error) => {
    console.error('[HTTP] 请求拦截器错误:', error)
    return Promise.reject(error)
  },
)

http.interceptors.response.use(
  (response) => {
    console.log(
      `[HTTP] 响应: ${response.status} ${response.config.url}`,
      typeof response.data === 'object' ? `(${JSON.stringify(response.data).length} bytes)` : '',
    )
    return response.data
  },
  (error) => {
    console.error(
      '[HTTP] 响应错误:',
      error.response?.status || 'NO_RESPONSE',
      error.config?.url,
      error.message,
    )
    return Promise.reject(error)
  },
)

export default http
