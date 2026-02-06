<template>
  <n-card size="small" class="book-item">
    <div class="book-info">
      <h3 class="book-title">{{ book.title }}</h3>
      <p v-if="book.author" class="book-author">{{ book.author }}</p>
    </div>
    <div class="book-formats">
      <n-tooltip
        v-for="fmt in book.formats"
        :key="fmt.extension"
        :disabled="!!fmt.download_url"
      >
        <template #trigger>
          <n-button
            :type="formatColor(fmt.extension)"
            size="small"
            :disabled="!fmt.download_url"
            @click="openDownload(fmt.download_url)"
          >
            {{ fmt.extension.toUpperCase() }}
            <span v-if="fmt.filesize" class="filesize">
              ({{ formatFileSize(fmt.filesize) }})
            </span>
          </n-button>
        </template>
        暂无下载链接
      </n-tooltip>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import type { BookResult } from '@/types/search'

defineProps<{
  book: BookResult
}>()

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

function openDownload(url: string) {
  if (url) {
    window.open(url, '_blank')
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
</style>
