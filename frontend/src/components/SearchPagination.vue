<template>
  <div v-if="total > pageSize" class="pagination-wrapper">
    <n-pagination
      :page="page"
      :page-size="pageSize"
      :item-count="total"
      show-quick-jumper
      @update:page="$emit('update:page', $event)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  total: number
}>()

defineEmits<{
  'update:page': [page: number]
}>()
</script>

<style scoped>
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-bottom: 24px;
}
</style>
