# Vue3 + Vite 搭建搜索界面最佳实践技术笔记

## 1. 项目初始化

### 1.1 使用 pnpm 和 Vite 创建项目

```bash
# 安装 pnpm (如果未安装)
npm install -g pnpm

# 创建 Vue3 + TypeScript 项目
pnpm create vite vue3-search-app --template vue-ts

# 进入项目目录
cd vue3-search-app

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

### 1.2 安装必要的依赖

```bash
# 安装 UI 组件库 (推荐 Naive UI)
pnpm add naive-ui

# 安装 HTTP 客户端
pnpm add axios

# 安装状态管理
pnpm add pinia

# 安装路由
pnpm add vue-router@4

# 安装自动导入插件 (开发依赖)
pnpm add -D unplugin-auto-import unplugin-vue-components

# 安装 Sass (可选)
pnpm add -D sass
```

### 1.3 配置 vite.config.ts

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    // 自动导入 Vue Composition API
    AutoImport({
      imports: [
        'vue',
        'vue-router',
        'pinia',
        {
          'naive-ui': [
            'useDialog',
            'useMessage',
            'useNotification',
            'useLoadingBar'
          ]
        }
      ],
      dts: 'src/types/auto-imports.d.ts'
    }),
    // 自动导入组件
    Components({
      resolvers: [NaiveUiResolver()],
      dts: 'src/types/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'naive-ui': ['naive-ui'],
          'vue-vendor': ['vue', 'vue-router', 'pinia']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
```

### 1.4 配置 tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,

    /* Path mapping */
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

## 2. UI 组件库选择: Naive UI vs Element Plus

### 2.1 对比分析

| 特性 | Naive UI | Element Plus |
|------|----------|--------------|
| **组件数量** | 70+ 组件 | 70+ 组件 |
| **设计理念** | 极简主义、现代化、注重性能 | 企业级、全面、适合复杂交互 |
| **TypeScript 支持** | ✅ 原生 TS 编写,类型完善 | ✅ 完整的 TS 支持 |
| **定制化能力** | ✅ 强大的主题定制系统 | ✅ 完善的主题系统 |
| **文档质量** | ✅ 清晰、有交互式主题预览 | ✅ 详细、示例丰富 |
| **社区活跃度** | 🔥 快速增长中 | 🔥 成熟、活跃 |
| **打包体积** | 较小 (Tree-shaking 友好) | 中等 |
| **适用场景** | 现代化应用、注重性能的项目 | 企业级应用、复杂后台系统 |

### 2.2 推荐结论

**对于搜索类应用,推荐使用 Naive UI**,原因如下:

1. **性能优先**: Naive UI 设计理念注重性能,对搜索应用的快速响应很重要
2. **现代化 UI**: 更简洁的设计风格适合搜索界面
3. **TypeScript 原生**: 完美的类型提示提高开发效率
4. **轻量级**: 更小的打包体积,更快的加载速度
5. **主题定制**: 提供可视化主题定制工具

## 3. 推荐项目结构

```
vue3-search-app/
├── public/                      # 静态资源
│   └── favicon.ico
├── src/
│   ├── api/                     # API 接口层
│   │   ├── request.ts          # Axios 封装
│   │   ├── types.ts            # API 类型定义
│   │   └── modules/            # API 模块
│   │       └── search.ts       # 搜索相关 API
│   ├── assets/                  # 资源文件
│   │   ├── styles/             # 样式文件
│   │   │   ├── variables.scss  # 变量
│   │   │   └── global.scss     # 全局样式
│   │   └── images/             # 图片
│   ├── components/              # 公共组件
│   │   ├── SearchBox.vue       # 搜索框组件
│   │   ├── SearchResults.vue   # 搜索结果列表
│   │   ├── SearchItem.vue      # 搜索结果项
│   │   ├── Pagination.vue      # 分页组件
│   │   └── LoadingState.vue    # 加载状态组件
│   ├── composables/             # 组合式函数
│   │   └── useSearch.ts        # 搜索逻辑
│   ├── router/                  # 路由配置
│   │   └── index.ts
│   ├── stores/                  # Pinia 状态管理
│   │   └── search.ts           # 搜索状态
│   ├── types/                   # 类型定义
│   │   ├── auto-imports.d.ts   # 自动生成
│   │   ├── components.d.ts     # 自动生成
│   │   └── search.ts           # 搜索相关类型
│   ├── utils/                   # 工具函数
│   │   └── helpers.ts
│   ├── views/                   # 页面组件
│   │   ├── Home.vue            # 首页
│   │   └── SearchPage.vue      # 搜索结果页
│   ├── App.vue                  # 根组件
│   ├── main.ts                  # 入口文件
│   └── env.d.ts                 # 环境类型定义
├── .gitignore
├── index.html
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## 4. API 调用封装 (Axios)

### 4.1 类型定义 (src/api/types.ts)

```typescript
// 通用 API 响应类型
export interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
  success: boolean
}

// 分页请求参数
export interface PageParams {
  page: number
  pageSize: number
}

// 分页响应数据
export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// 请求配置扩展
export interface RequestConfig {
  showLoading?: boolean
  showError?: boolean
  customErrorMsg?: string
}
```

### 4.2 Axios 实例封装 (src/api/request.ts)

```typescript
import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError
} from 'axios'
import type { ApiResponse, RequestConfig } from './types'

// 创建 Axios 实例类
class HttpRequest {
  private instance: AxiosInstance
  private loadingCount = 0

  constructor(baseURL: string, timeout: number = 10000) {
    this.instance = axios.create({
      baseURL,
      timeout,
      headers: {
        'Content-Type': 'application/json;charset=utf-8'
      }
    })

    this.setupInterceptors()
  }

  // 配置拦截器
  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 添加 token
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // 显示 loading
        const customConfig = config as AxiosRequestConfig & RequestConfig
        if (customConfig.showLoading !== false) {
          this.showLoading()
        }

        return config
      },
      (error: AxiosError) => {
        console.error('请求错误:', error)
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        this.hideLoading()

        const { data } = response

        // 处理业务错误
        if (!data.success) {
          const customConfig = response.config as AxiosRequestConfig & RequestConfig
          const errorMsg = customConfig.customErrorMsg || data.message || '请求失败'

          if (customConfig.showError !== false) {
            window.$message?.error(errorMsg)
          }

          return Promise.reject(new Error(errorMsg))
        }

        return response
      },
      (error: AxiosError<ApiResponse>) => {
        this.hideLoading()

        // HTTP 错误处理
        let errorMsg = '请求失败'

        if (error.response) {
          const status = error.response.status
          switch (status) {
            case 400:
              errorMsg = '请求参数错误'
              break
            case 401:
              errorMsg = '未授权,请重新登录'
              localStorage.removeItem('token')
              // 跳转到登录页
              window.location.href = '/login'
              break
            case 403:
              errorMsg = '没有权限访问'
              break
            case 404:
              errorMsg = '请求的资源不存在'
              break
            case 500:
              errorMsg = '服务器错误'
              break
            case 503:
              errorMsg = '服务暂时不可用'
              break
            default:
              errorMsg = error.response.data?.message || '请求失败'
          }
        } else if (error.request) {
          errorMsg = '网络连接失败'
        }

        const customConfig = error.config as AxiosRequestConfig & RequestConfig
        if (customConfig?.showError !== false) {
          window.$message?.error(errorMsg)
        }

        return Promise.reject(error)
      }
    )
  }

  // 显示加载中
  private showLoading(): void {
    if (this.loadingCount === 0) {
      window.$loadingBar?.start()
    }
    this.loadingCount++
  }

  // 隐藏加载中
  private hideLoading(): void {
    this.loadingCount--
    if (this.loadingCount <= 0) {
      this.loadingCount = 0
      window.$loadingBar?.finish()
    }
  }

  // GET 请求
  get<T = any>(
    url: string,
    params?: any,
    config?: AxiosRequestConfig & RequestConfig
  ): Promise<T> {
    return this.instance
      .get<ApiResponse<T>>(url, { params, ...config })
      .then(res => res.data.data)
  }

  // POST 请求
  post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig & RequestConfig
  ): Promise<T> {
    return this.instance
      .post<ApiResponse<T>>(url, data, config)
      .then(res => res.data.data)
  }

  // PUT 请求
  put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig & RequestConfig
  ): Promise<T> {
    return this.instance
      .put<ApiResponse<T>>(url, data, config)
      .then(res => res.data.data)
  }

  // DELETE 请求
  delete<T = any>(
    url: string,
    params?: any,
    config?: AxiosRequestConfig & RequestConfig
  ): Promise<T> {
    return this.instance
      .delete<ApiResponse<T>>(url, { params, ...config })
      .then(res => res.data.data)
  }
}

// 创建默认实例
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
const http = new HttpRequest(baseURL)

export default http
```

### 4.3 搜索 API (src/api/modules/search.ts)

```typescript
import http from '../request'
import type { PageParams, PageResult } from '../types'

// 搜索结果项类型
export interface SearchResultItem {
  id: string | number
  title: string
  content: string
  url: string
  timestamp: string
  author?: string
  category?: string
  tags?: string[]
  score?: number
}

// 搜索请求参数
export interface SearchParams extends PageParams {
  query: string
  category?: string
  sortBy?: 'relevance' | 'date'
}

// 搜索 API
export const searchApi = {
  // 搜索
  search(params: SearchParams) {
    return http.get<PageResult<SearchResultItem>>('/search', params)
  },

  // 获取热门搜索
  getHotSearches() {
    return http.get<string[]>('/search/hot')
  },

  // 获取搜索建议
  getSuggestions(query: string) {
    return http.get<string[]>('/search/suggestions', { query })
  }
}
```

## 5. 搜索组件设计

### 5.1 搜索类型定义 (src/types/search.ts)

```typescript
export interface SearchResultItem {
  id: string | number
  title: string
  content: string
  url: string
  timestamp: string
  author?: string
  category?: string
  tags?: string[]
  score?: number
}

export interface SearchState {
  query: string
  results: SearchResultItem[]
  total: number
  page: number
  pageSize: number
  loading: boolean
  error: string | null
}
```

### 5.2 搜索框组件 (src/components/SearchBox.vue)

```vue
<template>
  <div class="search-box">
    <n-input
      v-model:value="searchQuery"
      type="text"
      size="large"
      placeholder="输入搜索关键词..."
      clearable
      :loading="loading"
      @keyup.enter="handleSearch"
    >
      <template #prefix>
        <n-icon :component="SearchOutline" />
      </template>
    </n-input>

    <n-button
      type="primary"
      size="large"
      :loading="loading"
      @click="handleSearch"
    >
      搜索
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { SearchOutline } from '@vicons/ionicons5'

interface Props {
  initialQuery?: string
  loading?: boolean
}

interface Emits {
  (e: 'search', query: string): void
}

const props = withDefaults(defineProps<Props>(), {
  initialQuery: '',
  loading: false
})

const emit = defineEmits<Emits>()

const searchQuery = ref(props.initialQuery)

const handleSearch = () => {
  const query = searchQuery.value.trim()
  if (!query) {
    window.$message?.warning('请输入搜索关键词')
    return
  }
  emit('search', query)
}

// 暴露方法供父组件调用
defineExpose({
  clear: () => {
    searchQuery.value = ''
  },
  focus: () => {
    // 实现聚焦逻辑
  }
})
</script>

<style scoped lang="scss">
.search-box {
  display: flex;
  gap: 12px;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;

  .n-input {
    flex: 1;
  }

  .n-button {
    min-width: 100px;
  }
}
</style>
```

### 5.3 搜索结果列表组件 (src/components/SearchResults.vue)

```vue
<template>
  <div class="search-results">
    <!-- 搜索信息 -->
    <div v-if="!loading && results.length > 0" class="search-info">
      找到 <span class="highlight">{{ total }}</span> 条结果
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large">
        <template #description>
          正在搜索...
        </template>
      </n-spin>
    </div>

    <!-- 搜索结果 -->
    <div v-else-if="results.length > 0" class="results-list">
      <SearchItem
        v-for="item in results"
        :key="item.id"
        :item="item"
        @click="handleItemClick(item)"
      />
    </div>

    <!-- 空结果 -->
    <n-empty
      v-else-if="!loading && showEmpty"
      description="没有找到相关结果"
      size="large"
      class="empty-state"
    >
      <template #icon>
        <n-icon :component="SearchOutline" />
      </template>
      <template #extra>
        <n-space vertical>
          <div>建议:</div>
          <ul class="suggestions">
            <li>检查关键词是否拼写正确</li>
            <li>尝试使用更通用的关键词</li>
            <li>尝试使用更少的关键词</li>
          </ul>
        </n-space>
      </template>
    </n-empty>
  </div>
</template>

<script setup lang="ts">
import { SearchOutline } from '@vicons/ionicons5'
import SearchItem from './SearchItem.vue'
import type { SearchResultItem } from '@/types/search'

interface Props {
  results: SearchResultItem[]
  total: number
  loading?: boolean
  showEmpty?: boolean
}

interface Emits {
  (e: 'item-click', item: SearchResultItem): void
}

withDefaults(defineProps<Props>(), {
  loading: false,
  showEmpty: true
})

const emit = defineEmits<Emits>()

const handleItemClick = (item: SearchResultItem) => {
  emit('item-click', item)
}
</script>

<style scoped lang="scss">
.search-results {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px 0;
}

.search-info {
  margin-bottom: 20px;
  font-size: 14px;
  color: #666;

  .highlight {
    color: var(--primary-color);
    font-weight: 600;
  }
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  margin-top: 60px;

  .suggestions {
    text-align: left;
    padding-left: 20px;
    margin-top: 12px;

    li {
      margin: 8px 0;
      color: #999;
    }
  }
}
</style>
```

### 5.4 搜索结果项组件 (src/components/SearchItem.vue)

```vue
<template>
  <div class="search-item" @click="handleClick">
    <div class="item-header">
      <h3 class="item-title" v-html="highlightedTitle"></h3>
      <n-tag v-if="item.category" size="small" :bordered="false">
        {{ item.category }}
      </n-tag>
    </div>

    <p class="item-content" v-html="highlightedContent"></p>

    <div class="item-footer">
      <div class="item-meta">
        <span v-if="item.author" class="meta-item">
          <n-icon :component="PersonOutline" />
          {{ item.author }}
        </span>
        <span class="meta-item">
          <n-icon :component="TimeOutline" />
          {{ formatTime(item.timestamp) }}
        </span>
      </div>

      <div v-if="item.tags && item.tags.length > 0" class="item-tags">
        <n-tag
          v-for="tag in item.tags"
          :key="tag"
          size="small"
          :bordered="false"
          type="info"
        >
          {{ tag }}
        </n-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PersonOutline, TimeOutline } from '@vicons/ionicons5'
import type { SearchResultItem } from '@/types/search'

interface Props {
  item: SearchResultItem
  highlightKeyword?: string
}

interface Emits {
  (e: 'click', item: SearchResultItem): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 高亮关键词
const highlightText = (text: string, keyword?: string) => {
  if (!keyword) return text
  const regex = new RegExp(`(${keyword})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

const highlightedTitle = computed(() =>
  highlightText(props.item.title, props.highlightKeyword)
)

const highlightedContent = computed(() =>
  highlightText(props.item.content, props.highlightKeyword)
)

// 格式化时间
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < hour) {
    return `${Math.floor(diff / minute)} 分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} 小时前`
  } else if (diff < 30 * day) {
    return `${Math.floor(diff / day)} 天前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

const handleClick = () => {
  emit('click', props.item)
}
</script>

<style scoped lang="scss">
.search-item {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    border-color: var(--primary-color);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.item-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  flex: 1;

  :deep(mark) {
    background-color: #fff566;
    padding: 2px 4px;
    border-radius: 2px;
  }
}

.item-content {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;

  :deep(mark) {
    background-color: #fff566;
    padding: 2px 4px;
    border-radius: 2px;
  }
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #999;

  .n-icon {
    font-size: 14px;
  }
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
```

### 5.5 分页组件 (src/components/Pagination.vue)

```vue
<template>
  <div v-if="totalPages > 1" class="pagination-wrapper">
    <n-pagination
      v-model:page="currentPage"
      :page-count="totalPages"
      :page-size="pageSize"
      :page-sizes="pageSizes"
      show-size-picker
      show-quick-jumper
      :on-update:page="handlePageChange"
      :on-update:page-size="handlePageSizeChange"
    >
      <template #prefix="{ itemCount }">
        共 {{ itemCount }} 条
      </template>
    </n-pagination>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  total: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
}

interface Emits {
  (e: 'update:page', page: number): void
  (e: 'update:pageSize', pageSize: number): void
  (e: 'change', page: number, pageSize: number): void
}

const props = withDefaults(defineProps<Props>(), {
  page: 1,
  pageSize: 10,
  pageSizes: () => [10, 20, 30, 50]
})

const emit = defineEmits<Emits>()

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)

const totalPages = computed(() =>
  Math.ceil(props.total / currentPageSize.value)
)

watch(() => props.page, (newPage) => {
  currentPage.value = newPage
})

watch(() => props.pageSize, (newPageSize) => {
  currentPageSize.value = newPageSize
})

const handlePageChange = (page: number) => {
  emit('update:page', page)
  emit('change', page, currentPageSize.value)
}

const handlePageSizeChange = (pageSize: number) => {
  currentPageSize.value = pageSize
  currentPage.value = 1
  emit('update:pageSize', pageSize)
  emit('update:page', 1)
  emit('change', 1, pageSize)
}
</script>

<style scoped lang="scss">
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}
</style>
```

## 6. 状态管理方案

### 6.1 何时使用 Pinia vs 组件状态

**使用 Pinia 的场景:**
- 搜索状态需要在多个页面/组件间共享
- 需要持久化搜索历史
- 需要全局的搜索配置 (如默认排序、过滤条件)
- 复杂的搜索状态管理 (如多步骤搜索、高级筛选)

**使用组件状态的场景:**
- 简单的单页面搜索应用
- 搜索状态仅在当前页面使用
- 不需要搜索历史或持久化

### 6.2 搜索 Store (src/stores/search.ts)

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchApi } from '@/api/modules/search'
import type { SearchParams, SearchResultItem } from '@/api/modules/search'
import type { PageResult } from '@/api/types'

export const useSearchStore = defineStore('search', () => {
  // 状态
  const query = ref('')
  const results = ref<SearchResultItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const searchHistory = ref<string[]>([])

  // 计算属性
  const hasResults = computed(() => results.value.length > 0)
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
  const isEmpty = computed(() => !loading.value && results.value.length === 0 && query.value !== '')

  // 搜索方法
  const search = async (params?: Partial<SearchParams>) => {
    try {
      loading.value = true
      error.value = null

      const searchParams: SearchParams = {
        query: query.value,
        page: page.value,
        pageSize: pageSize.value,
        ...params
      }

      const result: PageResult<SearchResultItem> = await searchApi.search(searchParams)

      results.value = result.list
      total.value = result.total
      page.value = result.page
      pageSize.value = result.pageSize

      // 添加到搜索历史
      if (query.value && !searchHistory.value.includes(query.value)) {
        searchHistory.value.unshift(query.value)
        if (searchHistory.value.length > 10) {
          searchHistory.value = searchHistory.value.slice(0, 10)
        }
        saveSearchHistory()
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '搜索失败'
      results.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  // 设置搜索关键词
  const setQuery = (newQuery: string) => {
    query.value = newQuery
    page.value = 1
  }

  // 翻页
  const changePage = (newPage: number) => {
    page.value = newPage
    search()
  }

  // 改变每页数量
  const changePageSize = (newPageSize: number) => {
    pageSize.value = newPageSize
    page.value = 1
    search()
  }

  // 清空搜索
  const clear = () => {
    query.value = ''
    results.value = []
    total.value = 0
    page.value = 1
    error.value = null
  }

  // 保存搜索历史到 localStorage
  const saveSearchHistory = () => {
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value))
  }

  // 加载搜索历史
  const loadSearchHistory = () => {
    const saved = localStorage.getItem('searchHistory')
    if (saved) {
      try {
        searchHistory.value = JSON.parse(saved)
      } catch (e) {
        console.error('加载搜索历史失败', e)
      }
    }
  }

  // 清空搜索历史
  const clearHistory = () => {
    searchHistory.value = []
    localStorage.removeItem('searchHistory')
  }

  // 初始化时加载搜索历史
  loadSearchHistory()

  return {
    // 状态
    query,
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    searchHistory,
    // 计算属性
    hasResults,
    totalPages,
    isEmpty,
    // 方法
    search,
    setQuery,
    changePage,
    changePageSize,
    clear,
    clearHistory
  }
})
```

### 6.3 简单场景使用 Composable (src/composables/useSearch.ts)

```typescript
import { ref, computed } from 'vue'
import { searchApi } from '@/api/modules/search'
import type { SearchParams, SearchResultItem } from '@/api/modules/search'

export function useSearch() {
  const query = ref('')
  const results = ref<SearchResultItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const hasResults = computed(() => results.value.length > 0)
  const isEmpty = computed(() => !loading.value && results.value.length === 0 && query.value !== '')

  const search = async (params?: Partial<SearchParams>) => {
    try {
      loading.value = true
      error.value = null

      const searchParams: SearchParams = {
        query: query.value,
        page: page.value,
        pageSize: pageSize.value,
        ...params
      }

      const result = await searchApi.search(searchParams)

      results.value = result.list
      total.value = result.total
      page.value = result.page
      pageSize.value = result.pageSize
    } catch (err) {
      error.value = err instanceof Error ? err.message : '搜索失败'
      results.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const clear = () => {
    query.value = ''
    results.value = []
    total.value = 0
    page.value = 1
    error.value = null
  }

  return {
    query,
    results,
    total,
    page,
    pageSize,
    loading,
    error,
    hasResults,
    isEmpty,
    search,
    clear
  }
}
```

## 7. 路由设计

### 7.1 路由配置 (src/router/index.ts)

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: '首页'
    }
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/SearchPage.vue'),
    meta: {
      title: '搜索结果'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 搜索应用`
  }
  next()
})

export default router
```

### 7.2 搜索结果页 (src/views/SearchPage.vue)

```vue
<template>
  <div class="search-page">
    <div class="search-header">
      <div class="container">
        <div class="logo" @click="goHome">搜索应用</div>
        <SearchBox
          :initial-query="searchStore.query"
          :loading="searchStore.loading"
          @search="handleSearch"
        />
      </div>
    </div>

    <div class="search-content">
      <div class="container">
        <SearchResults
          :results="searchStore.results"
          :total="searchStore.total"
          :loading="searchStore.loading"
          :show-empty="searchStore.isEmpty"
          @item-click="handleItemClick"
        />

        <Pagination
          v-if="searchStore.hasResults"
          :total="searchStore.total"
          :page="searchStore.page"
          :page-size="searchStore.pageSize"
          @change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSearchStore } from '@/stores/search'
import SearchBox from '@/components/SearchBox.vue'
import SearchResults from '@/components/SearchResults.vue'
import Pagination from '@/components/Pagination.vue'
import type { SearchResultItem } from '@/types/search'

const route = useRoute()
const router = useRouter()
const searchStore = useSearchStore()

// 处理搜索
const handleSearch = (query: string) => {
  searchStore.setQuery(query)
  updateURL()
  searchStore.search()
}

// 处理翻页
const handlePageChange = (page: number, pageSize: number) => {
  searchStore.changePage(page)
  updateURL()
}

// 处理结果项点击
const handleItemClick = (item: SearchResultItem) => {
  // 打开新窗口
  window.open(item.url, '_blank')
}

// 返回首页
const goHome = () => {
  router.push('/')
}

// 更新 URL
const updateURL = () => {
  router.replace({
    path: '/search',
    query: {
      q: searchStore.query,
      page: searchStore.page > 1 ? searchStore.page : undefined
    }
  })
}

// 从 URL 恢复搜索状态
const restoreFromURL = () => {
  const query = route.query.q as string
  const page = parseInt(route.query.page as string) || 1

  if (query) {
    searchStore.setQuery(query)
    searchStore.page = page
    searchStore.search()
  } else {
    // 没有搜索关键词,跳转到首页
    router.replace('/')
  }
}

// 监听路由变化
watch(() => route.query, () => {
  if (route.path === '/search') {
    restoreFromURL()
  }
}, { deep: true })

onMounted(() => {
  restoreFromURL()
})
</script>

<style scoped lang="scss">
.search-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.search-header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  color: var(--primary-color);
  cursor: pointer;
  margin-bottom: 16px;
  transition: opacity 0.3s;

  &:hover {
    opacity: 0.8;
  }
}

.search-content {
  padding: 20px 0;
}
</style>
```

### 7.3 首页 (src/views/Home.vue)

```vue
<template>
  <div class="home-page">
    <div class="home-content">
      <h1 class="logo">搜索应用</h1>
      <p class="subtitle">快速找到你需要的内容</p>

      <SearchBox @search="handleSearch" />

      <!-- 搜索历史 -->
      <div v-if="searchStore.searchHistory.length > 0" class="search-history">
        <div class="history-header">
          <span>搜索历史</span>
          <n-button text @click="handleClearHistory">
            清空
          </n-button>
        </div>
        <div class="history-tags">
          <n-tag
            v-for="item in searchStore.searchHistory"
            :key="item"
            :bordered="false"
            closable
            @click="handleHistoryClick(item)"
            @close="handleHistoryRemove(item)"
          >
            {{ item }}
          </n-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSearchStore } from '@/stores/search'
import SearchBox from '@/components/SearchBox.vue'

const router = useRouter()
const searchStore = useSearchStore()

const handleSearch = (query: string) => {
  router.push({
    path: '/search',
    query: { q: query }
  })
}

const handleHistoryClick = (query: string) => {
  handleSearch(query)
}

const handleHistoryRemove = (query: string) => {
  const index = searchStore.searchHistory.indexOf(query)
  if (index > -1) {
    searchStore.searchHistory.splice(index, 1)
  }
}

const handleClearHistory = () => {
  searchStore.clearHistory()
}
</script>

<style scoped lang="scss">
.home-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.home-content {
  width: 100%;
  max-width: 800px;
  padding: 0 20px;
}

.logo {
  font-size: 64px;
  font-weight: bold;
  color: #fff;
  text-align: center;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  text-align: center;
  margin: 0 0 48px 0;
}

.search-history {
  margin-top: 40px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  color: #fff;
  font-size: 14px;
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  .n-tag {
    cursor: pointer;

    &:hover {
      opacity: 0.8;
    }
  }
}
</style>
```

## 8. 响应式设计

### 8.1 全局样式 (src/assets/styles/global.scss)

```scss
// 变量
:root {
  --primary-color: #18a058;
  --primary-hover: #36ad6a;
  --primary-pressed: #0c7a43;
  --error-color: #d03050;
  --warning-color: #f0a020;
  --info-color: #2080f0;
  --success-color: #18a058;
}

// 重置样式
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  width: 100%;
  height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
    'Noto Color Emoji';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
}

a {
  color: inherit;
  text-decoration: none;
}

ul,
ol {
  list-style: none;
}

// 响应式断点
$breakpoints: (
  xs: 480px,
  sm: 640px,
  md: 768px,
  lg: 1024px,
  xl: 1280px,
  xxl: 1536px
);

// 响应式 mixin
@mixin respond-to($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (max-width: map-get($breakpoints, $breakpoint)) {
      @content;
    }
  }
}

// 容器
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;

  @include respond-to(md) {
    padding: 0 16px;
  }
}

// 工具类
.text-center {
  text-align: center;
}

.text-left {
  text-align: left;
}

.text-right {
  text-align: right;
}

// 滚动条样式
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;

  &:hover {
    background: #555;
  }
}
```

### 8.2 响应式搜索组件调整

```vue
<!-- 在 SearchBox.vue 中添加响应式样式 -->
<style scoped lang="scss">
.search-box {
  display: flex;
  gap: 12px;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;

  @media (max-width: 640px) {
    flex-direction: column;
    gap: 8px;

    .n-button {
      width: 100%;
    }
  }
}
</style>
```

## 9. 构建部署配置

### 9.1 环境变量配置

创建 `.env` 文件:
```env
# 开发环境
VITE_API_BASE_URL=http://localhost:8000/api
```

创建 `.env.production` 文件:
```env
# 生产环境
VITE_API_BASE_URL=https://api.example.com
```

### 9.2 main.ts 入口配置

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// 全局样式
import './assets/styles/global.scss'

const app = createApp(App)

// 状态管理
app.use(createPinia())

// 路由
app.use(router)

// 挂载
app.mount('#app')
```

### 9.3 配置 Naive UI 全局化配置

```vue
<!-- App.vue -->
<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-loading-bar-provider>
      <n-message-provider>
        <n-notification-provider>
          <n-dialog-provider>
            <AppContent />
          </n-dialog-provider>
        </n-notification-provider>
      </n-message-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { NConfigProvider, NLoadingBarProvider, NMessageProvider, NNotificationProvider, NDialogProvider } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import AppContent from './AppContent.vue'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
    primaryColorPressed: '#0c7a43'
  }
}
</script>
```

```vue
<!-- AppContent.vue -->
<template>
  <router-view />
</template>

<script setup lang="ts">
import { useLoadingBar, useMessage, useNotification, useDialog } from 'naive-ui'

// 挂载到 window 对象供全局使用
window.$loadingBar = useLoadingBar()
window.$message = useMessage()
window.$notification = useNotification()
window.$dialog = useDialog()
</script>
```

### 9.4 TypeScript 全局类型声明 (src/env.d.ts)

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Naive UI 全局方法类型
import type {
  LoadingBarProviderInst,
  MessageProviderInst,
  NotificationProviderInst,
  DialogProviderInst
} from 'naive-ui'

declare global {
  interface Window {
    $loadingBar?: LoadingBarProviderInst
    $message?: MessageProviderInst
    $notification?: NotificationProviderInst
    $dialog?: DialogProviderInst
  }
}

export {}
```

### 9.5 构建命令

在 `package.json` 中配置:

```json
{
  "name": "vue3-search-app",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "axios": "^1.6.0",
    "naive-ui": "^2.38.0",
    "@vicons/ionicons5": "^0.12.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "vue-tsc": "^1.8.27",
    "sass": "^1.70.0",
    "unplugin-auto-import": "^0.17.5",
    "unplugin-vue-components": "^0.26.0"
  }
}
```

### 9.6 生产构建

```bash
# 类型检查
pnpm type-check

# 生产构建
pnpm build

# 预览生产构建
pnpm preview
```

### 9.7 部署建议

**静态托管平台:**
- Vercel
- Netlify
- GitHub Pages
- 阿里云 OSS + CDN
- 腾讯云 COS + CDN

**Nginx 配置示例:**

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/vue3-search-app/dist;
    index index.html;

    # 启用 gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 10. 性能优化建议

### 10.1 代码分割

- ✅ 路由懒加载已配置
- ✅ Vite 自动代码分割
- ✅ 手动分块配置 (见 vite.config.ts)

### 10.2 请求优化

```typescript
// 防抖搜索
import { useDebounceFn } from '@vueuse/core'

const debouncedSearch = useDebounceFn(() => {
  searchStore.search()
}, 300)
```

### 10.3 虚拟滚动 (大量结果时)

```bash
pnpm add vueuc
```

```vue
<template>
  <n-virtual-list
    :items="results"
    :item-size="120"
    :item-resizable="true"
  >
    <template #default="{ item }">
      <SearchItem :item="item" />
    </template>
  </n-virtual-list>
</template>
```

## 总结

本技术笔记涵盖了使用 Vue3 + Vite + TypeScript + Naive UI + Pinia 构建搜索应用的完整最佳实践,包括:

1. ✅ 项目初始化和配置
2. ✅ UI 组件库选择 (推荐 Naive UI)
3. ✅ 规范的项目结构
4. ✅ 完善的 Axios 封装 (类型安全、拦截器、错误处理)
5. ✅ 搜索组件设计 (搜索框、结果列表、分页、加载状态)
6. ✅ 状态管理方案 (Pinia Store + Composable)
7. ✅ 路由设计 (URL 参数、状态恢复)
8. ✅ 响应式布局
9. ✅ 生产构建和部署配置

所有代码都使用 TypeScript 编写,具有完整的类型安全保障。
