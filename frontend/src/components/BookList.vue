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
        <p class="progress-stage">{{ stage }}</p>
        <p class="progress-elapsed">已等待 {{ elapsed }} 秒</p>
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
  elapsed: number
  stage: string
}>()
</script>

<style scoped>
.book-list {
  margin-top: 16px;
}

.search-progress {
  padding: 32px 0;
}

.progress-stage {
  color: #666;
  font-size: 14px;
  text-align: center;
  margin: 12px 0 0 0;
}

.progress-elapsed {
  color: #aaa;
  font-size: 12px;
  text-align: center;
  margin: 6px 0 0 0;
}
</style>
