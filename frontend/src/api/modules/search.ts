import http from '../request'
import type { SearchResponse, DownloadResponse } from '@/types/search'

export function searchBooks(params: { q: string; page?: number; page_size?: number }) {
  return http.get<unknown, SearchResponse>('/search', { params })
}

export function getDownloadUrl(md5: string) {
  return http.get<unknown, DownloadResponse>(`/download/${md5}`)
}
