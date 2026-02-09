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
  const query = ref('')
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
      stages[i].status = fresh[i].status
      stages[i].progress = fresh[i].progress
      stages[i].elapsed = fresh[i].elapsed
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
    stages[0].status = 'active'

    tickTimer = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000
      totalElapsed.value = Math.floor(elapsedSec)

      for (let i = 0; i < stages.length; i++) {
        const b = boundaries[i]

        if (elapsedSec >= b.end) {
          // 已超过该阶段预计结束时间 → 完成
          if (stages[i].status !== 'completed') {
            stages[i].status = 'completed'
            stages[i].progress = 100
            stages[i].elapsed = stages[i].estimatedSeconds
          }
        } else if (elapsedSec >= b.start) {
          // 正在此阶段
          if (stages[i].status === 'pending') {
            stages[i].status = 'active'
          }
          const stageElapsed = elapsedSec - b.start
          const duration = b.end - b.start
          stages[i].elapsed = Math.floor(stageElapsed)
          // 进度最高到 95%，防止卡在 99%
          stages[i].progress = Math.min(Math.round((stageElapsed / duration) * 100), 95)
        }
      }

      // 如果所有预定阶段都完成了，最后一个阶段保持 active 状态持续计时
      const lastIdx = stages.length - 1
      if (elapsedSec >= boundaries[lastIdx].end) {
        stages[lastIdx].status = 'active'
        stages[lastIdx].progress = 95
        stages[lastIdx].elapsed = Math.floor(elapsedSec - boundaries[lastIdx].start)
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
      // 搜索成功：把所有阶段标记完成
      let cumulative = 0
      for (let i = 0; i < stages.length; i++) {
        const estimated = STAGE_DEFS[i].estimatedSeconds
        if (stages[i].status !== 'completed') {
          // 按比例分配实际耗时
          stages[i].elapsed = i === stages.length - 1
            ? Math.max(totalElapsed.value - cumulative, 0)
            : estimated
        }
        stages[i].status = 'completed'
        stages[i].progress = 100
        cumulative += stages[i].elapsed
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
    if (!query.value.trim()) {
      return
    }

    loading.value = true
    error.value = null
    startProgress()

    try {
      const data = await searchBooks({
        q: query.value.trim(),
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
    query,
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
