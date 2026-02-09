import { ref, computed, onUnmounted } from 'vue'
import { searchBooks } from '@/api/modules/search'
import type { BookResult } from '@/types/search'

const PROGRESS_DURATION = 180000
const PROGRESS_INTERVAL = 300
const PROGRESS_MAX = 95
const ELAPSED_INTERVAL = 1000

const STAGE_THRESHOLDS = [
  { seconds: 0, label: '正在连接搜索服务...' },
  { seconds: 5, label: '正在扫描数据库...' },
  { seconds: 15, label: '正在匹配 5900 万条记录...' },
  { seconds: 40, label: '正在整理搜索结果...' },
  { seconds: 60, label: '查询时间较长，请耐心等待...' },
] as const

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
  const elapsed = ref(0)

  const stage = computed(() => {
    let current: string = STAGE_THRESHOLDS[0].label
    for (const t of STAGE_THRESHOLDS) {
      if (elapsed.value >= t.seconds) {
        current = t.label
      }
    }
    return current
  })

  let progressTimer: ReturnType<typeof setInterval> | null = null
  let elapsedTimer: ReturnType<typeof setInterval> | null = null

  function startProgress() {
    progress.value = 0
    elapsed.value = 0
    const step = (PROGRESS_MAX * PROGRESS_INTERVAL) / PROGRESS_DURATION
    progressTimer = setInterval(() => {
      if (progress.value < PROGRESS_MAX) {
        progress.value = Math.min(progress.value + step, PROGRESS_MAX)
      }
    }, PROGRESS_INTERVAL)
    elapsedTimer = setInterval(() => {
      elapsed.value += 1
    }, ELAPSED_INTERVAL)
  }

  function stopProgress() {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
    progress.value = 100
  }

  function clearTimers() {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }

  onUnmounted(clearTimers)

  function friendlyErrorMessage(e: unknown): string {
    if (e instanceof Error) {
      const msg = e.message
      if (msg.includes('timeout') || msg.includes('Timeout')) {
        return '搜索请求超时，请稍后重试或尝试更精确的关键词'
      }
      if (msg.includes('Network Error') || msg.includes('ERR_NETWORK')) {
        return '网络连接失败，请检查网络后重试'
      }
      if (msg.includes('500') || msg.includes('Internal Server Error')) {
        return '服务器内部错误，请稍后重试'
      }
    }
    return '搜索失败，请稍后重试'
  }

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
      error.value = friendlyErrorMessage(e)
      results.value = []
      total.value = 0
      hasSearched.value = true
      console.error('[Search] 搜索失败:', e)
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
    elapsed,
    stage,
    search,
    changePage,
  }
}
