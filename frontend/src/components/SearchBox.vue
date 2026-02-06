<template>
  <div class="search-box">
    <n-input-group>
      <n-input
        :value="modelValue"
        placeholder="搜索电子书..."
        size="large"
        clearable
        @update:value="$emit('update:modelValue', $event)"
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
    </n-input-group>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  loading?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string]
  search: []
}>()
</script>

<style scoped>
.search-box {
  max-width: 640px;
  width: 100%;
}
</style>
