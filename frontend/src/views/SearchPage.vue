<template>
  <div class="search-page">
    <div class="search-header">
      <h2 class="brand-small" @click="goHome">EasyBook</h2>
      <SearchBox
        v-model:model-value="query"
        :loading="loading"
        @search="handleSearch"
      />
    </div>
    <div class="search-results">
      <p v-if="hasSearched && !loading" class="result-count">
        找到 {{ total }} 条结果
      </p>
      <BookList
        :results="results"
        :loading="loading"
        :has-searched="hasSearched"
        :error="error"
        :progress="progress"
      />
      <SearchPagination
        :page="page"
        :page-size="pageSize"
        :total="total"
        @update:page="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchBox from '@/components/SearchBox.vue'
import BookList from '@/components/BookList.vue'
import SearchPagination from '@/components/SearchPagination.vue'
import { useSearch } from '@/composables/useSearch'

const route = useRoute()
const router = useRouter()
const { query, results, total, page, pageSize, loading, error, hasSearched, progress, search, changePage } =
  useSearch()

function handleSearch() {
  if (query.value.trim()) {
    page.value = 1
    router.push({ path: '/search', query: { q: query.value.trim(), page: '1' } })
    search()
  }
}

function handlePageChange(newPage: number) {
  router.push({ path: '/search', query: { q: query.value, page: String(newPage) } })
  changePage(newPage)
}

function goHome() {
  router.push('/')
}

watch(
  () => route.query,
  () => {
    const q = route.query.q as string
    const p = parseInt(route.query.page as string) || 1
    if (q && (q !== query.value || p !== page.value)) {
      query.value = q
      page.value = p
      search()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.search-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px;
}

.search-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.brand-small {
  font-size: 24px;
  font-weight: 700;
  color: #18a058;
  margin: 0;
  cursor: pointer;
  white-space: nowrap;
}

.result-count {
  color: #999;
  font-size: 14px;
  margin: 0 0 8px 0;
}
</style>
