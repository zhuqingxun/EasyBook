<template>
  <n-card size="small" class="book-item">
    <div class="book-info">
      <h3 class="book-title">{{ book.title }}</h3>
      <p v-if="book.author" class="book-author">{{ book.author }}</p>
    </div>
    <div class="book-formats">
      <n-button
        v-for="fmt in book.formats"
        :key="fmt.extension"
        :type="formatColor(fmt.extension)"
        size="small"
        :disabled="!fmt.download_url"
        :loading="loadingMd5 === fmt.md5"
        @click="handleDownload(fmt)"
      >
        {{ fmt.extension.toUpperCase() }}
        <span v-if="fmt.filesize" class="filesize">
          ({{ formatFileSize(fmt.filesize) }})
        </span>
      </n-button>
    </div>

    <n-modal
      :show="showModal"
      preset="card"
      :title="`下载: ${modalTitle}`"
      style="width: 520px; max-width: 90vw"
      :mask-closable="true"
      @update:show="showModal = $event"
    >
      <div class="gateway-list">
        <div
          v-for="gw in gatewayResults"
          :key="gw.url"
          class="gateway-row"
          :class="{ 'gateway-available': gw.status === 'ok' }"
        >
          <span class="gateway-icon">
            <n-spin v-if="gw.status === 'checking'" :size="14" />
            <span v-else-if="gw.status === 'ok'" style="color: #18a058">&#10003;</span>
            <span v-else style="color: #d03050">&#10007;</span>
          </span>
          <span class="gateway-name">{{ gw.name }}</span>
          <span class="gateway-latency">
            <template v-if="gw.status === 'checking'">检测中...</template>
            <template v-else-if="gw.status === 'ok'">{{ gw.latency }}ms</template>
            <template v-else>{{ gw.error }}</template>
          </span>
          <n-button
            v-if="gw.status === 'ok'"
            size="tiny"
            type="primary"
            :loading="downloadingUrl === gw.url"
            @click="openDownload(gw.url)"
          >
            {{ downloadingUrl === gw.url ? '下载中' : '下载' }}
          </n-button>
        </div>
      </div>
      <template #footer>
        <div style="text-align: right">
          <n-button @click="showModal = false">关闭</n-button>
        </div>
      </template>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import type { BookResult, BookFormat } from '@/types/search'
import { getDownloadUrl } from '@/api/modules/search'

interface GatewayResult {
  url: string
  name: string
  status: 'checking' | 'ok' | 'fail'
  latency?: number
  error?: string
}

const props = defineProps<{
  book: BookResult
}>()

const message = useMessage()
const loadingMd5 = ref('')
const showModal = ref(false)
const modalTitle = ref('')
const gatewayResults = ref<GatewayResult[]>([])
const currentExtension = ref('')
const downloadingUrl = ref('')

function formatColor(ext: string): 'success' | 'error' | 'info' | 'warning' {
  const colors: Record<string, 'success' | 'error' | 'info' | 'warning'> = {
    epub: 'success',
    pdf: 'error',
    mobi: 'info',
    azw3: 'warning',
  }
  return colors[ext] || 'info'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function extractGatewayName(url: string): string {
  try {
    const hostname = new URL(url).hostname
    return hostname
  } catch {
    return url
  }
}

async function checkGateway(gw: GatewayResult): Promise<void> {
  const start = performance.now()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 5000)

  try {
    const response = await fetch(gw.url, {
      method: 'HEAD',
      mode: 'cors',
      signal: controller.signal,
    })
    clearTimeout(timer)
    const latency = Math.round(performance.now() - start)

    if (response.ok) {
      gw.status = 'ok'
      gw.latency = latency
    } else {
      gw.status = 'fail'
      gw.error = `HTTP ${response.status}`
    }
  } catch {
    clearTimeout(timer)
    gw.status = 'fail'
    gw.error = '超时'
  }
}

async function handleDownload(fmt: BookFormat) {
  if (!fmt.md5) return
  loadingMd5.value = fmt.md5

  try {
    const resp = await getDownloadUrl(fmt.md5)
    const allUrls = [resp.download_url, ...resp.alternatives]

    modalTitle.value = fmt.extension.toUpperCase()
    currentExtension.value = fmt.extension
    gatewayResults.value = allUrls.map((url) => ({
      url,
      name: extractGatewayName(url),
      status: 'checking' as const,
    }))

    showModal.value = true

    // 并发检测所有网关
    await Promise.allSettled(gatewayResults.value.map(checkGateway))
  } catch {
    message.error('获取下载链接失败')
  } finally {
    loadingMd5.value = ''
  }
}

async function openDownload(baseUrl: string) {
  const filename = `${props.book.title}.${currentExtension.value}`
  downloadingUrl.value = baseUrl

  try {
    const response = await fetch(baseUrl, { mode: 'cors' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)
  } catch {
    message.error('下载失败，请尝试其他网关')
  } finally {
    downloadingUrl.value = ''
  }
}
</script>

<style scoped>
.book-item {
  margin-bottom: 12px;
}

.book-info {
  margin-bottom: 8px;
}

.book-title {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
}

.book-author {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.book-formats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filesize {
  margin-left: 4px;
  font-size: 12px;
  opacity: 0.8;
}

.gateway-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gateway-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #f9f9f9;
}

.gateway-available {
  background: #f0faf4;
}

.gateway-icon {
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.gateway-name {
  flex: 1;
  font-family: monospace;
  font-size: 13px;
}

.gateway-latency {
  font-size: 12px;
  color: #999;
  min-width: 70px;
  text-align: right;
}
</style>
