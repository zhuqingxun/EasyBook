<template>
  <div class="admin-page">
    <div class="admin-header">
      <h2 class="brand-small" @click="goHome">EasyBook</h2>
      <span class="admin-title">管理面板</span>
    </div>

    <!-- 登录表单 -->
    <div v-if="!token" class="login-box">
      <n-card title="管理员登录" style="max-width: 400px; margin: 80px auto">
        <n-input
          v-model:value="password"
          type="password"
          placeholder="请输入管理密码"
          show-password-on="click"
          @keyup.enter="handleLogin"
        />
        <n-button
          type="primary"
          block
          style="margin-top: 16px"
          :loading="loginLoading"
          @click="handleLogin"
        >
          登录
        </n-button>
        <p v-if="loginError" class="error-text">{{ loginError }}</p>
      </n-card>
    </div>

    <!-- Dashboard -->
    <div v-else class="dashboard">
      <n-button text style="margin-bottom: 16px" @click="handleLogout">退出登录</n-button>

      <n-grid :x-gap="16" :y-gap="16" :cols="2">
        <!-- 搜索统计 -->
        <n-gi :span="1">
          <n-card title="搜索统计">
            <div class="stat-row">
              <n-statistic label="总搜索次数" :value="stats?.search_count ?? 0" />
              <n-statistic label="平均响应时间">
                <template #default>
                  {{ stats?.avg_response_time ?? 0 }}s
                </template>
              </n-statistic>
            </div>
            <n-divider />
            <h4 style="margin: 0 0 8px">热门搜索词 Top 20</h4>
            <n-data-table
              :columns="searchTermColumns"
              :data="stats?.top_search_terms ?? []"
              :max-height="300"
              size="small"
              :bordered="false"
            />
          </n-card>
        </n-gi>

        <!-- 访问统计 -->
        <n-gi :span="1">
          <n-card title="访问统计">
            <div class="stat-row">
              <n-statistic label="总 PV" :value="stats?.total_pv ?? 0" />
              <n-statistic label="独立访客 (UV)" :value="stats?.unique_visitors ?? 0" />
            </div>
            <n-divider />
            <h4 style="margin: 0 0 8px">每日访问趋势</h4>
            <n-data-table
              :columns="dailyPVColumns"
              :data="stats?.daily_pv ?? []"
              :max-height="200"
              size="small"
              :bordered="false"
            />
            <h4 style="margin: 12px 0 8px">最近 24 小时趋势</h4>
            <n-data-table
              :columns="hourlyPVColumns"
              :data="stats?.hourly_pv ?? []"
              :max-height="200"
              size="small"
              :bordered="false"
            />
          </n-card>
        </n-gi>

        <!-- 系统状态 -->
        <n-gi :span="1">
          <n-card title="系统状态">
            <template v-if="system">
              <div class="info-section">
                <h4>DuckDB</h4>
                <p>状态: {{ system.duckdb.initialized ? '已初始化' : '未初始化' }}</p>
                <p>模式: {{ system.duckdb.mode === 'remote_obs' ? '远程 OBS' : '本地文件' }}</p>
                <p>路径: {{ system.duckdb.parquet_path }}</p>
              </div>
              <n-divider />
              <div class="info-section">
                <h4>内存使用</h4>
                <p>RSS: {{ system.memory.rss_mb }} MB</p>
                <p>VMS: {{ system.memory.vms_mb }} MB</p>
              </div>
            </template>
            <n-spin v-else />
          </n-card>
        </n-gi>

        <!-- 缓存管理 -->
        <n-gi :span="1">
          <n-card title="缓存管理">
            <template v-if="system">
              <div class="stat-row">
                <n-statistic label="缓存条目">
                  <template #default>
                    {{ system.cache.size }} / {{ system.cache.max_size }}
                  </template>
                </n-statistic>
                <n-statistic label="命中率">
                  <template #default>
                    {{ (system.cache.hit_rate * 100).toFixed(1) }}%
                  </template>
                </n-statistic>
              </div>
              <div class="stat-row" style="margin-top: 12px">
                <n-statistic label="命中次数" :value="system.cache.hits" />
                <n-statistic label="未命中次数" :value="system.cache.misses" />
              </div>
              <n-divider />
              <n-button type="warning" @click="handleClearCache" :loading="clearingCache">
                清空缓存
              </n-button>
            </template>
            <n-spin v-else />
          </n-card>
        </n-gi>
      </n-grid>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NInput,
  NButton,
  NGrid,
  NGi,
  NStatistic,
  NDataTable,
  NDivider,
  NSpin,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import {
  adminLogin,
  getStats,
  getSystemStatus,
  clearCache,
  type StatsResponse,
  type SystemResponse,
} from '@/api/modules/admin'

const router = useRouter()
const message = useMessage()

const token = ref(sessionStorage.getItem('admin_token') || '')
const password = ref('')
const loginLoading = ref(false)
const loginError = ref('')
const clearingCache = ref(false)

const stats = ref<StatsResponse | null>(null)
const system = ref<SystemResponse | null>(null)

const searchTermColumns: DataTableColumns = [
  { title: '排名', key: 'rank', width: 60, render: (_, index) => `${index + 1}` },
  { title: '搜索词', key: 'term' },
  { title: '次数', key: 'count', width: 80 },
]

const dailyPVColumns: DataTableColumns = [
  { title: '日期', key: 'date' },
  { title: '访问量', key: 'count', width: 80 },
]

const hourlyPVColumns: DataTableColumns = [
  { title: '小时', key: 'hour' },
  { title: '访问量', key: 'count', width: 80 },
]

function goHome() {
  router.push('/')
}

async function handleLogin() {
  if (!password.value.trim()) return
  loginLoading.value = true
  loginError.value = ''
  try {
    const res = await adminLogin(password.value)
    token.value = res.token
    sessionStorage.setItem('admin_token', res.token)
    password.value = ''
    await loadDashboard()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loginError.value = err.response?.data?.detail || '登录失败'
  } finally {
    loginLoading.value = false
  }
}

function handleLogout() {
  token.value = ''
  sessionStorage.removeItem('admin_token')
  stats.value = null
  system.value = null
}

async function loadDashboard() {
  if (!token.value) return
  try {
    const [statsRes, systemRes] = await Promise.all([
      getStats(token.value),
      getSystemStatus(token.value),
    ])
    stats.value = statsRes
    system.value = systemRes
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 401) {
      handleLogout()
      message.error('登录已过期，请重新登录')
    }
  }
}

async function handleClearCache() {
  clearingCache.value = true
  try {
    await clearCache(token.value)
    message.success('缓存已清空')
    await loadDashboard()
  } catch {
    message.error('清空缓存失败')
  } finally {
    clearingCache.value = false
  }
}

onMounted(() => {
  if (token.value) {
    loadDashboard()
  }
})
</script>

<style scoped>
.admin-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px;
}

.admin-header {
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

.admin-title {
  font-size: 18px;
  color: #666;
}

.stat-row {
  display: flex;
  gap: 32px;
}

.info-section h4 {
  margin: 0 0 4px;
  color: #333;
}

.info-section p {
  margin: 2px 0;
  font-size: 14px;
  color: #666;
}

.error-text {
  color: #d03050;
  margin: 8px 0 0;
  font-size: 14px;
}
</style>
