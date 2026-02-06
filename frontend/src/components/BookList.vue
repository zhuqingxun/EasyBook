<template>
  <div class="book-list">
    <n-spin :show="loading">
      <template v-if="results.length > 0">
        <BookItem v-for="book in results" :key="book.id" :book="book" />
      </template>
      <template v-else-if="hasSearched && !loading">
        <n-empty description="没有找到相关电子书" />
      </template>
    </n-spin>
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
}>()
</script>

<style scoped>
.book-list {
  margin-top: 16px;
}
</style>
