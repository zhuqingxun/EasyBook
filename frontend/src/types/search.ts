export interface BookFormat {
  extension: string
  filesize: number | null
  download_url: string
  md5: string
}

export interface BookResult {
  id: string
  title: string
  author: string | null
  formats: BookFormat[]
}

export interface SearchResponse {
  total: number
  page: number
  page_size: number
  results: BookResult[]
  total_books: number
}
