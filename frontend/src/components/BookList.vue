<template>
  <div class="book-list">
    <template v-if="loading">
      <div class="search-progress">
        <n-progress
          type="line"
          :percentage="Math.round(progress)"
          :show-indicator="true"
          :height="16"
          status="success"
          processing
        />
        <p class="progress-hint">正在搜索，请耐心等待...</p>
      </div>
    </template>
    <template v-else-if="results.length > 0">
      <BookItem v-for="book in results" :key="book.id" :book="book" />
    </template>
    <template v-else-if="hasSearched">
      <n-empty description="没有找到相关电子书" />
    </template>
    <n-alert v-if="error" type="error" :title="error" closable style="margin-top: 12px" />
  </div>
</template>

<script setup lang="ts">
import BookItem from './BookItem.vue'
import type { BookResult } from '@/types/search'

defineProps<{
  results: BookResult[]
  loading: boolean
  hasSearched: boolean
  error: string | null
  progress: number
}>()
</script>

<style scoped>
.book-list {
  margin-top: 16px;
}

.search-progress {
  padding: 32px 0;
}

.progress-hint {
  color: #999;
  font-size: 13px;
  text-align: center;
  margin: 12px 0 0 0;
}
</style>
