<template>
  <div class="search-page">
    <div class="search-header">
      <h2 class="brand-small" @click="goHome">EasyBook</h2>
      <SearchBox
        :title="title"
        :author="author"
        :loading="loading"
        @update:title="title = $event"
        @update:author="author = $event"
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
        :stages="stages"
        :total-elapsed="totalElapsed"
      />
      <SearchPagination
        v-if="!loading && results.length > 0"
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
const { title, author, results, total, page, pageSize, loading, error, hasSearched, stages, totalElapsed, search, changePage } =
  useSearch()

function handleSearch() {
  if (title.value.trim() || author.value.trim()) {
    page.value = 1
    const query: Record<string, string> = { page: '1' }
    if (title.value.trim()) query.title = title.value.trim()
    if (author.value.trim()) query.author = author.value.trim()
    router.push({ path: '/search', query })
    search()
  }
}

function handlePageChange(newPage: number) {
  const query: Record<string, string> = { page: String(newPage) }
  if (title.value.trim()) query.title = title.value.trim()
  if (author.value.trim()) query.author = author.value.trim()
  router.push({ path: '/search', query })
  changePage(newPage)
}

function goHome() {
  router.push('/')
}

watch(
  () => route.query,
  () => {
    const t = (route.query.title as string) || ''
    const a = (route.query.author as string) || ''
    const p = parseInt(route.query.page as string) || 1
    if ((t || a) && (t !== title.value || a !== author.value || p !== page.value)) {
      title.value = t
      author.value = a
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
