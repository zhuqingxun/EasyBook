<template>
  <div class="search-box">
    <div class="search-inputs">
      <n-input
        :value="title"
        placeholder="书名"
        size="large"
        clearable
        @update:value="$emit('update:title', $event)"
        @keyup.enter="$emit('search')"
      />
      <n-input
        :value="author"
        placeholder="作者"
        size="large"
        clearable
        @update:value="$emit('update:author', $event)"
        @keyup.enter="$emit('search')"
      />
      <n-button
        type="primary"
        size="large"
        :loading="loading"
        @click="$emit('search')"
      >
        搜索
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  author: string
  loading?: boolean
}>()

defineEmits<{
  'update:title': [value: string]
  'update:author': [value: string]
  search: []
}>()
</script>

<style scoped>
.search-box {
  max-width: 640px;
  width: 100%;
}

.search-inputs {
  display: flex;
  gap: 8px;
}

@media (max-width: 600px) {
  .search-inputs {
    flex-direction: column;
  }
}
</style>
