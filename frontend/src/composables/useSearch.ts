import { ref } from 'vue'
import { searchBooks } from '@/api/modules/search'
import type { BookResult } from '@/types/search'

export function useSearch() {
  const query = ref('')
  const results = ref<BookResult[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasSearched = ref(false)

  const search = async () => {
    if (!query.value.trim()) {
      console.log('[Search] 搜索词为空，跳过')
      return
    }

    console.log(`[Search] 开始搜索: q="${query.value}", page=${page.value}, pageSize=${pageSize.value}`)
    loading.value = true
    error.value = null

    try {
      const data = await searchBooks({
        q: query.value.trim(),
        page: page.value,
        page_size: pageSize.value,
      })
      results.value = data.results
      total.value = data.total
      hasSearched.value = true
      console.log(`[Search] 搜索成功: total=${data.total}, results=${data.results.length}`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Search failed'
      error.value = msg
      results.value = []
      total.value = 0
      console.error('[Search] 搜索失败:', msg, e)
    } finally {
      loading.value = false
    }
  }

  const changePage = (newPage: number) => {
    console.log(`[Search] 翻页: ${page.value} -> ${newPage}`)
    page.value = newPage
    search()
  }

  return {
    query,
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    hasSearched,
    search,
    changePage,
  }
}
