import { ref, reactive, onUnmounted } from 'vue'
import { searchBooks } from '@/api/modules/search'
import type { BookResult } from '@/types/search'

export interface SearchStage {
  label: string
  estimatedSeconds: number
  status: 'pending' | 'active' | 'completed'
  progress: number
  elapsed: number
}

const STAGE_DEFS = [
  { label: '连接搜索服务', estimatedSeconds: 3 },
  { label: '扫描数据库', estimatedSeconds: 12 },
  { label: '匹配 5900 万条记录', estimatedSeconds: 35 },
  { label: '整理搜索结果', estimatedSeconds: 15 },
]

function createStages(): SearchStage[] {
  return STAGE_DEFS.map((d) => ({
    label: d.label,
    estimatedSeconds: d.estimatedSeconds,
    status: 'pending' as const,
    progress: 0,
    elapsed: 0,
  }))
}

export function useSearch() {
  const title = ref('')
  const author = ref('')
  const results = ref<BookResult[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasSearched = ref(false)
  const totalElapsed = ref(0)
  const stages = reactive<SearchStage[]>(createStages())

  let tickTimer: ReturnType<typeof setInterval> | null = null
  let startTime = 0

  function resetStages() {
    const fresh = createStages()
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i]
      const f = fresh[i]
      if (!s || !f) continue
      s.status = f.status
      s.progress = f.progress
      s.elapsed = f.elapsed
    }
  }

  function startProgress() {
    resetStages()
    totalElapsed.value = 0
    startTime = Date.now()

    // 预计算每个阶段的起止时间
    let cumulative = 0
    const boundaries = STAGE_DEFS.map((d) => {
      const start = cumulative
      cumulative += d.estimatedSeconds
      return { start, end: cumulative }
    })

    // 激活第一个阶段
    if (stages[0]) stages[0].status = 'active'

    tickTimer = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000
      totalElapsed.value = Math.floor(elapsedSec)

      for (let i = 0; i < stages.length; i++) {
        const s = stages[i]
        const b = boundaries[i]
        if (!s || !b) continue

        if (elapsedSec >= b.end) {
          if (s.status !== 'completed') {
            s.status = 'completed'
            s.progress = 100
            s.elapsed = s.estimatedSeconds
          }
        } else if (elapsedSec >= b.start) {
          if (s.status === 'pending') {
            s.status = 'active'
          }
          const stageElapsed = elapsedSec - b.start
          const duration = b.end - b.start
          s.elapsed = Math.floor(stageElapsed)
          s.progress = Math.min(Math.round((stageElapsed / duration) * 100), 95)
        }
      }

      // 如果所有预定阶段都完成了，最后一个阶段保持 active 状态持续计时
      const lastStage = stages[stages.length - 1]
      const lastBound = boundaries[boundaries.length - 1]
      if (lastStage && lastBound && elapsedSec >= lastBound.end) {
        lastStage.status = 'active'
        lastStage.progress = 95
        lastStage.elapsed = Math.floor(elapsedSec - lastBound.start)
      }
    }, 500)
  }

  function stopProgress(success: boolean) {
    if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }
    totalElapsed.value = Math.floor((Date.now() - startTime) / 1000)

    if (success) {
      let cumulative = 0
      for (let i = 0; i < stages.length; i++) {
        const s = stages[i]
        const def = STAGE_DEFS[i]
        if (!s || !def) continue
        if (s.status !== 'completed') {
          s.elapsed = i === stages.length - 1
            ? Math.max(totalElapsed.value - cumulative, 0)
            : def.estimatedSeconds
        }
        s.status = 'completed'
        s.progress = 100
        cumulative += s.elapsed
      }
    }
  }

  onUnmounted(() => {
    if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }
  })

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
    if (!title.value.trim() && !author.value.trim()) {
      return
    }

    loading.value = true
    error.value = null
    startProgress()

    try {
      const data = await searchBooks({
        title: title.value.trim() || undefined,
        author: author.value.trim() || undefined,
        page: page.value,
        page_size: pageSize.value,
      })
      stopProgress(true)
      results.value = data.results ?? []
      total.value = data.total ?? 0
      hasSearched.value = true
    } catch (e: unknown) {
      stopProgress(false)
      error.value = friendlyErrorMessage(e)
      results.value = []
      total.value = 0
      hasSearched.value = true
      console.error('[Search] 搜索失败:', e)
    } finally {
      loading.value = false
    }
  }

  const changePage = (newPage: number) => {
    page.value = newPage
    search()
  }

  return {
    title,
    author,
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    hasSearched,
    stages,
    totalElapsed,
    search,
    changePage,
  }
}
