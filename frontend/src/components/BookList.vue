<template>
  <div class="book-list">
    <template v-if="loading || showCompletedStages">
      <div class="search-progress">
        <div
          v-for="(s, i) in stages"
          :key="i"
          class="stage-row"
          :class="{ 'stage-pending': s.status === 'pending', 'stage-active': s.status === 'active', 'stage-completed': s.status === 'completed' }"
        >
          <div class="stage-header">
            <span class="stage-icon">
              <template v-if="s.status === 'completed'">&#10003;</template>
              <template v-else-if="s.status === 'active'">&#9679;</template>
              <template v-else>&#9675;</template>
            </span>
            <span class="stage-label">{{ s.label }}</span>
            <span class="stage-time">
              <template v-if="s.status === 'completed'">{{ s.elapsed }}s</template>
              <template v-else-if="s.status === 'active'">{{ s.elapsed }}s / ~{{ s.estimatedSeconds }}s</template>
            </span>
          </div>
          <div v-if="s.status !== 'pending'" class="stage-bar">
            <div
              class="stage-bar-fill"
              :class="{ 'bar-active': s.status === 'active', 'bar-completed': s.status === 'completed' }"
              :style="{ width: s.progress + '%' }"
            />
            <span v-if="s.status === 'active'" class="stage-percent">{{ s.progress }}%</span>
          </div>
        </div>
        <div v-if="allCompleted" class="stage-summary">
          搜索完成，总耗时 {{ totalElapsed }} 秒
        </div>
      </div>
    </template>
    <template v-if="!loading">
      <template v-if="results.length > 0">
        <BookItem v-for="book in results" :key="book.id" :book="book" />
      </template>
      <template v-else-if="hasSearched && !allCompleted">
        <n-empty description="没有找到相关电子书" />
      </template>
    </template>
    <n-alert v-if="error" type="error" :title="error" closable style="margin-top: 12px" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BookItem from './BookItem.vue'
import type { BookResult } from '@/types/search'
import type { SearchStage } from '@/composables/useSearch'

const props = defineProps<{
  results: BookResult[]
  loading: boolean
  hasSearched: boolean
  error: string | null
  stages: SearchStage[]
  totalElapsed: number
}>()

const allCompleted = computed(() =>
  props.stages.length > 0 && props.stages.every((s) => s.status === 'completed'),
)

const showCompletedStages = computed(() =>
  allCompleted.value && props.hasSearched,
)
</script>

<style scoped>
.book-list {
  margin-top: 16px;
}

.search-progress {
  padding: 16px 0;
}

.stage-row {
  margin-bottom: 12px;
  transition: opacity 0.3s;
}

.stage-pending {
  opacity: 0.4;
}

.stage-header {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  font-size: 13px;
}

.stage-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.stage-completed .stage-icon {
  color: #18a058;
  font-weight: bold;
}

.stage-active .stage-icon {
  color: #2080f0;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.stage-label {
  flex: 1;
  color: #333;
}

.stage-pending .stage-label {
  color: #aaa;
}

.stage-time {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
  flex-shrink: 0;
}

.stage-completed .stage-time {
  color: #18a058;
}

.stage-bar {
  position: relative;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  margin-left: 20px;
  overflow: hidden;
}

.stage-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.bar-active {
  background: linear-gradient(90deg, #2080f0, #36ad6a);
  animation: shimmer 1.5s infinite;
}

.bar-completed {
  background: #18a058;
}

@keyframes shimmer {
  0% { opacity: 0.8; }
  50% { opacity: 1; }
  100% { opacity: 0.8; }
}

.stage-percent {
  position: absolute;
  right: 4px;
  top: -16px;
  font-size: 11px;
  color: #2080f0;
}

.stage-summary {
  text-align: center;
  color: #18a058;
  font-size: 14px;
  font-weight: 500;
  margin-top: 16px;
  padding: 8px;
  background: #f6ffed;
  border-radius: 6px;
}
</style>
