import { ref, onUnmounted } from 'vue'
import { searchBooks } from '@/api/modules/search'
import type { BookResult } from '@/types/search'

const PROGRESS_DURATION = 60000
const PROGRESS_INTERVAL = 300
const PROGRESS_MAX = 95

export function useSearch() {
  const query = ref('')
  const results = ref<BookResult[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasSearched = ref(false)
  const progress = ref(0)

  let progressTimer: ReturnType<typeof setInterval> | null = null

  function startProgress() {
    progress.value = 0
    const step = (PROGRESS_MAX * PROGRESS_INTERVAL) / PROGRESS_DURATION
    progressTimer = setInterval(() => {
      if (progress.value < PROGRESS_MAX) {
        progress.value = Math.min(progress.value + step, PROGRESS_MAX)
      }
    }, PROGRESS_INTERVAL)
  }

  function stopProgress() {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    progress.value = 100
  }

  onUnmounted(() => {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
  })

  const search = async () => {
    if (!query.value.trim()) {
      console.log('[Search] 搜索词为空，跳过')
      return
    }

    console.log(`[Search] 开始搜索: q="${query.value}", page=${page.value}, pageSize=${pageSize.value}`)
    loading.value = true
    error.value = null
    startProgress()

    try {
      const data = await searchBooks({
        q: query.value.trim(),
        page: page.value,
        page_size: pageSize.value,
      })
      results.value = data.results ?? []
      total.value = data.total ?? 0
      hasSearched.value = true
      console.log(`[Search] 搜索成功: total=${data.total}, results=${results.value.length}`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Search failed'
      error.value = msg
      results.value = []
      total.value = 0
      hasSearched.value = true
      console.error('[Search] 搜索失败:', msg, e)
    } finally {
      stopProgress()
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
    progress,
    search,
    changePage,
  }
}
