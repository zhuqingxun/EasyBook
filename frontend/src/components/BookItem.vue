<template>
  <n-card size="small" class="book-item">
    <div class="book-info">
      <h3 class="book-title">{{ book.title }}</h3>
      <p v-if="book.author" class="book-author">{{ book.author }}</p>
    </div>
    <div class="book-formats">
      <n-popover
        v-for="fmt in book.formats"
        :key="fmt.md5"
        trigger="click"
        placement="bottom"
        :style="{ maxWidth: '280px' }"
      >
        <template #trigger>
          <n-button
            :type="formatColor(fmt.extension)"
            size="small"
            :disabled="!fmt.md5"
          >
            {{ fmt.extension.toUpperCase() }}
            <span v-if="fmt.filesize" class="filesize">
              ({{ formatFileSize(fmt.filesize) }})
            </span>
          </n-button>
        </template>
        <div class="download-sources">
          <div class="download-sources-title">选择下载来源</div>
          <div class="download-sources-list">
            <n-button
              v-for="source in getDownloadSources(fmt)"
              :key="source.name"
              size="small"
              quaternary
              block
              tag="a"
              :href="source.url"
              target="_blank"
              rel="noopener noreferrer"
              class="source-btn"
            >
              {{ source.name }}
            </n-button>
          </div>
        </div>
      </n-popover>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import type { BookResult, BookFormat } from '@/types/search'

const props = defineProps<{
  book: BookResult
}>()

interface DownloadSource {
  name: string
  url: string
}

const ANNAS_ARCHIVE_URL = import.meta.env.VITE_ANNAS_ARCHIVE_URL || 'https://zh.annas-archive.li'

function getDownloadSources(fmt: BookFormat): DownloadSource[] {
  const md5 = fmt.md5
  if (!md5) return []

  const sources: DownloadSource[] = [
    {
      name: "Anna's Archive",
      url: `${ANNAS_ARCHIVE_URL}/slow_download/${md5}/0/0`,
    },
    {
      name: '鸠摩搜索 (搜索)',
      url: 'https://www.jiumodiary.com/',
    },
    {
      name: '24h搜书 (搜索)',
      url: `https://24hbook.store/search?keyword=${encodeURIComponent(props.book.title)}`,
    },
  ]

  return sources
}

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

.download-sources {
  min-width: 180px;
}

.download-sources-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.download-sources-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-btn {
  justify-content: flex-start;
  text-decoration: none;
}
</style>
