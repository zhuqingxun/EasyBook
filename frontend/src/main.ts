import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles/global.scss'

console.log('[EasyBook] 应用初始化中...')
console.log('[EasyBook] API Base URL:', import.meta.env.VITE_API_BASE_URL || '/api (默认)')
console.log('[EasyBook] 环境:', import.meta.env.MODE)

const app = createApp(App)
app.use(router)
app.mount('#app')

console.log('[EasyBook] 应用已挂载')
