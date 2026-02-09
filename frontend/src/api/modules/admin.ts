import http from '../request'

export interface LoginResponse {
  token: string
}

export interface SearchTermItem {
  term: string
  count: number
}

export interface HourlyPV {
  hour: string
  count: number
}

export interface DailyPV {
  date: string
  count: number
}

export interface StatsResponse {
  search_count: number
  top_search_terms: SearchTermItem[]
  avg_response_time: number
  total_pv: number
  unique_visitors: number
  hourly_pv: HourlyPV[]
  daily_pv: DailyPV[]
}

export interface CacheStats {
  size: number
  max_size: number
  hits: number
  misses: number
  hit_rate: number
}

export interface SystemResponse {
  duckdb: {
    initialized: boolean
    mode: string
    parquet_path: string
  }
  cache: CacheStats
  memory: {
    rss_mb: number
    vms_mb: number
  }
}

function authHeader(token: string) {
  return { headers: { Authorization: `Bearer ${token}` } }
}

export function adminLogin(password: string): Promise<LoginResponse> {
  return http.post('/admin/login', { password })
}

export function getStats(token: string): Promise<StatsResponse> {
  return http.get('/admin/stats', authHeader(token))
}

export function getSystemStatus(token: string): Promise<SystemResponse> {
  return http.get('/admin/system', authHeader(token))
}

export function getCacheStats(token: string): Promise<CacheStats> {
  return http.get('/admin/cache', authHeader(token))
}

export function clearCache(token: string): Promise<{ message: string }> {
  return http.delete('/admin/cache', authHeader(token))
}
