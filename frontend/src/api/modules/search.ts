import http from '../request'
import type { SearchResponse } from '@/types/search'

export function searchBooks(params: {
  q?: string
  title?: string
  author?: string
  page?: number
  page_size?: number
}) {
  return http.get<unknown, SearchResponse>('/search', { params })
}
