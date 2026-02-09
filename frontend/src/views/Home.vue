<template>
  <div class="home">
    <div class="home-content">
      <h1 class="brand">EasyBook</h1>
      <p class="subtitle">电子书聚合搜索</p>
      <SearchBox
        :title="title"
        :author="author"
        @update:title="title = $event"
        @update:author="author = $event"
        @search="handleSearch"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SearchBox from '@/components/SearchBox.vue'

const router = useRouter()
const title = ref('')
const author = ref('')

function handleSearch() {
  if (title.value.trim() || author.value.trim()) {
    const query: Record<string, string> = {}
    if (title.value.trim()) query.title = title.value.trim()
    if (author.value.trim()) query.author = author.value.trim()
    router.push({ path: '/search', query })
  }
}
</script>

<style scoped>
.home {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.home-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.brand {
  font-size: 48px;
  font-weight: 700;
  margin: 0;
  color: #18a058;
}

.subtitle {
  font-size: 16px;
  color: #666;
  margin: 0 0 16px 0;
}
</style>
